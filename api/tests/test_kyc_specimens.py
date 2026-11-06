"""All 12 specimen applicants through the real OCR + decision pipeline."""
import json
from pathlib import Path
import pytest
from app.data_store import store
from app.kyc.checks import Declared, evaluate, DOC_TYPES
from app.kyc.ocr import decode, extract

DATA = Path(__file__).resolve().parents[2] / "data"
SPEC = json.loads((DATA / "specimens.json").read_text())

EXPECTED = {
    "K01": ("review", {"gstin.status", "udyam.number"}),
    "K02": ("verified", set()),
    "K03": ("verified", set()),
    "K04": ("fix_needed", {"gst_certificate.legible"}),
    "K05": ("fix_needed", {"udyam_certificate.present"}),
    "K06": ("review", {"gst_certificate.gstin"}),
    "K07": ("review", {"gst_certificate.legal_name"}),
    "K08": ("verified", set()),
    "K09": ("verified", set()),
    "K10": ("verified", set()),
    "K11": ("fix_needed", {"address_proof.fresh"}),
    "K12": ("verified", set()),
}

@pytest.fixture(scope="module")
def results():
    ds = store()
    out = {}
    for k, decl in SPEC.items():
        docs = {}
        for dt in DOC_TYPES:
            f = DATA / "kyc_documents" / f"{k}_{dt}.png"
            docs[dt] = extract(decode(f.read_bytes()), dt, set(ds.gstin), set(ds.udyam)) if f.exists() else None
        out[k] = evaluate(Declared(decl["gstin"], decl["udyam_number"], decl["business_name"]), docs)
    return out

@pytest.mark.parametrize("k", sorted(EXPECTED))
def test_specimen(results, k):
    outcome, must_fail = EXPECTED[k]
    r = results[k]
    failed = {c.id for c in r.checks if c.level == "hard" and c.status == "fail"}
    assert r.outcome == outcome, (k, r.outcome, failed)
    assert failed == must_fail, (k, failed)

def test_no_false_rejections(results):
    clean = [k for k, (o, _) in EXPECTED.items() if o == "verified"]
    assert all(results[k].outcome == "verified" for k in clean)
