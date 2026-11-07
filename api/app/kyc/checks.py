"""Smart KYC decision rules.

KYC answers four separate questions: who is this person, does the business exist, may
this person act for it, and can these products go live. An application is verified
only when every required fact is positively established. Missing or unreadable
evidence never passes: it becomes a fix for the owner or a review by a person.

Proof routes (which documents prove the business):
  gst           GSTIN holders: GST certificate + registry. Udyam only if one was declared.
  udyam         Udyam but no GST: Udyam certificate (DigiLocker or photo) + Udyam registry.
  shop_licence  Neither: Shop and Establishment certificate or trade licence; always
                checked by a person. GST-only products are not available on this route.
Every route also needs an address proof and the signatory's ID.

Rented shops: the bill is often in the landlord's name. That is a fix the owner can make
alone, not a review: the landlord confirms with an Aadhaar e-sign through a link, or the
owner uploads a rent agreement naming the landlord on the bill, the business and the address.

Registry first, documents second. Hard checks block until fixed; soft checks only add
notes. Soft on purpose: in the specimen pack every Udyam certificate's registration
date differs from the registry and several show a different activity, clean
applicants included, so hard-failing them would wrongly reject good customers.

Dataset rules (README): GSTIN PANs carry an 'X' 4th character and Udyam numbers use
district 00, both accepted by the format checks; dates are judged against the
reference "today" (15 July 2026); registry PINs are synthetic, so addresses are
compared with the registry, never with a real PIN directory.

Outcomes:
  verified     - every required fact positively established
  fix_needed   - the owner can fix it alone (retake, upload, newer bill)
  review       - a person must look (registry status, tampering signals, name mismatch, shop licence)
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date

from rapidfuzz import fuzz

from ..config import get_settings
from ..data_store import lookup_gstin, lookup_udyam
from .ids import gstin_valid, mask_gstin, mask_udyam, udyam_valid
from .ocr import Extraction, pin_code

DOC_TYPES = ("gst_certificate", "udyam_certificate", "address_proof", "signatory_id", "shop_licence", "rent_agreement")
DOC_LABELS = {"gst_certificate": "GST certificate", "udyam_certificate": "Udyam certificate",
              "address_proof": "address proof (electricity bill)", "signatory_id": "signatory ID",
              "shop_licence": "Shop and Establishment certificate or trade licence", "rent_agreement": "rent agreement"}
ROUTES = ("gst", "udyam", "shop_licence")
REQUIRED = {
    "gst": ("gst_certificate", "address_proof", "signatory_id"),
    "udyam": ("udyam_certificate", "address_proof", "signatory_id"),
    "shop_licence": ("shop_licence", "address_proof", "signatory_id"),
}
# fields a document must yield before it can count as evidence
ESSENTIAL = {
    "gst_certificate": ("gstin", "legal_name"),
    "address_proof": ("bill_date", "billed_to", "supply_address"),
    "signatory_id": ("name", "valid_till"),
    "rent_agreement": ("landlord", "tenant", "premises"),
}
NAME_MATCH = 93
ADDRESS_MATCH = 70
MIN_LICENCE_TEXT = 40  # characters of readable text a licence photo must carry


@dataclass
class Check:
    id: str
    level: str  # hard | soft
    status: str  # pass | fail | warn | skip
    severity: str  # fix | review | note
    message: str
    fix: str | None = None
    args: dict = field(default_factory=dict)


@dataclass
class Declared:
    gstin: str | None = None
    udyam_number: str | None = None
    business_name: str | None = None
    route: str = "gst"
    landlord: str | None = None  # the name a landlord e-signed with, confirming the shop is let to this business


@dataclass
class Result:
    outcome: str
    checks: list[Check]
    registry: dict
    extracted: dict
    route: str = "gst"

    def to_dict(self) -> dict:
        return {"outcome": self.outcome, "route": self.route, "checks": [asdict(c) for c in self.checks],
                "registry": self.registry, "extracted": self.extracted}


def norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


def same(a: str | None, b: str | None, threshold: int = NAME_MATCH) -> bool:
    if not a or not b:
        return False
    return fuzz.token_sort_ratio(norm(a), norm(b)) >= threshold


def street(address: str | None) -> str:
    """The address without its PIN: building and street are what tell two shops apart."""
    return norm(re.sub(r"\d\s?\d{2}\s?\d{3}\s*$", "", (address or "").strip()))


def proprietor(legal_name: str | None) -> str | None:
    m = re.match(r"^\s*(.+?)\s*\(\s*Prop", legal_name or "")
    return m.group(1) if m else None


def _date(s: str | None) -> date | None:
    try:
        return date.fromisoformat(s) if s else None
    except ValueError:
        return None


def _tenant_ok(tenant: str | None, names: list[str | None]) -> bool:
    t = norm(tenant)
    return bool(t) and any(n and (same(tenant, n) or (len(norm(n)) >= 6 and norm(n) in t)) for n in names)


def rented(add, bill: dict, lease: dict, signed: str | None, names: list[str | None], today: date) -> None:
    """The bill is in another name. A rented shop links itself to the bill through the landlord:
    their Aadhaar e-sign, or a rent agreement naming them, the business and this address."""
    billed = bill["billed_to"]
    if signed and same(signed, billed):
        add("address_proof.name", "hard", "pass", "review", f"The bill is in the landlord's name ({billed}), who confirmed with an Aadhaar e-sign.",
            None, {"billed_to": billed, "via": "landlord_esign"})
        return
    if signed:
        add("address_proof.name", "hard", "fail", "review", f"The landlord who confirmed (\"{signed}\") is not the person on the bill (\"{billed}\").",
            "A person will check the bill and the landlord's confirmation.", {"billed_to": billed, "signed": signed})
        return
    if lease:
        ok = True
        if not same(lease.get("landlord"), billed):
            ok = False
            add("rent_agreement.landlord", "hard", "fail", "review", f"The landlord on the rent agreement (\"{lease.get('landlord')}\") is not the person on the bill (\"{billed}\").",
                "A person will check the agreement.", {"landlord": lease.get("landlord"), "billed_to": billed})
        if not _tenant_ok(lease.get("tenant"), names):
            ok = False
            add("rent_agreement.tenant", "hard", "fail", "review", f"The rent agreement is for a different tenant (\"{lease.get('tenant')}\").",
                "A person will check the agreement.", {"tenant": lease.get("tenant")})
        lp, bp = pin_code(lease.get("premises")), pin_code(bill.get("supply_address"))
        if (lp and bp and lp != bp) or fuzz.token_set_ratio(street(lease.get("premises")), street(bill.get("supply_address"))) < ADDRESS_MATCH:
            ok = False
            add("rent_agreement.premises", "hard", "fail", "review", "The rent agreement is for a different address from the bill.",
                "A person will check the address.", {"premises": lease.get("premises"), "bill": bill.get("supply_address")})
        vt = _date(lease.get("valid_till"))
        if vt and vt < today:
            ok = False
            add("rent_agreement.valid", "hard", "fail", "fix", f"The rent agreement ended on {lease['valid_till']}.",
                "Upload your current rent agreement.", {"valid_till": lease["valid_till"], "doc": "rent_agreement"})
        if ok:
            add("address_proof.name", "hard", "pass", "review", f"The bill is in the landlord's name ({billed}); the rent agreement links the shop to you.",
                None, {"billed_to": billed, "via": "rent_agreement"})
            add("rent_agreement.face", "soft", "warn", "note", "Rent agreement accepted on its face; the installer sees the shop at the visit.")
        return
    add("address_proof.name", "hard", "fail", "fix", f"The bill is in another name ({billed}).",
        "If you rent the shop, ask your landlord to confirm in one minute, or upload your rent agreement.", {"billed_to": billed, "rented": True})


def required_docs(declared: Declared) -> tuple[str, ...]:
    req = REQUIRED.get(declared.route, REQUIRED["gst"])
    if declared.route == "gst" and declared.udyam_number:
        req = req + ("udyam_certificate",)  # declared Udyam must be evidenced
    return req


def evaluate(declared: Declared, docs: dict[str, Extraction | None]) -> Result:
    st = get_settings()
    today = st.reference_date
    route = declared.route if declared.route in ROUTES else "gst"
    checks: list[Check] = []

    def add(*a, **kw):
        checks.append(Check(*a, **kw))

    required = required_docs(declared)
    # optional documents the owner chose to upload are still checked
    to_check = list(required) + [dt for dt in DOC_TYPES if dt not in required and docs.get(dt) is not None]
    usable: dict[str, dict] = {}

    # 1. every document present, legible, of the right kind, and yielding its essential fields
    for dt in to_check:
        ex = docs.get(dt)
        label = DOC_LABELS[dt]
        if ex is None:
            fix = "Upload it, or fetch it from DigiLocker." if dt == "udyam_certificate" else "Upload a clear photo of it."
            add(f"{dt}.present", "hard", "fail", "fix", f"The {label} is missing.", fix, {"doc": dt})
            continue
        if not ex.quality.ok:
            add(f"{dt}.legible", "hard", "fail", "fix", f"The {label} photo is too blurred to read.",
                "Retake it in good light, phone held steady, the whole page in the frame.", {"doc": dt, "sharpness": ex.quality.sharpness})
            continue
        if ex.doc_type_detected and ex.doc_type_detected != dt:
            add(f"{dt}.type", "hard", "fail", "fix", f"This looks like your {DOC_LABELS[ex.doc_type_detected]}, not the {label}.",
                f"Upload the {label} here.", {"doc": dt, "detected": ex.doc_type_detected})
            continue
        if dt == "shop_licence":
            if len((ex.text or "").strip()) < MIN_LICENCE_TEXT:
                add(f"{dt}.type", "hard", "fail", "fix", "We could not read a licence in this photo.",
                    f"Upload a clear photo of your {label}.", {"doc": dt})
                continue
        elif not ex.doc_type_detected:  # fail closed: an unrecognised page is not evidence
            add(f"{dt}.type", "hard", "fail", "fix", f"We could not recognise this as a {label}.",
                f"Upload a clear photo of the whole {label}.", {"doc": dt, "detected": None})
            continue
        missing = [f for f in ESSENTIAL.get(dt, ()) if not ex.fields.get(f)]
        if missing:
            add(f"{dt}.fields", "hard", "fail", "fix", f"We could not read {', '.join(m.replace('_', ' ') for m in missing)} on the {label}.",
                "Retake the photo with the whole page flat and in focus.", {"doc": dt, "missing": missing})
            continue
        ai = (ex.id_meta or {}).get("ai") or {}
        if ai.get("conflicts"):  # the two readers disagree: neither answer is trusted
            add(f"{dt}.readers", "hard", "fail", "review", f"Two readers disagree on the {label}: {', '.join(c['field'].replace('_', ' ') for c in ai['conflicts'])}.",
                "A person will compare them with the photo.", {"doc": dt, "conflicts": ai["conflicts"]})
        if ai.get("looks_edited"):
            add(f"{dt}.edited", "hard", "fail", "review", f"The {label} may have been edited or photographed from a screen.",
                "A person will check the original.", {"doc": dt})
        extra = {"doc": dt}
        if abs(ex.quality.skew_deg) >= 0.5:
            extra["deskewed_deg"] = ex.quality.skew_deg
        add(f"{dt}.legible", "hard", "pass", "fix", f"{label.capitalize()} read successfully.", None, extra)
        usable[dt] = ex.fields

    gst_f, udy_f, bill_f, id_f = (usable.get(d, {}) for d in ("gst_certificate", "udyam_certificate", "address_proof", "signatory_id"))
    registry: dict = {}
    reg = None

    # 2. GST route: the declared GSTIN against the registry
    if route == "gst":
        g = (declared.gstin or gst_f.get("gstin") or "").upper()
        reg = lookup_gstin(g) if gstin_valid(g) else None
        if not g:
            add("gstin.declared", "hard", "fail", "fix", "No GSTIN was given.", "Enter the GSTIN printed on your GST certificate.")
        elif not gstin_valid(g):
            add("gstin.checksum", "hard", "fail", "fix", f"{mask_gstin(g)} is not a valid GSTIN (check character fails).", "Check the number and type it again.")
        elif not reg:
            add("gstin.registry", "hard", "fail", "review", f"{mask_gstin(g)} is not in the GST registry.", "We will check this with you.")
        else:
            registry["gstin"] = {"gstin_masked": mask_gstin(g), "legal_name": reg["legal_name"], "trade_name": reg["trade_name"],
                                 "constitution": reg["constitution"], "status": reg["status"], "state": reg["state"]}
            if reg["status"] != "Active":
                add("gstin.status", "hard", "fail", "review", f"The GST registry shows this GSTIN as {reg['status']}.",
                    "GST-only services cannot be activated. We will call you about next steps.", {"status": reg["status"]})
            else:
                add("gstin.status", "hard", "pass", "review", "GSTIN is Active in the GST registry.")

        # 3. the GST certificate corroborates the registry
        if gst_f:
            doc_g = (gst_f.get("gstin") or "").upper()
            meta = docs["gst_certificate"].id_meta.get("gstin", {}) if docs.get("gst_certificate") else {}
            if doc_g and not gstin_valid(doc_g):
                add("gst_certificate.gstin", "hard", "fail", "review",
                    f"The GSTIN printed on the certificate ({mask_gstin(doc_g)}) fails the GSTIN check character and does not match the registry.",
                    "A person will compare the certificate with the registry.", {"on_document": mask_gstin(doc_g), "declared": mask_gstin(g)})
            elif doc_g and g and doc_g != g:
                add("gst_certificate.gstin", "hard", "fail", "review", "The GSTIN on the certificate differs from the one you entered.",
                    "A person will compare them.", {"on_document": mask_gstin(doc_g), "declared": mask_gstin(g)})
            elif doc_g:
                add("gst_certificate.gstin", "hard", "pass", "review", "GSTIN on the certificate matches.", None,
                    {"ocr_corrected": bool(meta.get("healed"))})
            if reg:
                for key, reg_key, label in (("legal_name", "legal_name", "Legal name"), ("trade_name", "trade_name", "Trade name")):
                    if gst_f.get(key) and not same(gst_f[key], reg[reg_key]):
                        add(f"gst_certificate.{key}", "hard", "fail", "review",
                            f"{label} on the certificate (\"{gst_f[key]}\") does not match the registry (\"{reg[reg_key]}\").",
                            "A person will check the certificate.", {"on_document": gst_f[key], "registry": reg[reg_key]})
                    elif gst_f.get(key):
                        add(f"gst_certificate.{key}", "hard", "pass", "review", f"{label} matches the registry.")

    business = (reg or {}).get("trade_name") or declared.business_name or gst_f.get("trade_name")

    # 4. Udyam: required on the udyam route, checked whenever a certificate was given
    ureg = None
    if docs.get("udyam_certificate") is not None and "udyam_certificate" in usable:
        u = (udy_f.get("udyam_number") or declared.udyam_number or "").upper() if route == "udyam" else (udy_f.get("udyam_number") or "").upper()
        if not u:
            add("udyam.number", "hard", "fail", "fix", "The Udyam registration number is blank on the certificate.",
                "Type your Udyam number, or fetch the certificate from DigiLocker.")
        elif not udyam_valid(u):
            add("udyam.format", "hard", "fail", "fix", f"{mask_udyam(u)} is not a Udyam number.", "Udyam numbers look like UDYAM-MH-00-1234567.")
        else:
            ureg = lookup_udyam(u)
            if not ureg:
                add("udyam.registry", "hard", "fail", "review", f"{mask_udyam(u)} is not in the Udyam registry.", "A person will check it.")
            else:
                registry["udyam"] = {"udyam_masked": mask_udyam(u), "enterprise_name": ureg["enterprise_name"], "type": ureg["enterprise_type"],
                                     "activity": ureg["major_activity"], "city": ureg["city"]}
                if route == "udyam":
                    # no GST registry: the Udyam registry names the business; the bill and ID must match it
                    business = ureg["enterprise_name"]
                if business and not same(ureg["enterprise_name"], business):
                    add("udyam.name", "hard", "fail", "review", "The Udyam registration is for a different business name.", "A person will check it.",
                        {"registry": ureg["enterprise_name"], "business": business})
                else:
                    add("udyam.registry", "hard", "pass", "review", "Udyam number found in the registry and the name matches.")
                if udy_f.get("date_of_registration") and udy_f["date_of_registration"] != ureg["date_of_registration"]:
                    add("udyam.date", "soft", "warn", "note", "Registration date on the certificate differs from the registry.", None,
                        {"on_document": udy_f["date_of_registration"], "registry": ureg["date_of_registration"]})
                if udy_f.get("major_activity") and norm(udy_f["major_activity"]) != norm(ureg["major_activity"]):
                    add("udyam.activity", "soft", "warn", "note", "Major activity on the certificate differs from the registry.", None,
                        {"on_document": udy_f["major_activity"], "registry": ureg["major_activity"]})

    # 4b. shop licence route: a person always confirms the business
    if route == "shop_licence":
        add("shop_licence.review", "hard", "fail", "review", "A person checks shop licences and trade licences.",
            "We will check it within one working day and message you.", {"route": route})

    # 5. address proof: fresh, same business, same place
    if bill_f:
        bd = _date(bill_f.get("bill_date"))
        if not bd:
            add("address_proof.date", "hard", "fail", "fix", "We could not read the bill date.", "Upload a clearer photo of the bill.")
        elif bd > today:
            add("address_proof.future", "hard", "fail", "review", f"The bill is dated {bill_f['bill_date']}, which is in the future.",
                "A person will check the bill.", {"bill_date": bill_f["bill_date"]})
        else:
            age = (today - bd).days
            if age > st.address_proof_max_age_days:
                add("address_proof.fresh", "hard", "fail", "fix", f"This bill is {age} days old; we need one from the last {st.address_proof_max_age_days} days.",
                    "Upload your latest electricity, water or gas bill.", {"age_days": age, "bill_date": bill_f["bill_date"]})
            else:
                add("address_proof.fresh", "hard", "pass", "fix", f"Bill dated {bill_f['bill_date']} ({age} days old).", None, {"age_days": age})
        if business and bill_f.get("billed_to") and not same(bill_f["billed_to"], business):
            legal = (reg or {}).get("legal_name") or gst_f.get("legal_name")
            if not (legal and same(bill_f["billed_to"], proprietor(legal) or legal)):  # a proprietor's own name is their business's
                rented(add, bill_f, usable.get("rent_agreement", {}), declared.landlord, [business, legal, proprietor(legal)], today)
        reg_addr = (reg or {}).get("principal_place_of_business")
        reg_pin, bill_pin = pin_code(reg_addr), pin_code(bill_f.get("supply_address"))
        if reg_pin and bill_pin:
            if reg_pin != bill_pin:
                add("address_proof.pin", "hard", "fail", "review", f"The bill's PIN code ({bill_pin}) differs from the GST address ({reg_pin}).",
                    "A person will check the address.")
            elif fuzz.token_set_ratio(street(bill_f.get("supply_address")), street(reg_addr)) < ADDRESS_MATCH:
                add("address_proof.address", "hard", "fail", "review", "The bill is for a different building or street from the GST address.",
                    "A person will check the address.", {"bill": bill_f.get("supply_address"), "registry": reg_addr})
            else:
                add("address_proof.pin", "hard", "pass", "review", "Bill address matches the GST address.")
        elif ureg and route == "udyam" and ureg.get("city") and ureg["city"].lower() not in (bill_f.get("supply_address") or "").lower():
            add("address_proof.city", "hard", "fail", "review", f"The bill is not in {ureg['city']}, the Udyam registration's city.",
                "A person will check the address.")

    # 6. signatory
    if id_f:
        vt = _date(id_f.get("valid_till"))
        if vt and vt < today:
            add("signatory.valid", "hard", "fail", "fix", f"The signatory ID expired on {id_f['valid_till']}.", "Upload a valid ID.")
        elif vt:
            add("signatory.valid", "hard", "pass", "fix", "Signatory ID is valid.")
        else:
            add("signatory.valid", "hard", "fail", "fix", "We could not read the ID's validity date.", "Retake the photo of the ID.")
        constitution = (reg or {}).get("constitution") or gst_f.get("constitution")
        prop = proprietor((reg or {}).get("legal_name") or gst_f.get("legal_name"))
        if prop:
            if id_f.get("name") and not same(id_f["name"], prop):
                add("signatory.proprietor", "hard", "fail", "review", f"For a proprietorship the signatory must be the proprietor ({prop}).",
                    "Upload the proprietor's ID.", {"id_name": id_f.get("name"), "proprietor": prop})
            elif id_f.get("name"):
                add("signatory.proprietor", "hard", "pass", "review", "Signatory is the proprietor.")
        elif constitution and constitution != "Proprietorship" and norm(id_f.get("designation")) in ("owner", "office admin", "manager"):
            add("signatory.authority", "soft", "warn", "note",
                f"For a {constitution}, keep an authorisation letter or board resolution naming the signatory.", None,
                {"designation": id_f.get("designation")})
        if business and id_f.get("business") and not same(id_f["business"], business):
            add("signatory.business", "hard", "fail", "review", "The ID is for a different business.", "Upload the ID issued for this business.")

    hard_fails = [c for c in checks if c.level == "hard" and c.status == "fail"]
    if any(c.severity == "review" for c in hard_fails):
        outcome = "review"
    elif hard_fails:
        outcome = "fix_needed"
    else:
        outcome = "verified"
    extracted = {dt: (dict(docs[dt].fields) if docs.get(dt) else None) for dt in DOC_TYPES}  # copy: never mutate cached reads
    for dt, f in extracted.items():
        if f and f.get("gstin"):
            f["gstin"] = mask_gstin(f["gstin"]) if gstin_valid(f["gstin"]) else f["gstin"][:4] + "*******"
        if f and f.get("udyam_number"):
            f["udyam_number"] = mask_udyam(f["udyam_number"])
        if f and f.get("id_no"):
            f["id_no"] = f["id_no"][:3] + "****" + f["id_no"][-2:]
        if f and f.get("consumer_no"):
            f["consumer_no"] = "******" + f["consumer_no"][-4:]
    return Result(outcome, checks, registry, extracted, route)
