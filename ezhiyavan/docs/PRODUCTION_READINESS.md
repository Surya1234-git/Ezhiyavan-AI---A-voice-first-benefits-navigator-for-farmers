# Production readiness - honest status
The admin screen (`/#/admin` -> Production readiness, API `GET /api/admin/readiness`) is the live version of this table: its status comes from evidence, never a manual tick.
Legend: DONE+TESTED = exercised by an automated test in my environment; WRITTEN = code exists but was not run here; OPEN = not done.

| Area | Status |
|---|---|
| Scheme verification by humans, evidence pages, two-reviewer approval | Workflow DONE+TESTED (incl. a fictional verified fixture end to end at engine level). Real verification OPEN: all seven schemes are drafts and cannot be approved; worksheets are in `docs/review_worksheets/` |
| Expired schemes excluded, scheme expiring between profile and discovery | DONE+TESTED |
| Eligibility engine, explanations, family/member rules, conflicts, estimates, income tax per person | DONE+TESTED (synthetic cases) |
| Held-out evaluation: deterministic 70/15/15 split, locked test split, unsafe-error reporting, `--final` log | DONE+TESTED. A real, human-labelled 600-example benchmark is OPEN |
| English OCR incl. rotated/skewed/noisy/scanned PDF; fallback-language reporting (checks which language data is really installed) | DONE+TESTED. Tamil OCR on real documents OPEN (`eval/doc_eval.py`, needs `tam` data) |
| Sensitive-number masking, retention, key rotation, encrypted backups (SQLite), audit triggers (SQLite) | DONE+TESTED (retention job WRITTEN) |
| Readiness register (auto checks, report-driven checks, evidence + independent reviewer for the rest) | DONE+TESTED |
| Shared rate limiting (Redis backend, memory fallback, worker-sharing semantics) | Logic DONE+TESTED with a fake Redis; **real Redis WRITTEN, not run** |
| Log scrubbing, JSON logs, counters, health check, alert webhook | Scrubbing/counters DONE+TESTED; `/healthz`, metrics endpoint and webhook WRITTEN, not run live |
| API auth, ownership, CSRF header, consent, partner flow, timeline | WRITTEN (`tests_api.py` needs FastAPI/SQLAlchemy installed) |
| Frontend: type-check, bundle, mocked-API browser test at 320-1440px, 200% zoom, keyboard, accessible-name audit, app-shell offline load | DONE+TESTED. `npm run build` (Vite) and screen-reader testing OPEN |
| Real-backend journeys (`real_backend_journey.py`, `verified_farmer_journey.py`) | WRITTEN, not run |
| Alembic migrations | OPEN (not installed here; `create_all` does not alter existing tables) |
| PostgreSQL backup + restore drill | OPEN |
| SMS OTP (Twilio adapter; India needs DLT-registered sender) | WRITTEN, not tested live |
| Production key management (KMS/secret manager, rotation drills) | Mechanism DONE+TESTED; operating procedure OPEN |
| Independent security review, load test | OPEN |
| Supervised pilot | Kit in `pilot/`. OPEN |
| Plain-language result summary (headline, do-first, still-to-confirm, near miss) | Logic DONE+TESTED (unit tests); endpoint field WRITTEN, not run live; UI tested in real Chromium with a mocked API |
| Server-side validation of saved values (type and range) | Logic DONE+TESTED; wiring in `set_field` WRITTEN, not run live |
| Client-IP resolution for rate limiting (rightmost trusted proxy hop; forged leftmost entries ignored) | Logic DONE+TESTED; `TRUST_PROXY_HOPS` WRITTEN |
| OCR moved off the async event loop (thread pool) | WRITTEN, not run |
| "Report a wrong rule" (farmer) + admin review list | Endpoints WRITTEN, not run live; UI tested with a mocked API |
| Anonymised impact dashboard | Aggregation DONE+TESTED (unit); endpoint WRITTEN, not run live; small-sample flag below 5 farmers |
| Docker, docker-compose, Makefile, GitHub Actions CI, `seed_demo.py` | WRITTEN, not run |
| KCC and PM-JAY rule corrections (tenant / allied-activity farmers; age 70+), skip of redundant questions | DONE+TESTED (unit); sources are in the worksheets and still need human confirmation |
| Evidence notes and draft evidence for PM-KISAN, KCC, PM-JAY | WRITTEN; page/section left blank for a human reviewer; nothing is verified |
| UI safety fixes: confirmed delete, inline messages instead of pop-ups, accessible badge colours with icons | DONE; tested in real Chromium with a mocked API (delete cancel and confirm are both covered) |
| Rule audit of all seven drafts | DONE as research (`docs/RULE_AUDIT.md`); nothing verified |

| Results card redesign (tick-list, draft banner, details expander) | DONE; tested in real Chromium with a mocked API |
| PM-KISAN evidence cited by FAQ question number (2021 FAQ read in full); NRI claim retracted; scheme still a draft | DONE as research; needs human reviewers |
| UI pass: SVG icons instead of emoji, no inline styles, design tokens, Do-this-first panel, welcome language buttons | DONE; tested in real Chromium with a mocked API; not yet seen on a real phone |
| Tab bar, progress and Back, listening state, skeletons, logo, welcome strings translated | DONE; tested in real Chromium with a mocked API and a fake speech recogniser; undo endpoint written and API-tested but not run |
| More panel without menu roles; skeleton, empty and error states on Documents, Benefits, Applications | DONE; loading and empty states tested in real Chromium with a mocked API; error/Retry states not tested |

