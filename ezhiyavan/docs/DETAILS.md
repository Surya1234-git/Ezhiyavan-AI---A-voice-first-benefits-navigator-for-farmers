# Ezhiyavan AI – detailed engineering notes (moved from the old README; the short overview is `../README.md`)

Voice-first, multilingual (Tamil / English / Hindi) benefits navigator.
**Rules-as-data**: an LLM/parser only *extracts* facts, the farmer confirms them, a deterministic engine decides.

## Run
```bash
# backend (Python 3.11+)
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))")
# DEMO mode only (dev OTP shown on screen, unverified demo rules active):
ENV=dev ALLOW_UNVERIFIED=1 uvicorn app.main:app --reload     # http://localhost:8000/docs
# PostgreSQL: export DATABASE_URL=postgresql+psycopg2://user:pass@host/db  (default: SQLite)

# frontend (Node 18+)
cd frontend && npm install && npm run dev   # http://localhost:5173 (proxies /api)
```
Tests: `cd backend && python -m unittest tests.py` (engine, validator, family/conflicts/estimate, governance/approvals, redaction, real English OCR incl. rotated/skewed/noisy scans and scanned PDF, extraction, key rotation, backups, audit triggers, security – 174 pass)
and `pip install httpx pytest && pytest tests_api.py` (auth, ownership/IDOR, uploads, CORS, OTP rate limit – **written but not yet run**).

## AI extraction
Set `ANTHROPIC_API_KEY` (and optionally `LLM_MODEL`, default `claude-sonnet-5-5`) to enable LLM extraction in `app/extract.py`. It extracts one field per answer,
treats farmer text as untrusted, validates output strictly, compares with the rule-based parser (disagreement => "low confidence" warning), falls back to rules on any failure,
and the farmer always confirms. The LLM never decides eligibility. Not yet measured: accuracy across accents/dialects – build a labelled test set before claiming numbers.
Scheme files can use `any`/`all` groups, `effective_from`, `expires`, `applicable_states`, `benefit_detail {amount_inr, frequency, verified}`, `deadline` (see `engine.py`).

## Version 7: evidence, not features
- **Readiness register** (`app/readiness.py`, admin screen): 16 checks. Scheme checks are computed from the live files; Tamil OCR and the multilingual benchmark can only be passed by attaching the JSON report from `eval/doc_eval.py --json` / `eval/run_eval.py --split test --final --json out.json`, which must show real Tamil documents with Tamil data actually used (no fallback), >=150 documents, >=95% classification/field accuracy, **0 high-confidence wrong values**, a final run on the held-out test split of real-consented cases, Tamil/Tanglish/English/Hindi all present and **0 unsafe wrong values**. Everything else needs evidence text/URL, a test date and a reviewer who is not the person recording. Today 1 of 16 passes (expired schemes are excluded); that is the honest number.
- **Leak-proof benchmark**: `eval/run_eval.py` scores only dev+val by default; the test split is locked behind `--final`, every final run is logged with the cases-file hash, and a changed file triggers a warning. It reports **unsafe wrong values** (a non-empty wrong answer, e.g. a son's tax status given to the applicant) separately from safe abstentions. It already caught a real unsafe case from the review (Tamil dative 'மகனுக்கு'), now fixed with a general third-person safety net. Cases may carry `"provenance": "real-consented"`; the bundled file is synthetic.
- **OCR language honesty**: Tesseract silently runs without a missing language (e.g. `tam`); the code now checks which data is installed and `doc_eval` reports requested vs actually-used languages and fallback counts. Without Tamil data installed, a Tamil evaluation cannot pass.
- **Shared rate limiting** (`REDIS_URL`, `pip install redis`) with automatic per-process fallback if Redis fails (counted), plus scrubbed JSON logs (Aadhaar/PAN/bank/phone/e-mail/OTP masked), counters (`/api/admin/metrics`), `/healthz` and an optional `ALERT_WEBHOOK_URL`. Real Redis and the webhook are untested.
- **Application timeline**: prepared -> submitted -> under review -> decision, every step labelled self-reported and never official; `under_review` status added. Claim pack shows verification date or the plain 'not officially verified' box, evidence/page references and the timeline.
- **Verified-scheme path**: `fixtures/make_verified_fixture.py` creates fictional verified/draft/expired schemes (`SCHEME_DIR=...`, `ALLOW_UNVERIFIED=0`); engine-level tests cover hidden drafts/expired schemes, evidence pages, member consent and expiry-between-steps. `frontend/e2e/verified_farmer_journey.py` runs the browser version against the real backend (written, not run).
- **Frontend checks (mocked API, real Chromium)**: no horizontal overflow at 320/360/390/768/1024/1440px and at 320px with 200% zoom, keyboard Tab never loses focus, every control has an accessible name, admin readiness screen, timeline, and the app shell loads offline via the service worker. Offline use is **app shell only**: no offline profile access or drafting.
- Review worksheets for all seven schemes: `docs/review_worksheets/`.

## What remains for a 10/10 (and the tooling for each)
1. **Scheme verification** (human work): `python backend/scripts/review_worksheet.py PM_KISAN` prints a per-rule checklist with evidence status and blockers. I could not read the official PM-KISAN guideline PDFs (robots.txt blocked automated access from my environment), so no page numbers were added. Never weaken the approval blockers.
2. **Income tax per person** (done, synthetic-tested): the farmer is asked separately about themselves, their spouse and other household members. 'My son pays' fills only the other-members flag (manual check), never the applicant; pronouns ('he pays') are treated as someone else; 'nobody' answers all three; one child not paying never clears the household. Known limits: pronouns/relations beyond the lists, rare Tamil/Hindi inflections and sarcasm are not handled - measure on real speech.
3. **Tamil OCR validation**: install Tesseract `tam` data (`OCR_LANGS=tam+eng`), collect consented anonymised documents with label files and run `python backend/eval/doc_eval.py <folder>` (classification accuracy and abstentions, exact-match fields, wrong values incl. high-confidence-wrong, missing values, farmer correction rate, per tag such as district/scan quality). The harness itself is tested on synthetic English images only.
4. **Real-backend journey**: `frontend/e2e/real_backend_journey.py` (instructions in its header) covers registration -> questions -> family -> upload -> discovery -> claim pack -> tracking -> deletion. **Written, not run.**
5. **Production**: see `docs/PRODUCTION_READINESS.md` (per-item status) and `deploy/cron.example` (retention + backups). Alembic, PostgreSQL restore drill, live OTP and independent security review remain open.
6. **Pilot**: `pilot/` has the consent/measurement protocol, a session log template and `analyze.py`, which prints n beside every figure and withholds percentages under 20 sessions. No pilot has been run.

## Scheme governance (can farmers trust what they see?)
- Each scheme has `source_evidence` (title, https url, document_date, page/section, rule_ids) and `conditions_complete`. **Approval is blocked** unless every rule - including every exclusion - is covered by evidence with a page or section, dates are valid, conditions are marked complete, and (if an amount is marked verified) the amount has evidence.
- A brand-new scheme or any change to rules/benefit/states/dates is **high-impact: two different approvers, neither the submitter**; metadata-only changes need one. `GET /api/admin/schemes/{id}/diff` shows rule-by-rule changes against the last verified version and the blockers.
- Expired schemes are removed from farmer results automatically; `GET /api/admin/trust` (shown as a banner on `/#/admin`) says plainly whether everything shown to farmers is verified, evidenced and current.
- All seven shipped files are drafts with `conditions_complete: false`, so **none can be approved yet** - the system correctly refuses until a human has encoded the real conditions and filled in evidence pages. The PM-KISAN evidence entry deliberately has no page/date because I did not read the guideline text.
- Eligibility traces carry what the farmer reported, the rule ID and its evidence (or "source being checked"). Four separate levels are never merged: rules matched / documents supplied / a person looked at the document / government confirmed (always "no": no integration exists).

## Privacy, retention, backups
- Documents: Aadhaar, PAN and bank-account numbers are masked **before** classification/extraction and never returned or stored as text (`app/docs.py: redact`; over-masking is deliberate). The uploaded original file still contains them, so it is encrypted at rest (`FILE_ENC_KEY`) and purged on schedule.
- Retention: `python -m app.maintenance` (run daily) deletes documents older than `DOC_RETENTION_DAYS` (365), erases farmers inactive for `INACTIVE_RETENTION_DAYS` (730), and clears expired OTP/revoked-token rows. **Written but not run here (no SQLAlchemy in my sandbox)**; covered by tests in `tests_api.py`.
- Key rotation: `FILE_ENC_KEY` takes a comma list, newest first; `FILE_ENC_KEY="<new>,<old>" python scripts/rotate_key.py uploads` re-encrypts every file (tested), then drop the old key.
- Backups: `BACKUP_KEY=<fernet key> python scripts/backup.py backup ./backups` (SQLite tested: encrypted, wrong key fails, rotation keeps the newest N). PostgreSQL path uses `pg_dump` and is untested. Restore regularly to prove it works.
- Audit log is append-only at the app level and, on SQLite, via DB triggers (tested). A DB administrator can still drop triggers: in production use a separate write-only DB role or WORM storage.
- **Schema changes**: new columns (`last_active`, `created_at`, member attributes, `sha256`/`quality`) are not added to an existing database by `create_all`. Adopt Alembic before real data exists (not installed in my sandbox, so I did not generate migrations).

## Family discovery and claim pack
Member attributes (disability, widowed, student; unknown stays unknown and yields amber) feed member-level schemes. `conflicts_with` flags pensions a person may not be able to combine (flag only; the conflict notes in the drafts are my assumption and must be verified). `estimate` sums only **officially verified** amounts, counts conflicting schemes once, and is labelled an upper bound, not a promise; with the shipped drafts it is 0. `GET /api/me/claim-pack/{scheme}` returns a printable summary (checklist, steps, your confirmed facts; no phone/Aadhaar/PAN/bank numbers). The widow-pension and disability-assistance files are **placeholders**: real conditions (age, income, percentage, remarriage...) are NOT encoded.

## Browser end-to-end test
Real Chromium, **mocked API** (proves the UI flow, not the backend): bundle then run
```bash
cd frontend && npx esbuild src/main.tsx --bundle --outdir=/tmp/e2e --entry-names=bundle --jsx=automatic --loader:.css=css --minify --define:process.env.NODE_ENV='"production"'
cp public/* /tmp/e2e/ && pip install playwright && playwright install chromium && python e2e/farmer_journey.py /tmp/e2e
```
It covers: consent gating, OTP login, spoken/typed answers with confirm-before-save, results with unverified-rule labelling, claim pack, family consent payload, document upload + confirm-before-use, wallet reminders, logout, partner/admin login screens, no console errors, no horizontal overflow at 390px. It already caught a real mobile overflow bug. Not covered: real backend integration, other browsers, screen readers/accessibility audit, offline PWA behaviour, slow networks.

## Operator screens
`http://localhost:5173/#/partner` (help centres) and `/#/admin` (scheme reviewers): English UI, tokens held in memory only (a page refresh logs out). Partner: consented cases, answer unanswered questions with the farmer, review documents, notes. Admin: list all rules incl. pending, load JSON, submit with validation errors shown, approve (a different reviewer), audit log.
Create operator logins with the hash command under Production settings.

## Measuring AI accuracy
`python backend/eval/run_eval.py` scores extraction on `eval/cases.jsonl`. The bundled 105 cases (en 45, ta 33, hi 17, mixed 10) are **synthetic** (written by the developer, and the parser was tuned after the harness exposed bugs), so the ~97% it prints is NOT real-world accuracy. Replace with consented real farmer utterances per language/accent and report those. With `ANTHROPIC_API_KEY` set it also scores the LLM pipeline.
`POST /api/me/chat` extracts several facts from one message and returns proposals (never saved; contradictions with earlier answers are flagged).

## Extraction behaviour (Tamil, Tanglish, English, Hindi)
Land area is the quantity attached to a land unit ('3 kids, 2 acres' -> 2), with halves/quarters ('ஒன்றரை', 'ढाई', 'one and a half'), sums ('2 acres 50 cents'), cents/hectare conversion, spoken corrections ('...actually three'), and Tanglish numbers (rendu, naalu). 'I don't know' / 'தெரியாது' / 'पता नहीं' is **unknown**, never yes/no. Land said to be in another family member's name, approximate values and corrections lower confidence and are shown to the farmer. The confirm screen shows their own words, what was understood, the confidence and the warnings; nothing is saved until 'Correct'. Number-word coverage is partial (common words, not every Tamil compound); the 105 bundled eval cases are synthetic.

## Documents (OCR)
`pip install -r requirements-ocr.txt` + system Tesseract; set `OCR_LANGS=tam+eng` once Tamil data (`tesseract-ocr-tam`) is installed (falls back to English if missing). Scanned PDFs are rendered (pypdfium2, first 5 pages) and OCR'd; duplicates (same file hash) and low-resolution/low-confidence scans are flagged. English OCR end-to-end is tested; **Tamil OCR has not been tested** (no Tamil data in my environment). Without them the upload still works and the app asks the farmer to type the values.
Pipeline (`app/docs.py`): preprocess (contrast, denoise, deskew, orientation retry - tested on rotated/skewed/noisy English scans) -> read text -> classify (needs >=2 distinct keywords; ties/weak evidence = 'unknown', the farmer's chosen type is used) -> warnings (unusual/several areas, missing survey no., invalid or expired dates, poor OCR) and per-field confidence -> cross-document and profile consistency checks. Pipeline: read text -> classify (land record / income / community / bank passbook) -> extract fields -> list missing fields -> **farmer edits and confirms** -> saved as `confirmed`.
Account numbers and Aadhaar numbers are deliberately never extracted. Reading a document is not authenticity verification; the API and UI say so. 
Field extraction is regex-based and has **not been measured on real documents**; Tamil land records (chitta/adangal) vary by district, so collect samples and measure the correction rate before relying on it.

## Family, partners, reminders
- Member-level schemes (`"applies_to": "member"`, e.g. the pension draft) are evaluated separately for each member who has consent; household schemes use the household profile.
- CSC/NGO partners: `PARTNER_USERS` (same hash format as admins) -> `POST /api/partner/login`. A farmer grants/revokes access via `/api/me/consents`; partners see only consented cases, can add notes and enter profile answers (audited). Farmers can read who accessed their case at `/api/me/access-log`. The web screen is at `/#/partner`; entering or reviewing anything requires ticking that the farmer is present and agrees (the API rejects it otherwise), and a help centre can mark a document 'looks consistent / needs attention' – a human look, never official verification.
- `/api/me/reminders`: missing documents, scheme deadlines and document expiry (within 30 days). Delivery by SMS/WhatsApp/push is not built; reminders appear in the Benefits tab.

## Production settings
Also: `FILE_ENC_KEY` (Fernet key: `python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"`; uploads are encrypted at rest, and **production uploads are refused without it**), `TWILIO_SID/TWILIO_TOKEN/TWILIO_FROM` (SMS OTP adapter, untested against the live API; Indian SMS normally needs DLT registration so you may need a different gateway), `PARTNER_USERS`, `CLAMD_HOST` (ClamAV; upload fails closed if configured but unreachable), `TRUST_PROXY=1` behind a reverse proxy, `RATE_AUTH`/`RATE_API` (per-IP per-minute, in-memory per process).
Sessions are an HttpOnly, SameSite=Strict, Secure cookie plus a required `X-Requested-With` header on writes; the token is returned in the JSON body only in `ENV=dev`.

`SECRET_KEY` (required), `CORS_ORIGINS` (comma list, default localhost:5173), `ALLOW_UNVERIFIED=0` (default), no `ENV=dev`,
`ADMIN_USERS='{"alice":"salt$hash"}'` where hash = `python -c "import hashlib;print('SALT$'+hashlib.pbkdf2_hmac('sha256',b'PASSWORD',b'SALT',200000).hex())"`.
Real OTP needs an SMS provider wired into `request_otp` (returns 503 until then). Serve over HTTPS only.

## Admin / scheme governance
Admin login -> `POST /api/admin/schemes` saves a rule as `pending_review` (old version copied to `schemes/history/`) -> a **different** admin calls
`POST /api/admin/schemes/{id}/approve` -> status `verified` + `last_verified` date. Everything is in `GET /api/admin/audit`.
Shipped scheme files remain unverified demo drafts, so with defaults the app shows no schemes until a reviewer approves them against official sources.

## IMPORTANT – honesty notes
- Scheme files in `backend/schemes/*.json` are **demo drafts** (`"status": "demo_unverified"`), written from general public knowledge. They are NOT verified legal specifications. Before any real use, a reviewer must check each against the official source, set `last_verified`, and change status to `verified`. Set `ALLOW_UNVERIFIED=0` in production so only verified rules are active.
- Results are "potentially eligible / needs verification / condition not met" – never a guarantee. No percentage scores.
- The app does NOT submit applications. It links to official portals; the farmer records the reference number/status manually (labelled "self-reported").
- Not yet built: QR code in the claim pack (needs `pip install segno`; untested here),  Alembic migrations, Redis/gateway rate limits, refresh-token rotation (sessions are a 12h HttpOnly cookie with server-side revocation), error/security-event monitoring, SMS/WhatsApp/voice delivery and retries, offline profile access and drafting (the PWA caches only the app shell), low-data mode, Tamil OCR validation, a >=100-per-language real evaluation set, verified scheme rules (all shipped schemes are drafts), independent security review, Vite production build run, real-backend end-to-end tests, and the real-farmer pilot.

## Add a scheme without changing code
Use the admin flow above (or drop a verified JSON file in `backend/schemes/`). The next `/discover` call picks it up. Questions are asked only for fields the active rules need.
