"""Database models. SQLite locally, Postgres in production (DATABASE_URL).

No table holds a raw identifier: GSTIN, Udyam number, phone and signatory ID number
live only in the token vault, encrypted. Documents are stored as ciphertext.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, create_engine, ForeignKey, LargeBinary, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import get_settings


def now() -> datetime:
    return datetime.now(timezone.utc)


def aware(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; everything here is UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class Base(DeclarativeBase):
    pass


class VaultEntry(Base):
    __tablename__ = "vault"
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(24))
    hmac_index: Mapped[str] = mapped_column(String(64), index=True)
    wrapped_dek: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)  # None = crypto-shredded
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AdvisorSession(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ses"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    channel: Mapped[str] = mapped_column(String(16), default="web")  # web | whatsapp | voice | partner
    language: Mapped[str] = mapped_column(String(8), default="en")
    partner_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)  # identifiers replaced by tokens
    messages: Mapped[list] = mapped_column(JSON, default=list)  # masked text only
    bundle: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    trace: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="open")
    phone_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone_index: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # keyed hash, finds a returning WhatsApp user
    stall_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ord"))
    access_key: Mapped[str] = mapped_column(String(64), default=lambda: uuid.uuid4().hex)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    session_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="draft")
    business_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    segment: Mapped[str | None] = mapped_column(String(8), nullable=True)
    city: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="en")
    channel: Mapped[str] = mapped_column(String(16), default="web")
    partner_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    bundle: Mapped[dict] = mapped_column(JSON, default=dict)
    term_months: Mapped[int] = mapped_column(Integer, default=12)
    monthly: Mapped[int] = mapped_column(Integer, default=0)
    setup: Mapped[int] = mapped_column(Integer, default=0)
    setup_emi: Mapped[bool] = mapped_column(Boolean, default=False)
    gstin_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    udyam_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kyc_outcome: Mapped[str | None] = mapped_column(String(16), nullable=True)
    kyc_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    payment: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    install_slot: Mapped[str | None] = mapped_column(String(40), nullable=True)
    specimen: Mapped[str | None] = mapped_column(String(8), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class OrderEvent(Base):
    __tablename__ = "order_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(40), ForeignKey("orders.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    kind: Mapped[str] = mapped_column(String(32))
    product_id: Mapped[str | None] = mapped_column(String(8), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class Consent(Base):
    __tablename__ = "consents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(40), index=True)
    purpose: Mapped[str] = mapped_column(String(32))
    granted: Mapped[bool] = mapped_column(Boolean)
    notice_version: Mapped[str] = mapped_column(String(32))
    language: Mapped[str] = mapped_column(String(8))
    channel: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("doc"))
    order_id: Mapped[str] = mapped_column(String(40), index=True)
    doc_type: Mapped[str] = mapped_column(String(32))
    storage_key: Mapped[str] = mapped_column(String(200))
    wrapped_dek: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    mime: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    delete_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fields: Mapped[dict] = mapped_column(JSON, default=dict)  # masked extraction
    quality: Mapped[dict] = mapped_column(JSON, default=dict)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    actor: Mapped[str] = mapped_column(String(48))
    action: Mapped[str] = mapped_column(String(48))
    target: Mapped[str] = mapped_column(String(80))
    purpose: Mapped[str | None] = mapped_column(String(32), nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class Callback(Base):
    __tablename__ = "callbacks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(String(16), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    partner_id: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="assigned")  # assigned | called | won | lost
    virtual_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class SimUser(Base):
    """DoT (31 Aug 2023): every end user of a business connection is verified before their SIM goes live."""
    __tablename__ = "sim_users"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sim"))
    order_id: Mapped[str] = mapped_column(String(40), index=True)
    name_token: Mapped[str] = mapped_column(String(64))
    phone_token: Mapped[str] = mapped_column(String(64))
    phone_masked: Mapped[str] = mapped_column(String(16), default="")
    product_id: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(16), default="invited")  # invited | verified
    method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InboundMessage(Base):
    """Webhook deduplication: Meta retries deliveries, and each message must be answered once."""
    __tablename__ = "inbound_messages"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    channel: Mapped[str] = mapped_column(String(16))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class HelpRequest(Base):
    """'Talk to a person': an owned task with a reachable number, a language and a time window."""
    __tablename__ = "help_requests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("hlp"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    source: Mapped[str] = mapped_column(String(16))  # advisor | quote | kyc | tracker | account | whatsapp
    session_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    order_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    phone_token: Mapped[str] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(8), default="en")
    window: Mapped[str] = mapped_column(String(32))  # today_evening | tomorrow_morning | asap ...
    reason: Mapped[str] = mapped_column(String(32))
    summary: Mapped[dict] = mapped_column(JSON, default=dict)  # masked: profile facts, quote, stage
    partner_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    assignee: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | assigned | called | resolved
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


Index("ix_vault_kind_hmac", VaultEntry.kind, VaultEntry.hmac_index)

_engine = None
_Session = None


def engine():
    global _engine, _Session
    if _engine is None:
        url = get_settings().database_url
        kw = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {"pool_pre_ping": True, "pool_size": 10}
        _engine = create_engine(url, **kw)
        _Session = sessionmaker(bind=_engine, expire_on_commit=False)
        Base.metadata.create_all(_engine)
    return _engine


def SessionLocal():
    engine()
    return _Session()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
