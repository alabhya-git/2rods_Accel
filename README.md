# Accel Business · Udyam Digital

**Four doors, one order.** A small business owner chooses *Help me choose*, *I know what I need*, *Talk to a person* or *WhatsApp*: in any of 10 languages, by text or voice, on the web, a phone or WhatsApp. Every door ends in the same honest quote, the right proof route, a booked install, and one account afterwards.

Built for Airtel SYNC, Track A: *Project Udyam Digital*. Accel Telecom and Accel Business are fictional; all data is the official synthetic pack. Payments run in test mode.

| | |
|---|---|
| Live demo | https://udyam-demo-ux45wjd45q-el.a.run.app (Cloud Run, Mumbai) |
| Owner app | `/` (four doors) · `/express` · `/help` · `/orders` |
| Partner desk | `/partner`: `PARTNER-001` / `partner-demo`, reviewers `reviewer-1` and `reviewer-2` / `review-demo` (demo only) |
| Judge console | `/judge`: advisor scenarios and the 12 KYC specimens, live |
| API docs | `/docs` |

## What changed since round 1, and why

Two independent evaluations (Claude and Codex) found the same blockers. Each is now fixed and covered by a test.

| Finding | Now |
|---|---|
| KYC passed four unrelated screenshots (fail-open) | Unrecognised pages and missing essential fields fail closed: a fix or a person, never *verified* (`tests/test_trust.py`, full upload + OCR path) |
| No-GST owners shut out (1,466 leads; 2,913 lack GST or Udyam) | Proof routes: GST, Udyam (DigiLocker or photo), shop licence (always reviewed); GST-only products refused on non-GST routes |
| Business SIMs went live without end-user KYC (DoT, 31 Aug 2023) | Each SIM user verifies through their own link; the line stays on hold until then |
| Registry status only checked once | GSTIN re-checked at the moment of activation; a cancelled GSTIN puts the product on hold |
| "Talk to a person" did nothing | An owned call-back task with number, window, language and summary, in the partner desk queue |
| Corrections didn't stick ("only internet" kept email); sites undercounted | Negated clauses remove needs and keep them out of defaults; sites add up across clauses |
| Hindi spellings of WhatsApp ignored in AI-off mode | Loanwords matched by consonant skeleton in all 10 scripts, so variants like व्हाट्सऐप work |
| Quote, charge and mandate disagreed; budget ignored GST | One payment schedule in paise behind every amount; idempotent payment; budget all-in (10,000-cart property test) |
| Model could state prices and promises in free text | Facts by construction: the model writes `{{slots}}`, the server fills them; digits, prices, product names and promise words outside slots are rejected |
| Open reset, shared passcode, unsigned webhooks, open CORS | Signed staff roles, admin-only reset, two-reviewer overrides, WhatsApp signature + dedupe, rate limits, CSP; production refuses demo settings |
| Erasing one order broke another; tracker events before commit; no cross-instance relay | Per-order tokens; events published after commit; Redis relay between instances |

## How it works

- **Advisor:** a deterministic rules engine owns eligibility, quantity and price. Claude Opus 5.5 (official SDK, cached system prompt, low effort, refusal fallback) asks and explains through tools, and writes numbers only as slots. After a recommendation, the engine finds the assumptions that move the price most and offers them as one-tap questions (typed profile patches with a quote diff). With no key, the same engine runs a rules-only advisor in all 10 languages. The engine keeps what the owner asked for: a feature they name (roaming, data per SIM) picks the plan that has it and survives budget cuts; a speed they name gets the slowest line that meets it, and a budget never quietly trades it away: when the budget can't pay for that speed, the advisor says so and offers the best line inside the budget; a leased line is never added just to unlock an add-on; and a rule that blocks one product gets an explanation and the rest of the bundle, never a hand-off.
- **Smart KYC:** local OCR (Tesseract + OpenCV) is the first reader. With the owner's separate consent, Claude vision is a second reader for **business documents only** (never ID cards); fields both readers disagree on, or pages that look edited, go to a person. Validators follow the dataset's own rules (PAN 'X', Udyam district 00, 15 July 2026 as "today").
- **Money:** `engine/schedule.py` turns a quote into dated debits; due today, instalments (summing exactly to setup), mandate limit and invoice lines are read from it.
- **Voice:** Sarvam speech in 10 languages through the server (key never in the browser), browser speech as fallback; heard words are shown for confirmation. WhatsApp voice notes are transcribed and answered.
- **Privacy:** token vault with AES-256-GCM and per-record keys; consent checked per action; self-serve rights (see, download, erase, withdraw); the LLM sees masked text and tokens in chat.
## The hidden pain points, from the leads data

| Pain | Evidence (`smb_leads.csv` unless noted) | What the app does | Test |
|---|---|---|---|
| The person ordering isn't the owner | 59% of leads are managers, admins or partners; "owner had no time for a visit" drops 531 leads | *I work here*: staff prepare the order, the owner gets a link and approves with Aadhaar e-sign from anywhere. Nothing is charged before; the e-sign covers the payment schedule's hash, so what they approved is what gets charged | `test_staff_order_cannot_be_charged_until_the_owner_approves` |
| KYC wants GST *and* Udyam | 58% lack one; quote-to-KYC is 21% with neither, 84% with both | Three proof routes (GST, Udyam, shop licence). On the shop-licence route, a nudge to free Udyam registration (Aadhaar + PAN, 10 minutes) turns a next-day review into an automatic check | `test_kyc_specimens.py` |
| Existing Accel customers treated as strangers | 38% already use Accel; they activate at 9.2% vs 6.3% and cost 18% less, yet 16% are lost as "unreachable" | Recognised after the network verifies the number (never from a typed number): *welcome back*, and their existing numbers become business SIMs with KYC already on file, live at once | `test_existing_customer_is_recognised_and_their_numbers_become_business_sims` |
| Rented shop: the bill is in the landlord's name | Not measured in the data. Before, our own KYC said "upload a rent agreement" with nowhere to upload one | A fix the owner can make alone: the landlord confirms through a link with Aadhaar e-sign (their name must match the bill), or the owner uploads a rent agreement naming the landlord, the business and the address. KYC then passes without a person. Demo applicant **K02R** | `test_landlord_link_verifies_kyc_without_a_review`, `test_rent_agreement_*` |
| Each SIM user needs their own KYC | DoT, 31 Aug 2023 | Per-user verification links; lines held until verified; existing Accel numbers skip it | `test_api_journey.py` |
| Fear of scams | Not in the data: owners are asked for documents and UPI details by callers they cannot check | Every call-back has a 4-digit code the caller must say first; *Check it's us* verifies a partner ID or calling number; "who opened your documents" from the audit log; "we never ask for OTP or PIN" on every money and document screen | `test_call_back_has_a_code_*`, `test_access_log_*` |
| Products need setup after install | Churn: website 37.5%, guest Wi-Fi 23%, WhatsApp Business 22%, against 15% overall | *Set up* is tracked like *installed*: guided tasks, "do it with me" call, WhatsApp nudge on day 3, expert call on day 7, and an ops queue of live-but-not-set-up customers | `test_setup_is_tracked_after_go_live` |

```
Owner web app · WhatsApp · Voice · Partner desk
            │ Cloudflare (TLS, WAF, Turnstile)
   Cloud Run, Mumbai ── API (FastAPI): rules engine, advisor tools, schedule, KYC, orders, care
            │                └─ voice gateway · workers · scheduled jobs
   Cloud SQL Postgres · PII vault + Cloud KMS · Cloud Storage (CMEK) · Redis · Secret Manager
   Adapters (real or mock): Claude · Sarvam · Razorpay · WhatsApp · Firebase OTP · GSTIN/Udyam · DigiLocker · BSS
```

## Real and mocked

| Real | Mocked (by design for the hackathon) |
|---|---|
| Rules engine, payment schedule, OCR, KYC decisions, vault and consent, staff roles, call-back tasks, tracker, Claude (with a key), Sarvam (with a key), WhatsApp webhook (with a Meta app) | GSTIN and Udyam registries (the supplied CSVs), DigiLocker, Aadhaar e-sign, Accel's subscriber base (demo numbers 9876500001 and 9876500002), operator end-user e-KYC, installer dispatch, billing system, SIM-swap check, payment provider (test-mode adapter) |

## Run it

```bash
# API (Python 3.12, Tesseract installed)
cd api && pip install -r requirements-dev.txt && uvicorn app.main:app --reload
# Web app
cd web && npm ci && npm run dev        # or npm run build; the API serves web/dist at /
# Tests: 987, including the 744-case invariant eval and the 10,000-cart money test
cd api && python -m pytest -q
```

Optional keys (`.env`): `LLM_PROVIDER=anthropic` + `LLM_API_KEY` (Claude), `SARVAM_API_KEY` (voice), `WHATSAPP_*` (Meta Cloud API). Without them the app runs rules-only with browser speech.

## The demo path (Ramesh, no-GST kirana, Jaipur)

1. `/` → *Help me choose* in Hindi: "जयपुर में किराना दुकान, 3 लोग, जीएसटी नहीं, व्हाट्सऐप पर ऑर्डर" → one question that changes the price → bundle, with the WhatsApp API refused for GST.
2. Quote: all-in monthly, due today, and "vs what you pay today".
3. KYC: route *Shop licence only* → fixes in Hindi → review by a person (partner desk).
4. Partner desk: the call-back request and the review queue (two reviewers for risky overrides).
5. Tracker: SIM users verify through their links → lines go live → *My account* (one bill, Get help).
6. Switch the AI off: the same quote, from the rules-only advisor.

Pain-point demos: on the quote, use **9876500001** (an existing Accel customer) and *I work here* with any other number as the owner's; in KYC, specimen **K02R** (rented clinic, bill in the landlord's name); `/verify` to check a caller.

## Deploy

- `infra/terraform/`: Cloud Run, Cloud SQL Postgres 16 (PITR, backups to Delhi), Secret Manager, Cloud KMS, private CMEK bucket, Artifact Registry, least-privilege service account. `environment = demo | prod`.
- `.github/workflows/ci.yml`: tests, web build, gitleaks, Semgrep, pip-audit, Trivy; canary deploy of the judge demo via Workload Identity Federation (no keys in CI).
- See [deploy/cloud-run.md](deploy/cloud-run.md) for the manual path.

**Submission documents:** [business case deck](docs/deck/udyam-digital-business-case.pdf) · [demo video](docs/video/udyam-digital-demo.mp4) · [architecture](docs/architecture.svg) · [privacy note](docs/privacy-note.md)
