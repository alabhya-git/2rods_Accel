# Data privacy and security choices

**Dukaan Connect** — designed to the Digital Personal Data Protection Act, 2023 and the DPDP Rules, 2025 (notified 13 November 2025; most obligations apply from about May 2027). Data is synthetic, but treated as real.

**1. Collect only what each step needs.**

| Step | Data | Why |
|---|---|---|
| Advisor | Business type, staff, sites, city, pin code, GSTIN (optional) | Pick an eligible bundle; GSTIN pre-fills the business from the registry |
| Order | Mobile number | Updates and the signatory SIM-swap check |
| KYC | Only what the chosen route needs: GSTIN, or Udyam, or a shop licence; a bill; from the ID only name, ID number, validity | Verify the business and signatory; no GST is a route, not a refusal |
| Business SIMs | Each SIM user's name and mobile number; they verify themselves through their own link | DoT requires end-user KYC before a business SIM goes live |

Never collected: Aadhaar number, face images, date of birth, bank details (UPI handles payment).

**2. Consent before processing.** A standalone notice in the owner's language, one switch per purpose: verify my business and install and bill (needed); AI reading of business documents, updates about this order, and offers (optional; offers off by default). Each choice is stored with notice version, time and channel. Withdrawal is one tap in the tracker, as easy as giving it. Nothing is uploaded or detokenised for a purpose without a live consent for it.

**3. Tokens in transit.** Raw identifiers enter once, at the API, and are replaced by random tokens (`tok_gstin_…`). Orders, tracker, back-office, analytics and the language model only see tokens or masked values (`37LD********1ZB`). Only the KYC service and fulfilment may detokenise, each for its own purpose; every attempt, allowed or denied, is audited. A keyed hash (HMAC-SHA256) supports lookups and duplicate checks without the raw value.

**4. Encryption at rest.** AES-256-GCM envelope encryption: every vault entry and every document has its own data key, wrapped by a key-encryption key derived from a master key held in Secret Manager or KMS. Buckets and databases hold only ciphertext. TLS on every hop.

**5. The AI boundary.** In chat, the language model receives masked text and tokens, never a raw GSTIN or phone number. Documents are read on our own servers first (Tesseract). Only if the owner says yes to *AI reading of business documents* does Claude (Anthropic, outside India) also read GST, Udyam, shop-licence or bill photos; **ID card photos are never sent**. Saying no costs time, not access: our reader and a person check instead. The model cannot set prices or products: it writes slots that the server fills from the rules engine, and any number, price, product name or promise in its own words is rejected.

**6. Who sees what.** The owner: everything about their own order. Staff sign in as themselves with a role (partner, reviewer, ops, admin); every action is audited under their name. Partners: only their own leads and call-back requests, masked; calls go through a masked virtual number. Reviewers: masked identifiers and the failed checks; risky overrides need a second reviewer. Engineers: masked logs (a filter redacts GSTIN, PAN, phone, Aadhaar-like and ID patterns). Tokens are never shared between orders, so erasing one order cannot affect another.

**7. Retention.** Document photos are crypto-shredded (data key destroyed, file deleted) 30 days after upload, unless telecom KYC record-keeping requires longer; checked fields stay encrypted for the contract. Abandoned conversations are purged after 30 days. An hourly job enforces this.

**8. Rights.** From the tracker: see and download my data, withdraw any consent, erase my data (identifiers and documents are crypto-shredded). Grievances are answered within the 90 days the Rules allow; we target 7.

**9. Breach response.** Tell affected owners without delay; initial notice to the Data Protection Board without delay and a detailed report within 72 hours (Rule 7). Audit logs and per-record keys limit the blast radius.

**10. Fraud controls.** GSTIN checksum and live registry status (22 customers last quarter held a cancelled or suspended GSTIN), cross-document name and address matching, tamper signals, SIM swap in the last 72 hours on the signatory's number, and a human review queue.

**Tested, not just written.** The test suite checks that the advisor never sees a raw identifier, that detokenising for the wrong purpose is refused and audited, that withdrawn consent blocks KYC, and that erasure leaves only ciphertext with no key.

**11. Security.** Signed staff tokens, rate limits, a strict Content Security Policy, signed and deduplicated WhatsApp webhooks, and a production start-up check that refuses demo settings (judge mode, demo staff, open CORS, mock adapters).

**Prototype vs production.** Real: rules engine, payment schedule, OCR, KYC decisions, vault, consent ledger, staff roles, call-back tasks; Claude and Sarvam when keys are set. Mocked: GSTIN and Udyam registries (the supplied data), DigiLocker, end-user e-KYC, SIM swap, masked calling, payments (test mode). Production: Cloud Run and Cloud SQL in Mumbai with backups in Delhi; master key in Secret Manager with a Cloud KMS key ring provisioned for envelope wrapping; data-processing terms with every vendor (Google Cloud, Anthropic, Sarvam, Meta, Razorpay).
