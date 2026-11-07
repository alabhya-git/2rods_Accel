"""Facts by construction: the model writes slots, the server fills them.

Claude never types a number, a price, a product name or a promise. It writes
{{monthly_all_in}}, {{product:P04}}, {{line:P16}} and so on; the server renders each slot
from the rules engine's bundle and the payment schedule, in Indian number format. A
reply that carries a digit, a currency amount, a catalogue product name or a promise
word outside a slot is rejected and replaced by the template explanation. This is
stricter than parsing amounts back out of free text: there is nothing to parse.
"""
from __future__ import annotations

import re
import unicodedata

from ..data_store import store
from ..engine import schedule
from ..engine.pricing import gst, rupees
from ..engine.profile import Profile

SLOT = re.compile(r"\{\{\s*([a-z_]+)(?::([A-Za-z0-9_]+))?\s*\}\}")
CURRENCY = re.compile(r"₹|\brs\.?(?=\s|\d|$)|\binr\b|रु\.?|रुपये|रुपए|ரூ|రూ|ರೂ|રૂ|টাকা|രൂ|ਰੁ", re.I)
# promises only a contract can make: never in the model's own words
PROMISES = re.compile(
    r"\b(?:guarantee[ds]?|free(?:\s+of\s+cost)?|forever|lifetime|tomorrow|today itself|same day|instantly|discount(?:ed)?|"
    r"waive[ds]?|refund(?:ed)?|cashback|no (?:contract|lock-?in)|unlimited|99(?:\.\d)?\s?%|uptime|sla)\b|"
    r"गारंटी|मुफ़्त|मुफ्त|फ्री|छूट|डिस्काउंट|कल तक|आज ही|मोफत|சலுகை|இலவசம்|ఉచితం|ಉಚಿತ|મફત|বিনামূল্যে|സൗജന്യ|ਮੁਫ਼ਤ",
    re.I)

# the reply is for the owner: notes to itself about the profile, the owner or its tools are not
META = re.compile(r"\b(?:the owner(?:'s)?|profile|ask one question|tool (?:call|result)s?|the context|system prompt|"
                  r"update_profile|request_human|recommend tool)\b", re.I)

DAYS = {"en": "days", "hi": "दिन", "mr": "दिवस", "ta": "நாட்கள்", "te": "రోజులు", "kn": "ದಿನಗಳು", "gu": "દિવસ", "bn": "দিন",
        "ml": "ദിവസം", "pa": "ਦਿਨ"}

NAMES = ("monthly", "monthly_all_in", "gst", "setup", "due_today", "emi", "saving_24", "install_days",
         "product", "qty", "line", "budget", "current_spend", "vs_today", "employees", "sites", "city")


def has_digit(text: str) -> bool:
    return any(unicodedata.category(ch) == "Nd" for ch in text)


def problems(raw: str, bundle: dict | None) -> list[str]:
    """Why a model reply can't be shown as written. Empty list = safe to render."""
    out: list[str] = []
    known = {ln["product_id"] for ln in (bundle or {}).get("lines", [])} | \
            {e["product_id"] for e in (bundle or {}).get("exclusions", [])} | \
            {a["product_id"] for a in (bundle or {}).get("addons", [])}
    for m in SLOT.finditer(raw):
        name, arg = m.group(1), m.group(2)
        if name not in NAMES:
            out.append(f"unknown slot {name}")
        elif name in ("product", "qty", "line") and arg not in known:
            out.append(f"slot {name}:{arg} is not in the bundle")
        elif name not in ("product", "employees", "sites", "city") and not bundle:
            out.append(f"slot {name} before a bundle exists")
    bare = SLOT.sub(" ", raw)
    if has_digit(bare):
        out.append("a number outside a slot")
    if CURRENCY.search(bare):
        out.append("a currency amount outside a slot")
    low = bare.lower()
    for p in store().products.values():
        if p.name.lower() in low:
            out.append(f"product name '{p.name}' outside a slot")
    if re.search(r"\bP\d{2}\b", bare):
        out.append("internal product code shown to the owner")
    pm = PROMISES.search(bare)
    if pm:
        out.append(f"a promise word ('{pm.group(0)}')")
    mm = META.search(bare)
    if mm:
        out.append(f"talks about its own workings ('{mm.group(0)}')")
    return out


def render(raw: str, bundle: dict | None, profile: Profile) -> str:
    b = bundle or {}
    lines = {ln["product_id"]: ln for ln in b.get("lines", [])}
    names = {p.id: p.name for p in store().products.values()}
    monthly = int(b.get("monthly", 0))
    all_in = monthly + gst(monthly)
    sched = schedule.for_bundle(b, False) if b.get("lines") else None

    def value(name: str, arg: str | None) -> str:
        if name == "monthly":
            return rupees(monthly)
        if name == "monthly_all_in":
            return rupees(all_in)
        if name == "gst":
            return rupees(gst(monthly))
        if name == "setup":
            return rupees(int(b.get("setup", 0)))
        if name == "due_today":
            return schedule.rupees(sched["due_today"]) if sched else rupees(0)
        if name == "emi":
            return rupees(int(b.get("setup_emi", 0)))
        if name == "saving_24":
            return rupees(max(0, monthly - int(b.get("monthly_other_term", monthly))))
        if name == "install_days":  # the unit travels with the number, in the owner's language
            return f"{int(b.get('install_days', 0))} {DAYS.get(profile.language, DAYS['en'])}"
        if name == "product":
            return names.get(arg or "", "")
        if name == "qty":
            return str(lines.get(arg or "", {}).get("qty", ""))
        if name == "line":
            return rupees(int(lines.get(arg or "", {}).get("monthly", 0)))
        if name == "budget":
            return rupees(profile.budget or 0)
        if name == "current_spend":
            return rupees(profile.current_spend or 0)
        if name == "vs_today":
            return rupees(all_in - (profile.current_spend or 0))
        if name == "employees":
            return str(profile.employees or "")
        if name == "sites":
            return str(profile.n_sites)
        if name == "city":
            return profile.city or ""
        return ""

    return SLOT.sub(lambda m: value(m.group(1), m.group(2)), raw)


GUIDE = """How to write numbers, prices and product names: you never type them. Write slots and the server fills them.
{{monthly}} monthly price before GST · {{monthly_all_in}} monthly price with GST · {{gst}} the GST · {{setup}} one-time setup
{{due_today}} first payment · {{emi}} setup instalment per month · {{saving_24}} monthly saving on a 24-month plan
{{install_days}} time to go live (unit included) · {{product:ID}} a product's name · {{qty:ID}} its quantity · {{line:ID}} its monthly price
{{budget}} the owner's budget · {{current_spend}} what they pay today · {{vs_today}} new all-in minus today's spend
{{employees}} staff · {{sites}} sites · {{city}} city
IDs come from the recommend tool result. No digits, rupee signs, product names, discounts or promises (free, guaranteed, tomorrow, SLA) in your own words."""
