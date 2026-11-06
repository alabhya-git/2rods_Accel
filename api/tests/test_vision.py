"""The second document reader: consent-gated, business documents only, disagreements go to a person."""
from app.kyc import vision
from app.kyc.checks import Declared, evaluate
from app.kyc.ocr import Extraction, Quality

GOOD = Quality(20000.0, 0.05, 0.0, False, False)


def test_id_cards_are_never_sent(monkeypatch):
    monkeypatch.setattr(vision, "enabled", lambda: True)
    assert vision.read(b"x", "image/png", "signatory_id") is None


def test_second_reader_fills_gaps_and_flags_disagreement():
    ex = Extraction(None, GOOD, {"billed_to": "Sharma Kirana", "bill_date": ""}, text="")
    ai = {"document_type": "address_proof", "billed_to": "Verma Stores", "bill_date": "2026-07-01", "supply_address": "Shop 4, MI Road, Jaipur - 302001",
          "consumer_no": "", "looks_edited": False}
    m = vision.merge(ex, ai, "address_proof")
    assert m.doc_type_detected == "address_proof" and m.fields["bill_date"] == "2026-07-01"
    assert m.id_meta["ai"]["conflicts"][0]["field"] == "billed_to"
    r = evaluate(Declared(None, None, "Sharma Kirana", "shop_licence"), {"address_proof": m, "shop_licence": None, "signatory_id": None})
    assert "address_proof.readers" in {c.id for c in r.checks if c.status == "fail"}


def test_edited_looking_document_goes_to_a_person():
    ex = Extraction("address_proof", GOOD, {"billed_to": "A", "bill_date": "2026-07-01", "supply_address": "B - 302001"},
                    {"ai": {"looks_edited": True, "conflicts": []}})
    r = evaluate(Declared(None, None, "A", "shop_licence"), {"address_proof": ex, "shop_licence": None, "signatory_id": None})
    assert "address_proof.edited" in {c.id for c in r.checks if c.status == "fail"} and r.outcome == "review"
