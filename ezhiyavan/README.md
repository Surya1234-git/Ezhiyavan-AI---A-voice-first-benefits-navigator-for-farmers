# Ezhiyavan AI

**A voice-first benefits navigator for farmers.** Speak or tap in Tamil, English or Hindi, confirm what the app understood, and see which government schemes you may qualify for, why, and exactly what to do next.

> The AI only *listens*. A deterministic rules engine *decides*, and every result shows the rule and its source. No black-box eligibility.

## What it does
- **Ask by voice, text or one tap.** Yes/No/"I don't know" buttons on yes/no questions; "I don't know" is stored as *unknown*, never guessed. Questions are read aloud.
- **Confirm before saving.** The farmer sees their own words, what was understood, and the confidence. Nothing is stored until they say "correct".
- **Clear results.** A headline ("You may qualify for N schemes"), one draft banner, and a card per scheme with a status chip, a "why" tick-list (met / not met / needs confirmation, always a word as well as a symbol), one **Do this first** action and one main button. Documents, steps, sources and the full explanation sit behind **See details**. A **Read aloud** button reads the summary.
- **Claim pack.** A printable checklist of documents, steps and the facts the farmer confirmed (no Aadhaar/PAN/bank numbers).
- **Documents.** Upload a land record or passbook; text is read (OCR), sensitive numbers are masked, and the farmer confirms the values.
- **Family and help centres.** Member-level schemes with per-member consent; consented CSC/NGO partners can help; a **help-centre finder** opens a map search.
- **Trust tooling.** Scheme rules carry evidence and need **two different reviewers** to go live; farmers and partners can **report a rule that looks wrong**; an admin **impact dashboard** shows anonymised totals.

## Run it (demo mode)
```bash
make demo                  # backend + seeded demo farmer + frontend + browser (no Docker)
make demo-docker           # the same stack in Docker -> http://localhost:5173
make test                  # every check that can run; says what was skipped and why
```
Without Docker:
```bash
cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
ENV=dev ALLOW_UNVERIFIED=1 SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))") uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```
**Demo mode** shows the OTP on screen and activates *unverified* scheme drafts. Never use it with real farmers. Production settings are in `docs/DETAILS.md`.

## How it was checked (honest status)
| Checked here | Result |
|---|---|
| Backend unit tests (`tests.py`, 174) and new-logic, rule-correction and static-check tests (`tests_new.py`, 33) | pass |
| Browser journey in real Chromium with a **mocked API** (voice/typed answers, one-tap answers, results, report-a-rule, help finder, claim pack, family, documents, admin screens, accessible names, 320-1440px, keyboard, offline shell) | pass |
| **Not run here:** FastAPI endpoints (`tests_api.py`), real-backend journeys, Docker files, GitHub Actions, `tsc`/Vite production build, `seed_demo.py`, Tamil OCR on real documents | run them before demo day (`make test`, CI) |

## Honest limits
- We audited all seven drafts against official sources (`docs/RULE_AUDIT.md`) and fixed two errors (KCC now covers tenant farmers and allied-activity farmers; PM-JAY now covers everyone aged 70+). No scheme is verified yet: `docs/VERIFY_PM_KISAN.md` shows how two reviewers do it.
- The seven scheme files are **unverified demo drafts** written from public knowledge. They are labelled that way in the app. Real verification needs a human against the official guidelines.
- The extraction benchmark (105 cases: en 45, ta 33, hi 17, mixed 10) is **synthetic**, written by the developer. It is not real-world accuracy.
- The app never submits applications and never claims government confirmation; tracking is self-reported.

## Docs
`docs/AUDIT.md` (what exists, what is missing, what is risky) · `docs/PITCH.md` (3-minute script and slides) · `docs/JUDGE_QA.md` · `docs/DETAILS.md` (full engineering notes) · `docs/PRODUCTION_READINESS.md` · `docs/review_worksheets/`
