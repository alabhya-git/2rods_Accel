"""Retention: documents are crypto-shredded after their window; abandoned journeys purged."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import AdvisorSession, AuditLog, Document, now
from .storage import shred_document
from .vault import shred


def purge(db: Session) -> dict:
    st = get_settings()
    n_docs = 0
    for doc in db.scalars(select(Document).where(Document.deleted_at.is_(None), Document.delete_after < now())).all():
        shred_document(db, doc, "retention_window")
        n_docs += 1
    cutoff = now() - timedelta(days=st.abandoned_session_days)
    n_sessions = 0
    for s in db.scalars(select(AdvisorSession).where(AdvisorSession.status == "open", AdvisorSession.updated_at < cutoff)).all():
        for v in (s.profile or {}).values():
            if isinstance(v, str) and v.startswith("tok_"):
                shred(db, v)
        if s.phone_token:
            shred(db, s.phone_token)
        s.messages, s.profile, s.status = [], {}, "purged"
        n_sessions += 1
    db.add(AuditLog(actor="system", action="retention_run", target="all", purpose=None, detail={"documents": n_docs, "sessions": n_sessions}))
    db.commit()
    return {"documents_shredded": n_docs, "sessions_purged": n_sessions}
