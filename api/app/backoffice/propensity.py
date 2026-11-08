"""Lead propensity: which unclosed leads a partner should call first.

Logistic regression on fields known when the lead is created (no leakage from later
stages). Trained at start-up on smb_leads.csv in about a second; 5-fold AUC reported.
"""
from __future__ import annotations

import threading
from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ..data_store import SEGMENT_CODE, store

CAT = ["lead_source", "segment", "city_tier", "preferred_language", "has_gstin", "has_udyam", "current_internet",
       "current_provider", "annual_turnover_band", "contact_role"]
NUM = ["employee_count", "num_sites", "monthly_telecom_spend_inr", "n_interest"]

ACTION = {
    "Unreachable after 3 attempts": ("WhatsApp", "Send a WhatsApp resume link from the verified Dukaan Connect number"),
    "Wrong or invalid number": ("Partner visit", "Verify the number on a partner visit; switch to network number check at sign-up"),
    "Not interested on first call": ("WhatsApp", "Send a 2-minute advisor link with a segment bundle"),
    "Owner had no time for a visit": ("WhatsApp", "Send the self-serve advisor link; no visit needed"),
    "Visit not scheduled by sales": ("Partner call", "Partner calls within 24 hours with assist mode"),
    "Only wanted a mobile plan": ("WhatsApp", "Offer postpaid lines online; suggest Fibre later"),
    "Locked in with current provider": ("Reminder", "Remind 30 days before their contract ends"),
    "Price too high": ("Partner call", "Offer the 24-month floor price and setup-fee EMI"),
    "Competitor offered cheaper plan": ("Partner call", "Show one-bill bundle value against the competitor quote"),
    "Quote too complex to understand": ("WhatsApp", "Send the plain-language quote link in their language"),
    "Quote took too long to arrive": ("WhatsApp", "Send an instant quote link"),
    "Decided to wait": ("Reminder", "Follow up in 30 days with the saved quote"),
    "Found paperwork too long": ("WhatsApp", "Send the 4-minute Smart KYC link with DigiLocker"),
    "Missing GST or Udyam document": ("WhatsApp", "Fetch the Udyam certificate from DigiLocker"),
    "Document details did not match": ("Partner visit", "Partner checks documents in person"),
    "Authorised signatory not available": ("WhatsApp", "Send the e-sign link to the signatory"),
    "Installation delayed beyond 21 days": ("Ops", "Offer AirFiber, live in 2 days"),
    "Customer cancelled before install": ("Partner call", "Call to understand and rebook"),
    "First payment failed": ("WhatsApp", "Send a UPI Autopay link"),
    "Site not feasible for fibre": ("Ops", "Offer AirFiber"),
}


def _frame(leads: list[dict]) -> pd.DataFrame:
    d = pd.DataFrame(leads)
    for c in NUM[:3]:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0)
    d["n_interest"] = d["products_of_interest"].fillna("").str.count(";") + 1
    d["act"] = (d["outcome"] == "Activated").astype(int)
    return d


@lru_cache
def model() -> dict:
    d = _frame(store().leads)
    ct = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore"), CAT), ("n", StandardScaler(), NUM)])
    pipe = make_pipeline(ct, LogisticRegression(max_iter=5000, C=0.5))
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    oof = cross_val_predict(pipe, d[CAT + NUM], d["act"], cv=cv, method="predict_proba")[:, 1]
    auc = float(roc_auc_score(d["act"], oof))
    d["score"] = oof
    d["decile"] = pd.qcut(d["score"].rank(method="first"), 10, labels=False)
    top30 = d["decile"] >= 7
    pipe.fit(d[CAT + NUM], d["act"])
    names = pipe[0].get_feature_names_out()
    coefs = pipe[-1].coef_[0]
    drivers = sorted(zip(names, coefs), key=lambda x: -abs(x[1]))[:10]
    lift = d.groupby("decile")["act"].mean().sort_index(ascending=False)
    return {
        "pipe": pipe, "frame": d, "auc": round(auc, 3),
        "top30_share": round(float(d.loc[top30, "act"].sum() / d["act"].sum()), 3),
        "top_decile_rate": round(float(lift.iloc[0]), 3), "base_rate": round(float(d["act"].mean()), 3),
        "lift": [{"decile": int(10 - i), "activation_rate": round(float(v), 3)} for i, v in enumerate(lift.values)],
        "drivers": [{"feature": n.split("__", 1)[1].replace("_", " "), "weight": round(float(c), 3)} for n, c in drivers],
    }


def warm() -> None:
    threading.Thread(target=model, daemon=True).start()


def queue(limit: int = 50, segment: str | None = None, city: str | None = None, reason: str | None = None) -> list[dict]:
    m = model()
    d = m["frame"]
    q = d[d["act"] == 0].copy()
    if segment:
        q = q[q["segment"].map(SEGMENT_CODE) == segment]
    if city:
        q = q[q["city"] == city]
    if reason:
        q = q[q["drop_reason"] == reason]
    q = q.sort_values("score", ascending=False).head(limit)
    out = []
    for r in q.itertuples():
        channel, action = ACTION.get(r.drop_reason, ("Partner call", "Call back"))
        out.append({"lead_id": r.lead_id, "business_name": r.business_name, "business_type": r.business_type,
                    "segment": SEGMENT_CODE[r.segment], "city": r.city, "language": r.preferred_language,
                    "stage_reached": r.stage_reached, "drop_reason": r.drop_reason, "score": round(float(r.score), 3),
                    "decile": int(r.decile) + 1, "channel": channel, "action": action, "contact": r.contact_name.split()[0] + " " + r.contact_name.split()[-1][0] + ".",
                    "has_gstin": r.has_gstin == "Y", "monthly_spend": int(r.monthly_telecom_spend_inr)})
    return out


def card() -> dict:
    m = model()
    return {k: m[k] for k in ("auc", "top30_share", "top_decile_rate", "base_rate", "lift", "drivers")} | {
        "features": CAT + NUM, "algorithm": "logistic regression, 5-fold cross-validated, fields known at lead creation only"}


def score_profile(p: dict) -> float:
    """Score a live advisor session so the back-office can rank stalled ones too."""
    m = model()
    row = {"lead_source": "Website form", "segment": {v: k for k, v in SEGMENT_CODE.items()}.get(p.get("segment") or "micro"),
           "city_tier": str(p.get("city_tier") or 2), "preferred_language": "English", "has_gstin": "Y" if p.get("has_gstin") else "N",
           "has_udyam": "N", "current_internet": p.get("current_internet") or "Mobile hotspot", "current_provider": "Local ISP",
           "annual_turnover_band": "40 lakh - 1.5 cr", "contact_role": "Owner", "employee_count": p.get("employees") or 1,
           "num_sites": p.get("sites") or 1, "monthly_telecom_spend_inr": 1200, "n_interest": max(1, len(p.get("needs") or []))}
    df = pd.DataFrame([row])
    df["city_tier"] = df["city_tier"].astype(m["frame"]["city_tier"].dtype)
    return float(m["pipe"].predict_proba(df[CAT + NUM])[0, 1])
