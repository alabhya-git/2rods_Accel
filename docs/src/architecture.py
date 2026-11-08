"""Generates docs/architecture.svg (1920x1080). Render to PNG with docs/src/render.py."""
from pathlib import Path
from xml.sax.saxutils import escape

INK, SOFT, RULE, LEDGER, KUMKUM, HALDI, LEAF, TINT = "#1B1F3B", "#4A4F6E", "#D5DEEE", "#2B4C8C", "#C8102E", "#F2A900", "#1E7B4F", "#F6F8FC"
out: list[str] = []


def text(x, y, s, size=18, weight=400, color=INK, anchor="start"):
    out.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(s)}</text>')


def box(x, y, w, h, title, lines=(), fill="#fff", stroke=RULE, sw=1.5, badge=None, dashed=False, tsize=20, t0=32, l0=58, lh=23):
    dash = ' stroke-dasharray="7 6"' if dashed else ""
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dash}/>')
    tx = x + 16
    text(tx, y + t0, title, tsize, 700)
    for i, ln in enumerate(lines):
        text(tx, y + l0 + i * lh, ln, 16.5, 400, SOFT)
    if badge:
        for j, b in enumerate(badge):
            cx = x + w - 22 - j * 30
            out.append(f'<circle cx="{cx}" cy="{y + 24}" r="12" fill="{KUMKUM}"/>')
            text(cx, y + 30, str(b), 15, 700, "#fff", "middle")


def arrow(x1, y1, x2, y2, color=SOFT, both=False, w=2):
    mk = {SOFT: "a", KUMKUM: "r", LEAF: "g"}[color]
    m = f' marker-start="url(#{mk})"' if both else ""
    out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}" marker-end="url(#{mk})"{m}/>')


def label(x, y, s, color=SOFT, anchor="middle"):
    text(x, y, s, 14, 600, color, anchor)


W, H = 1920, 1000
out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="&quot;Baloo 2&quot;, sans-serif">')
out.append('<defs>' + "".join(f'<marker id="{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{c}"/></marker>' for i, c in (("a", SOFT), ("r", KUMKUM), ("g", LEAF))) + '</defs>')
out.append(f'<rect width="{W}" height="{H}" fill="#fff"/>')
text(60, 78, "Dukaan Connect: solution architecture", 42, 800)
text(60, 118, "Raw identifiers stop at the gateway. Only Smart KYC and fulfilment detokenise; the language model sees masked text only.", 22, 400, SOFT)

# channels
chan = [("Phone web app", ["PWA, 10 Indian languages", "voice in and read-aloud"]),
        ("WhatsApp", ["Cloud API webhook", "same advisor, same rules"]),
        ("Partner assist", ["same app under a partner ID", "commission on digital closes"]),
        ("Partner desk", ["callback queue, KYC reviews,", "metrics, masked calls"])]
text(60, 168, "Channels", 18, 700, SOFT)
for i, (t, ls) in enumerate(chan):
    y = 190 + i * 124
    box(60, y, 300, 108, t, ls)
    arrow(360, y + 54, 398, y + 54)

# gateway
out.append(f'<rect x="400" y="190" width="210" height="480" rx="10" fill="{KUMKUM}" fill-opacity="0.08" stroke="{KUMKUM}" stroke-width="2.5"/>')
text(418, 226, "API gateway", 21, 800)
text(418, 252, "and token vault", 21, 800)
gy = 296
for grp in (["TLS on every hop"], ["consent checked for", "each purpose"], ["GSTIN, Udyam no.,", "phone, ID number and", "address become", "random tokens"], ["keyed-hash index", "for lookups"], ["rate limits and", "log redaction"]):
    for ln in grp:
        text(418, gy, ln, 16.5, 400, SOFT); gy += 23
    gy += 16
for y in (270, 430, 590):
    arrow(610, y, 646, y)

# core services
out.append(f'<rect x="648" y="160" width="672" height="520" rx="12" fill="{TINT}" stroke="{RULE}" stroke-width="1.5"/>')
text(666, 190, "Core services (FastAPI, stateless): see only tokens or masked values", 18, 700, SOFT)
core = [
    (666, 206, "Advisor agent", ["LLM tool calls: update_profile,", "recommend, explain_product", "rules-only fallback, 10 languages"], [1]),
    (1004, 206, "Rules engine", ["catalogue as knowledge graph:", "eligibility, dependencies,", "quantities, price; guard"], [1]),
    (666, 362, "Quote and order", ["one monthly price, add-ons,", "re-priced on the server,", "UPI Autopay, install slot"], [3]),
    (1004, 362, "Smart KYC", ["quality gate, deskew, OCR,", "checksum self-heal, registry", "and cross-document checks"], [2]),
    (666, 518, "Tracker", ["every step an event;", "SSE to the app, WhatsApp push,", "Redis bus across instances"], [3]),
    (1004, 518, "Back-office", ["propensity score (AUC 0.71),", "review queue, masked calling,", "metrics against baseline"], [4]),
]
for x, y, t, ls, b in core:
    box(x, y, 298, 142, t, ls, badge=b)
arrow(966, 286, 1002, 286)
label(984, 274, "tools")

# adapters
out.append(f'<rect x="1360" y="160" width="500" height="520" rx="12" fill="#fff" stroke="{RULE}" stroke-width="1.5"/>')
text(1378, 190, "Adapters (dashed = mocked in the prototype)", 18, 700, SOFT)
adapters = [
    ("Registries", ["GSTIN and Udyam lookups; DigiLocker", "for the Udyam certificate"], [2]),
    ("Network APIs", ["SIM swap and number verification", "(CAMARA); fibre serviceability"], [2]),
    ("CPaaS", ["masked virtual numbers for partner", "calls; WhatsApp updates"], [4, 3]),
    ("Payments and legacy systems", ["UPI Autopay; CRM, billing, order", "management, field-force scheduling"], [3]),
    ("LLM provider", ["Claude, Gemini or OpenAI-compatible;", "receives masked text only"], [1]),
]
for i, (t, ls, b) in enumerate(adapters):
    y = 206 + i * 92
    box(1378, y, 464, 84, t, ls, dashed=(t != "LLM provider"), badge=b, tsize=19, t0=27, l0=51, lh=21)
    arrow(1322, y + 42, 1376, y + 42, KUMKUM if t != "LLM provider" else LEAF, w=2.5)
# arrow legend under the adapters column
out.append(f'<line x1="1378" y1="{700}" x2="1408" y2="{700}" stroke="{KUMKUM}" stroke-width="2.5"/>')
text(1416, 705, "detokenised for its own purpose", 15, 600, KUMKUM)
out.append(f'<line x1="1676" y1="{700}" x2="1706" y2="{700}" stroke="{LEAF}" stroke-width="2.5"/>')
text(1714, 705, "masked text only", 15, 600, LEAF)

# data
out.append(f'<rect x="648" y="716" width="672" height="196" rx="12" fill="#fff" stroke="{RULE}" stroke-width="1.5"/>')
text(666, 746, "Data, in an India region", 18, 700, SOFT)
arrow(984, 682, 984, 714)
data = [("Postgres", ["tokens, encrypted", "columns, events"]), ("Documents", ["AES-256-GCM,", "one key per file"]),
        ("Consent ledger", ["purpose, notice", "version, audit log"]), ("Key service", ["KMS master key,", "crypto-shredding"])]
for i, (t, ls) in enumerate(data):
    box(666 + i * 162, 762, 152, 132, t, ls, tsize=19)

# flows legend
out.append(f'<rect x="60" y="716" width="550" height="196" rx="12" fill="#fff" stroke="{RULE}" stroke-width="1.5"/>')
text(78, 746, "Four flows", 18, 700, SOFT)
flows = [("Advise", "owner message, advisor calls the rules engine, quote"),
         ("Verify", "consent, encrypted upload, OCR, registries, fix hints"),
         ("Fulfil", "order, payment, legacy order management, live tracker"),
         ("Recover", "stalled leads with consent, ranked, masked call")]
for i, (n, d) in enumerate(flows):
    y = 782 + i * 32
    out.append(f'<circle cx="92" cy="{y - 6}" r="12" fill="{KUMKUM}"/>')
    text(92, y, str(i + 1), 15, 700, "#fff", "middle")
    text(114, y, n, 18, 700)
    text(196, y, d, 17, 400, SOFT)

# deployment
out.append(f'<rect x="1360" y="716" width="500" height="196" rx="12" fill="{LEDGER}" fill-opacity="0.06" stroke="{LEDGER}" stroke-width="1.5"/>')
text(1378, 746, "Deployment", 18, 700, SOFT)
for i, ln in enumerate(["One Docker image on Cloud Run, asia-south1 (Mumbai)", "autoscaling 1 to 10 instances, min 1 warm",
                        "Postgres and Redis; secrets in Secret Manager", "CI: 82 tests (28 scenarios, 12 KYC specimens)",
                        "works with no LLM key: rules-only mode"]):
    text(1378, 782 + i * 27, ln, 17, 400, INK)

text(60, 960, "Dukaan Connect is our product prototype; all data is the official synthetic pack. Airtel SYNC, Track A: Project Udyam Digital.", 16, 400, "#8A8FA8")
out.append("</svg>")
Path(__file__).resolve().parents[1].joinpath("architecture.svg").write_text("\n".join(out), encoding="utf-8")
print("ok")
