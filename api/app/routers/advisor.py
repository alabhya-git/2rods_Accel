from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..advisor.agent import Advisor
from ..db import AdvisorSession, get_db
from ..engine.profile import LANGUAGES
from ..privacy import vault
from ..security import verify as verify_staff

router = APIRouter(prefix="/api/advisor", tags=["advisor"])


class NewSession(BaseModel):
    language: str = "en"
    channel: str = "web"
    partner_id: str | None = None


class Message(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    language: str | None = None  # set when the owner picks a language in the UI


def load_state(s: AdvisorSession) -> dict:
    prof = dict(s.profile or {})
    meta = prof.pop("_meta", {})
    return {"profile": prof, "history": s.messages or [], "bundle": s.bundle, "language": s.language, **meta}


def save_state(s: AdvisorSession, state: dict, turn) -> None:
    meta = {k: state.get(k) for k in ("asked", "questions", "tokens", "lang_locked")}
    s.profile = {**state["profile"], "_meta": meta}
    s.messages = state["history"]
    s.bundle = state.get("bundle")
    s.language = state.get("language") or s.language
    s.trace = (s.trace or [])[-10:] + [{"turn": len(s.messages) // 2, "steps": turn.trace}]
    if turn.stage == "recommended":
        s.status = "quoted"
    if turn.stage == "handoff":
        s.stall_reason = "asked_for_person"


def view(s: AdvisorSession, turn=None) -> dict:
    state = load_state(s)
    prof = {k: v for k, v in state["profile"].items()}
    return {"session_id": s.id, "language": s.language, "channel": s.channel, "partner_id": s.partner_id, "status": s.status,
            "profile": prof, "bundle": s.bundle, "messages": s.messages, "turn": turn.to_dict() if turn else None,
            "has_gstin_token": bool((state.get("tokens") or {}).get("gstin"))}


def advisor_for(db: Session) -> Advisor:
    return Advisor(tokenize=lambda kind, value: vault.tokenize(db, kind, value))


@router.post("/sessions")
def new_session(body: NewSession, db: Session = Depends(get_db), x_staff_token: str | None = Header(default=None)):
    lang = body.language if body.language in LANGUAGES else "en"
    claims = verify_staff(x_staff_token) or {}
    # partner credit only from a signed partner sign-in, never from a query string
    partner_id = body.partner_id if body.partner_id and claims.get("partner_id") == body.partner_id else None
    channel = "partner" if partner_id else ("whatsapp" if body.channel == "whatsapp" else "web")
    s = AdvisorSession(language=lang, channel=channel, partner_id=partner_id,
                       profile={"language": lang, "_meta": {"lang_locked": body.language in LANGUAGES and body.language != "en"}})
    turn = advisor_for(db).greet(lang)
    s.messages = [{"role": "assistant", "text": turn.text}]
    db.add(s)
    db.commit()
    return view(s, turn)


@router.get("/sessions/{sid}")
def get_session(sid: str, db: Session = Depends(get_db)):
    s = db.get(AdvisorSession, sid)
    if not s:
        raise HTTPException(404, "session not found")
    return view(s)


class ProfilePatch(BaseModel):
    """A tap on the 'What I understood' card or a price question: typed, exact, no model in the loop."""
    set: dict = Field(default_factory=dict)
    qty: dict[str, int] = Field(default_factory=dict)
    add_needs: list[str] = Field(default_factory=list)
    remove_needs: list[str] = Field(default_factory=list)
    only: bool = False


@router.post("/sessions/{sid}/profile")
def patch_profile(sid: str, body: ProfilePatch, db: Session = Depends(get_db)):
    s = db.get(AdvisorSession, sid)
    if not s:
        raise HTTPException(404, "session not found")
    turn, state = advisor_for(db).apply_patch(load_state(s), body.model_dump())
    save_state(s, state, turn)
    db.commit()
    return view(s, turn)


@router.post("/sessions/{sid}/messages")
def message(sid: str, body: Message, db: Session = Depends(get_db)):
    s = db.get(AdvisorSession, sid)
    if not s:
        raise HTTPException(404, "session not found")
    state = load_state(s)
    if body.language in LANGUAGES:
        state["language"], state["lang_locked"] = body.language, True
    turn, state = advisor_for(db).respond(state, body.text)
    save_state(s, state, turn)
    db.commit()
    return view(s, turn)
