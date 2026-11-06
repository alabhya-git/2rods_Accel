"""Encrypted document storage. Files are sealed before they touch disk or a bucket.

Local disk by default; set STORAGE_BACKEND=gcs and STORAGE_BUCKET for Google Cloud
Storage (asia-south1) in production. The bucket only ever holds ciphertext.
"""
from __future__ import annotations

import os
from datetime import timedelta

from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import AuditLog, Document, new_id, now
from . import crypto


class _Local:
    def __init__(self):
        self.root = get_settings().storage_dir

    def put(self, key: str, data: bytes) -> None:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        return (self.root / key).read_bytes()

    def delete(self, key: str) -> None:
        try:
            (self.root / key).unlink()
        except FileNotFoundError:
            pass


class _GCS:  # pragma: no cover - needs cloud credentials
    def __init__(self, bucket: str):
        from google.cloud import storage  # type: ignore

        self.bucket = storage.Client().bucket(bucket)

    def put(self, key, data):
        self.bucket.blob(key).upload_from_string(data)

    def get(self, key):
        return self.bucket.blob(key).download_as_bytes()

    def delete(self, key):
        self.bucket.blob(key).delete()


def backend():
    if os.getenv("STORAGE_BACKEND") == "gcs":
        return _GCS(os.environ["STORAGE_BUCKET"])
    return _Local()


def save_document(db: Session, order_id: str, doc_type: str, data: bytes, mime: str) -> Document:
    doc_id = new_id("doc")
    key = f"{order_id}/{doc_id}.bin"
    wrapped, nonce, ct = crypto.seal(data, aad=doc_id.encode())
    backend().put(key, ct)
    doc = Document(id=doc_id, order_id=order_id, doc_type=doc_type, storage_key=key, wrapped_dek=wrapped, nonce=nonce,
                   sha256=crypto.sha256(data), size=len(data), mime=mime,
                   delete_after=now() + timedelta(days=get_settings().document_retention_days))
    db.add(doc)
    db.add(AuditLog(actor="owner", action="document_uploaded", target=doc_id, purpose="kyc_verification", detail={"doc_type": doc_type, "size": len(data)}))
    db.flush()
    return doc


def read_document(db: Session, doc: Document, actor: str) -> bytes:
    ct = backend().get(doc.storage_key)
    db.add(AuditLog(actor=actor, action="document_read", target=doc.id, purpose="kyc_verification", detail={}))
    return crypto.open_(doc.wrapped_dek, doc.nonce, ct, aad=doc.id.encode())


def shred_document(db: Session, doc: Document, reason: str) -> None:
    backend().delete(doc.storage_key)
    doc.wrapped_dek = None
    doc.deleted_at = now()
    db.add(AuditLog(actor="system", action="document_shredded", target=doc.id, purpose=None, detail={"reason": reason}))
    db.flush()
