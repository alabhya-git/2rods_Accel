"""Self-hosted document reading: quality gate, deskew, watermark removal, OCR, field parsing.

Runs Tesseract + OpenCV inside our own boundary, so documents are never sent to a
third-party AI service. ID numbers are re-read from a tight crop and self-healed.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from rapidfuzz import fuzz

from .ids import heal_gstin, heal_udyam

BLUR_THRESHOLD = 1500.0  # Laplacian variance on inked regions; sharp scans score > 15,000
MIN_INK = 0.006  # share of dark pixels; a washed-out photo falls below
DATE_RE = re.compile(r"(\d{4})\s*-\s*(\d{2})\s*-\s*(\d{2})")

DOC_TITLES = {
    "gst_certificate": ["gst registration certificate"],
    "udyam_certificate": ["udyam registration certificate"],
    "address_proof": ["electricity bill", "utility", "address proof"],
    "signatory_id": ["authorised signatory id", "signatory id"],
    "shop_licence": ["shop and establishment", "shops and establishments", "shops & establishments", "trade licence",
                     "trade license", "gumasta", "registration certificate of establishment"],
    # last: a rented shop's bill is in the landlord's name, and this links the shop to its tenant
    "rent_agreement": ["rent agreement", "leave and licence", "leave and license", "lease agreement", "tenancy agreement"],
}
FIELDS = {
    "gst_certificate": {"gstin": ["gstin"], "legal_name": ["legal name"], "trade_name": ["trade name"],
                         "constitution": ["constitution"], "address": ["address of principal"],
                         "date_of_liability": ["date of liability"], "registration_type": ["type of registration"]},
    "udyam_certificate": {"udyam_number": ["udyam reg. number", "udyam reg number"], "enterprise_name": ["enterprise name"],
                           "major_activity": ["major activity"], "city": ["city"], "state": ["state"],
                           "date_of_registration": ["date of registration"]},
    "address_proof": {"consumer_no": ["consumer no"], "billed_to": ["billed to"], "supply_address": ["supply address"],
                       "bill_date": ["bill date"], "units": ["units consumed"], "amount_due": ["amount due"]},
    "signatory_id": {"name": ["name"], "designation": ["designation"], "business": ["for business"],
                      "id_no": ["id no"], "valid_till": ["valid till"]},
    "shop_licence": {"licence_no": ["licence no", "license no", "registration no", "certificate no"],
                     "establishment": ["name of establishment", "establishment name", "name of the establishment"],
                     "owner": ["name of employer", "name of owner", "proprietor"], "address": ["address", "postal address"],
                     "valid_till": ["valid till", "valid upto", "valid up to"]},
    "rent_agreement": {"landlord": ["landlord", "licensor", "lessor"], "tenant": ["tenant", "licensee", "lessee"],
                       "premises": ["premises", "property address"], "date_of_agreement": ["agreement date", "date of agreement"],
                       "valid_till": ["valid till", "valid upto", "period till"], "rent": ["monthly rent", "rent per month"]},
}
CONTINUATION_LABELS = ["place of business"]
MULTILINE = {"address", "supply_address", "premises"}


@dataclass
class Quality:
    sharpness: float
    ink: float
    skew_deg: float
    blurred: bool
    faint: bool

    @property
    def ok(self) -> bool:
        return not (self.blurred or self.faint)


@dataclass
class Extraction:
    doc_type_detected: str | None
    quality: Quality
    fields: dict[str, str] = field(default_factory=dict)
    id_meta: dict[str, dict] = field(default_factory=dict)
    text: str = ""


def decode(data: bytes) -> np.ndarray:
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("not an image")
    # downscale very large phone photos; upscale tiny ones
    h, w = img.shape[:2]
    scale = 1.0
    if max(h, w) > 2600:
        scale = 2600 / max(h, w)
    elif max(h, w) < 900:
        scale = 900 / max(h, w)
    if scale != 1.0:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return img


def _ink_mask(img: np.ndarray) -> np.ndarray:
    return (img.max(axis=2) < 140).astype(np.uint8)


def _skew(mask: np.ndarray) -> float:
    small = cv2.resize(mask, (max(1, mask.shape[1] // 2), max(1, mask.shape[0] // 2)), interpolation=cv2.INTER_AREA)
    best = (0.0, -1.0)
    centre = (small.shape[1] / 2, small.shape[0] / 2)
    for a in np.arange(-15, 15.01, 0.5):
        m = cv2.getRotationMatrix2D(centre, float(a), 1)
        v = float(np.var(cv2.warpAffine(small * 255, m, (small.shape[1], small.shape[0])).sum(axis=1).astype(float)))
        if v > best[1]:
            best = (float(a), v)
    return best[0]


def assess(img: np.ndarray) -> Quality:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mask = _ink_mask(img)
    region = cv2.dilate(mask, np.ones((5, 5), np.uint8)) > 0
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    sharp = float(lap[region].var()) if region.sum() > 50 else 0.0
    ink = float(mask.mean())
    return Quality(round(sharp, 1), round(ink, 4), _skew(mask), sharp < BLUR_THRESHOLD, ink < MIN_INK)


def _deskew(img: np.ndarray, angle: float) -> np.ndarray:
    if abs(angle) < 0.5:
        return img
    m = cv2.getRotationMatrix2D((img.shape[1] / 2, img.shape[0] / 2), angle, 1)
    return cv2.warpAffine(img, m, (img.shape[1], img.shape[0]), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))


def _clean_gray(img: np.ndarray) -> np.ndarray:
    """Grey image with the pink 'SYNTHETIC SPECIMEN' watermark (and similar tints) removed."""
    b, g, r = (img[:, :, i].astype(int) for i in range(3))
    tint = (r - g > 35) & (r - b > 25) & (r > 150)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray[tint] = 255
    return gray


def _lines(gray2x: np.ndarray) -> list[dict]:
    d = pytesseract.image_to_data(gray2x, config="--psm 6", output_type=Output.DICT)
    groups: dict[tuple, list] = {}
    for i, w in enumerate(d["text"]):
        if not w.strip():
            continue
        k = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
        groups.setdefault(k, []).append((d["left"][i], d["top"][i], d["width"][i], d["height"][i], w))
    out = []
    for ws in groups.values():
        ws.sort()
        out.append({"words": ws, "top": min(w[1] for w in ws), "bottom": max(w[1] + w[3] for w in ws),
                    "text": " ".join(w[4] for w in ws)})
    out.sort(key=lambda ln: ln["top"])
    return out


def _match_label(text: str, doc_type: str) -> str | None:
    t = text.lower().strip(" .:")
    best, score = None, 0
    for key, labels in FIELDS[doc_type].items():
        for lab in labels:
            s = 100 if t == lab else fuzz.ratio(t, lab)
            if s > score:
                best, score = key, s
    return best if score >= 80 else None


def detect_type(text: str) -> str | None:
    t = text.lower()
    for dt, titles in DOC_TITLES.items():
        if any(x in t for x in titles):
            return dt
    return None


def _join(prev: str, nxt: str) -> str:
    if prev and nxt and prev[-1].isalpha() and nxt[0].islower():
        return prev + nxt  # word split across the column edge ("A" + "ndhra")
    return (prev + " " + nxt).strip()


def _read_id_crop(gray: np.ndarray, top: int, bottom: int, x0: int, kind: str, known: set[str] | None) -> dict:
    crop = gray[max(0, top - 8): bottom + 8, x0:]
    votes: Counter = Counter()
    metas: dict[str, dict] = {}
    raws = []
    for scale in (2, 3, 4):
        c = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        _, c = cv2.threshold(c, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        c = cv2.copyMakeBorder(c, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
        for psm in ("7", "8"):
            raw = pytesseract.image_to_string(
                c, config=f"--psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-").strip()
            raws.append(raw)
            h = heal_gstin(raw, known) if kind == "gstin" else heal_udyam(raw, known)
            if h["valid"]:
                bonus = 3 if known and h["value"] in known else 1
                votes[h["value"]] += bonus
                metas.setdefault(h["value"], h)
    if votes:
        value, _ = votes.most_common(1)[0]
        meta = dict(metas[value])
        meta["votes"] = dict(votes)
        return meta
    # nothing valid: report the most common coerced reading so a person can see it
    heals = [heal_gstin(r, known) if kind == "gstin" else heal_udyam(r, known) for r in raws if r]
    readings = Counter(h["value"] for h in heals if h["value"] and len(re.sub(r"[^0-9A-Z]", "", h["value"])) >= 11)
    value = readings.most_common(1)[0][0] if readings else ""
    return {"raw": raws[0] if raws else "", "value": value, "healed": False, "valid": False, "votes": dict(readings)}


def extract(img: np.ndarray, expected_type: str | None, known_gstins: set[str] | None = None,
            known_udyam: set[str] | None = None) -> Extraction:
    q = assess(img)
    work = _deskew(img, q.skew_deg)
    gray = _clean_gray(work)
    gray2 = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    lines = _lines(gray2)
    text = "\n".join(ln["text"] for ln in lines)
    detected = detect_type(text)
    doc_type = expected_type or detected
    ex = Extraction(detected, q, text=text)
    if not doc_type or q.blurred:
        return ex

    width2 = gray2.shape[1]
    if doc_type == "signatory_id":
        # label on one line, value on the next
        pending = None
        for ln in lines:
            key = _match_label(ln["text"], doc_type)
            if key:
                pending = key
                continue
            if pending:
                ex.fields[pending] = ln["text"].strip()
                pending = None
    else:
        split = int(width2 * 0.38)
        last = None
        for ln in lines:
            label = " ".join(w[4] for w in ln["words"] if w[0] < split).strip()
            value = " ".join(w[4] for w in ln["words"] if w[0] >= split).strip()
            key = _match_label(label, doc_type) if label else None
            if key:
                ex.fields[key] = value
                last = key
                if key == "gstin" or key == "udyam_number":
                    x0 = int(split / 2)
                    meta = _read_id_crop(gray, ln["top"] // 2, ln["bottom"] // 2, x0,
                                         "gstin" if key == "gstin" else "udyam",
                                         known_gstins if key == "gstin" else known_udyam)
                    ex.id_meta[key] = meta
                    ex.fields[key] = meta["value"] if value else ""
            elif last in MULTILINE and value and (not label or any(fuzz.partial_ratio(label.lower(), c) > 80 for c in CONTINUATION_LABELS)):
                ex.fields[last] = _join(ex.fields[last], value)
            elif label and not value:
                last = None
    for k, v in list(ex.fields.items()):
        if k.startswith("date") or k in ("bill_date", "valid_till"):
            m = DATE_RE.search(v)
            if m:
                ex.fields[k] = "-".join(m.groups())
    return ex


def pin_code(address: str | None) -> str | None:
    """Last 6 digits after the final hyphen (OCR may split '752083' into '75 2083')."""
    if not address:
        return None
    tail = address.rsplit("-", 1)[-1]
    digits = re.sub(r"\D", "", tail)
    if len(digits) >= 6:
        return digits[-6:]
    m = re.findall(r"\d{6}", re.sub(r"\s", "", address))
    return m[-1] if m else None
