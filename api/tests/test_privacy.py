import pytest

from app.db import SessionLocal, VaultEntry, Order, AuditLog
from app.privacy import consent, crypto, vault
from app.privacy.redact import mask_text
from app.privacy.storage import read_document, save_document, shred_document


@pytest.fixture
def db():
    s = SessionLocal()
    yield s
    s.rollback()
    s.close()


def test_ciphertext_never_contains_plaintext(db):
    tok = vault.tokenize(db, "gstin", "27XUIXG0767D1ZP")
    e = db.get(VaultEntry, tok)
    assert b"27XUIXG0767D1ZP" not in e.ciphertext
    assert tok.startswith("tok_gstin_") and "27XU" not in tok


def test_tokens_are_never_shared_so_erasure_is_per_order(db):
    a, b = vault.tokenize(db, "phone", "9876543210"), vault.tokenize(db, "phone", "9876543210")
    assert a != b and vault.find(db, "phone", "9876543210")
    vault.shred(db, a)  # erasing one order's copy leaves the other order working
    assert vault.detokenize(db, b, actor="owner", purpose="rights_access", order_id="ord_x") == "9876543210"


def test_order_purposes_need_an_order(db):
    tok = vault.tokenize(db, "gstin", "19EOGXH4115Y1ZL")
    with pytest.raises(PermissionError):
        vault.detokenize(db, tok, actor="kyc_service", purpose="kyc_verification")


def test_detokenize_needs_policy_and_consent(db):
    order = Order()
    db.add(order)
    db.flush()
    tok = vault.tokenize(db, "gstin", "19EOGXH4115Y1ZL")
    with pytest.raises(PermissionError):
        vault.detokenize(db, tok, actor="backoffice", purpose="kyc_verification", order_id=order.id)
    with pytest.raises(PermissionError):  # no consent yet
        vault.detokenize(db, tok, actor="kyc_service", purpose="kyc_verification", order_id=order.id)
    consent.record(db, order.id, {"kyc_verification": True, "service_delivery": True}, "en", "web")
    assert vault.detokenize(db, tok, actor="kyc_service", purpose="kyc_verification", order_id=order.id) == "19EOGXH4115Y1ZL"
    consent.withdraw(db, order.id, "kyc_verification")
    with pytest.raises(PermissionError):
        vault.detokenize(db, tok, actor="kyc_service", purpose="kyc_verification", order_id=order.id)
    actions = [a.action for a in db.query(AuditLog).filter(AuditLog.target == tok[:20]).all()]
    assert "detokenize" in actions and "detokenize_denied" in actions


def test_required_consents_enforced(db):
    with pytest.raises(ValueError):
        consent.record(db, "ord_x", {"kyc_verification": True}, "en", "web")


def test_crypto_shred(db):
    tok = vault.tokenize(db, "id_no", "SYN-ID-123456")
    vault.shred(db, tok)
    e = db.get(VaultEntry, tok)
    with pytest.raises(PermissionError):
        crypto.open_(e.wrapped_dek, e.nonce, e.ciphertext, tok.encode())


def test_document_round_trip_and_shred(db):
    data = b"\x89PNG fake image bytes"
    doc = save_document(db, "ord_test", "gst_certificate", data, "image/png")
    assert read_document(db, doc, "kyc_service") == data
    shred_document(db, doc, "test")
    with pytest.raises(Exception):
        read_document(db, doc, "kyc_service")


def test_masking():
    s = "GSTIN 27XUIXG0767D1ZP phone 9876543210 udyam UDYAM-MH-00-9516696 mail a.b@x.com pan ABCDE1234F id SYN-ID-447889"
    m = mask_text(s)
    for raw in ("27XUIXG0767D1ZP", "9876543210", "UDYAM-MH-00-9516696", "a.b@x.com", "ABCDE1234F", "SYN-ID-447889"):
        assert raw not in m
    assert "27XU" in m and "1ZP" in m
