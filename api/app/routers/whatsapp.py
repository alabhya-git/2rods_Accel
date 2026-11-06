"""WhatsApp front end. Same advisor, same rules, same privacy.

Real: WhatsApp Cloud API webhook (WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, WHATSAPP_VERIFY_TOKEN,
WHATSAPP_APP_SECRET). Every delivery is signature-checked (X-Hub-Signature-256) and
deduplicated by message id, because Meta retries. Text and voice notes are understood;
documents are never collected in the chat: KYC and payment open the web app by link.
Demo: /api/whatsapp/simulate powers the in-app WhatsApp simulator, no Meta account needed.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..advisor.agent import Advisor
from ..config import get_settings
from ..db import AdvisorSession, InboundMessage, get_db
from ..kyc.ids import mask_phone
from ..privacy import crypto, vault
from ..voice import speech
from .advisor import load_state, save_state

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])
log = logging.getLogger("app.whatsapp")


def converse(db: Session, wa_number: str, text: str, voice: bool = False) -> dict:
    idx = crypto.index("phone", wa_number)
    s = db.scalar(select(AdvisorSession).where(AdvisorSession.phone_index == idx, AdvisorSession.channel == "whatsapp",
                                               AdvisorSession.status.in_(["open", "quoted"])).order_by(AdvisorSession.updated_at.desc()))
    adv = Advisor(tokenize=lambda kind, value: vault.tokenize(db, kind, value))
    if not s:
        s = AdvisorSession(channel="whatsapp", phone_token=vault.tokenize(db, "phone", wa_number), phone_index=idx,
                           language="en", profile={"_meta": {}})
        db.add(s)
        db.flush()
    turn, state = adv.respond(load_state(s), text)
    save_state(s, state, turn)
    db.commit()
    reply = turn.text
    base = get_settings().public_url.rstrip("/")
    if turn.stage == "recommended":
        reply += f"\n\n{base}/quote?session={s.id}"
    if turn.stage == "handoff":
        reply += f"\n\n{base}/help?session={s.id}"
    return {"session_id": s.id, "reply": reply, "turn": turn.to_dict(), "from_masked": mask_phone(wa_number), "voice": voice}


class SimIn(BaseModel):
    from_number: str = "9800000001"
    text: str


@router.post("/simulate")
def simulate(body: SimIn, db: Session = Depends(get_db)):
    return converse(db, body.from_number, body.text)


@router.get("/webhook")
def verify(mode: str = Query(alias="hub.mode", default=""), token: str = Query(alias="hub.verify_token", default=""),
           challenge: str = Query(alias="hub.challenge", default="")):
    if mode == "subscribe" and hmac.compare_digest(token, get_settings().whatsapp_verify_token):
        return PlainTextResponse(challenge)
    raise HTTPException(403, "verification failed")


def signature_ok(raw: bytes, header: str | None) -> bool:
    secret = get_settings().whatsapp_app_secret
    if not secret:
        return get_settings().environment != "prod"  # dev without a Meta app; production refuses to start without it
    good = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return bool(header) and hmac.compare_digest(good, header)


def first_time(db: Session, msg_id: str) -> bool:
    db.add(InboundMessage(id=msg_id, channel="whatsapp"))
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def send(to: str, text: str) -> None:
    st = get_settings()
    if not (st.whatsapp_token and st.whatsapp_phone_id):
        return
    version = os.getenv("WHATSAPP_API_VERSION", "v21.0")
    try:
        httpx.post(f"https://graph.facebook.com/{version}/{st.whatsapp_phone_id}/messages", timeout=10,
                   headers={"authorization": f"Bearer {st.whatsapp_token}"},
                   json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text[:4000]}})
    except httpx.HTTPError as e:
        log.warning("whatsapp send failed: %s", e)


def media_bytes(media_id: str) -> bytes | None:
    st = get_settings()
    if not st.whatsapp_token:
        return None
    version = os.getenv("WHATSAPP_API_VERSION", "v21.0")
    try:
        h = {"authorization": f"Bearer {st.whatsapp_token}"}
        meta = httpx.get(f"https://graph.facebook.com/{version}/{media_id}", headers=h, timeout=10).json()
        return httpx.get(meta["url"], headers=h, timeout=20).content
    except (httpx.HTTPError, KeyError) as e:
        log.warning("whatsapp media fetch failed: %s", e)
        return None


@router.post("/webhook")
async def receive(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    if not signature_ok(raw, request.headers.get("x-hub-signature-256")):
        raise HTTPException(401, "bad signature")
    body = await request.json()
    try:
        value = body["entry"][0]["changes"][0]["value"]
        msg = value["messages"][0]
    except (KeyError, IndexError, TypeError):
        return {"ok": True}  # delivery receipts and status updates
    if not first_time(db, msg.get("id") or hashlib.sha256(raw).hexdigest()):
        return {"ok": True, "duplicate": True}
    kind = msg.get("type")
    if kind == "text":
        out = converse(db, msg["from"], msg["text"]["body"])
    elif kind == "audio":  # a voice note in any of the 10 languages
        audio = media_bytes(msg["audio"]["id"])
        heard = speech.transcribe(audio, "audio/ogg") if audio else None
        if not heard or not heard.get("text"):
            send(msg["from"], "Sorry, I couldn't hear that clearly. Please type it, or send the voice note again.")
            return {"ok": True}
        out = converse(db, msg["from"], heard["text"], voice=True)
        out["reply"] = f"🎙 \"{heard['text']}\"\n\n" + out["reply"]  # show what was heard before acting on it
    else:
        send(msg["from"], "I can read text and voice notes. For documents, use the secure link I send with your quote.")
        return {"ok": True}
    send(msg["from"], out["reply"])
    return {"ok": True}
