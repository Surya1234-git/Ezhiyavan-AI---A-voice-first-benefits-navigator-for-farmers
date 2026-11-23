# Phase 0 audit (2026-11-21)

Audit of the repo against the "hackathon-winning product" brief. Status words: **exists** (built and tested here), **partial**, **written** (code exists, never run end to end), **missing**.

## Phase 0: proving it runs
| Item | Status | Evidence |
|---|---|---|
| Backend unit tests | exists | 207 pass (`tests.py` 174, `tests_new.py` 33) |
| Static check for import-order and undefined names | exists (new) | `scripts/check_names.py`, 25 files clean; tests prove it flags the original startup bug pattern |
| Extraction benchmark | exists | 88/88 on dev+val, **synthetic**, 0 unsafe values |
| Browser journey, mocked API, real Chromium | exists | passes (language, voice fallback, one-tap answers, results card with tick-list and collapsed details, report-a-rule, help finder, delete cancel **and delete confirm**, claim pack, family, documents, admin, accessible names, widths, keyboard, offline shell, no pop-ups) |
| Frontend type-check | partial | passes under **offline shims** for React types (real `@types/react` not installable here). Real command: `cd frontend && npm install && npm run build` |
| FastAPI endpoint tests (`tests_api.py`) | **written, not run** | no FastAPI here |
| Real-backend browser journeys | **written, not run** | need a running backend; both scripts updated for the delete confirmation |
| Docker / compose | **written, not run** | no Docker here; compose and CI YAML parse correctly |
| `make demo`, `make test` | written / exists | `make test` runs and reports skips honestly; `make demo` (`scripts/demo.sh`) is **not run** |

## Risks found
1. Everything that touches the real database, auth cookies, CSRF, rate limiting, OCR and uploads has never run together. Expect failures on first run.
2. The two real-backend journey scripts were written for an older UI; selectors may still be off.
3. The browser test uses a mocked API, so a mismatch between mock and real API would not show.
4. `main.py` (about 600 lines), `App.tsx` and `i18n.ts` are very large single files (Phase 6).
5. Rules are drafts and nothing is verified (Phase 1). The seed script and demo script depend on the backend answering as the mock does.

## Gap list against the brief (not started unless stated)
- Phase 1 rule trust: NRI exclusion, reviewer screen, freshness chip, per-rule plain-language source: **missing** (evidence notes and a two-reviewer API exist).
- Phase 2: smarter question choice (only a redundancy skip exists), back/undo, unit and number-word parsing, ranking, what-if, QR code and PDF, photo-quality tip, rejection helper, family summary: **missing or partial**.
- Phase 3: offline drafting, SMS/WhatsApp, assisted mode, low-literacy mode, deadlines, helpers, grievance letter: **missing** (impact dashboard exists, aggregate only).
- Phase 4: design system, icons, welcome screen, bottom tab bar, skeletons: **missing** (contrast fixed and delete confirmed).
- Phase 5-7: performance budgets, error boundaries, Alembic, load test, real e2e, pilot and real data: **missing**.

## Commands to run what could not run here
```
pip install -r backend/requirements.txt httpx pytest && (cd backend && pytest tests_api.py -q)
cd frontend && npm install && npm run build
make demo-backend            # shell 1
BASE_URL=http://localhost:5173 python frontend/e2e/real_backend_journey.py   # shell 2 (with `npm run dev` running)
docker compose up --build
make demo
```

## Update after the first Phase 1 / results-screen work
- Results card redesigned (progressive disclosure, tick-list, one draft banner). Tested in the browser against the mocked API only.
- PM-KISAN evidence filled **from the official FAQ I read in full** (question numbers, date 2021-11-23). The Operational Guidelines PDF could not be fetched, so it is still unread. An earlier note about an NRI exclusion was **retracted**: it is not in the FAQ.
- Delete-confirm path is now covered by the browser test.
- Still missing from the Phase 1 list: reviewer screen, "may be out of date" chip, per-rule plain-language source line, Uzhavar Padhukappu Thittam.

## Update after the UI pass
- **Emoji -> SVG icons:** 68 emoji across `App.tsx`, `Admin.tsx`, `Partner.tsx` replaced by one stroke icon set (`src/Icon.tsx`); the browser test fails if any emoji or raw markup is rendered on the welcome, results or admin screens.
- **Inline styles -> classes:** 87 inline `style={{}}` blocks (49 + 25 + 13) replaced by CSS classes; 0 remain. Design tokens (colour, type scale, 8px spacing, radius) are in `:root`. The admin badges now use the accessible badge colours instead of the old low-contrast inline ones.
- **"Do this first"** is now a numbered, highlighted panel. **Track** is a visible secondary button on green and amber cards.
- **Welcome:** three large language buttons and a "Speak, Confirm, Rules decide" strip.
- Still not done from the UI list: bottom tab bar, one question per screen with progress and undo, listening animation with live transcript, skeleton loaders, a logo and illustration, native-speaker review of strings, 360px / 200% zoom / TalkBack checks on a real phone.
- Verification: browser journey passes against the mocked API; type-check passes only against offline stand-in types.

## Update after the second UI pass
- **Welcome strings:** the three English strings (mobile placeholder, OTP button, OTP placeholder) now come from the translation file in Tamil, English and Hindi.
- **Bottom tab bar:** four tabs plus More (Family and Benefits live under More); `aria-current` marks the active tab.
- **One question per screen:** progress ("Question 2 of about 3", an estimate because one answer can make others unnecessary) and a Back button that takes the last answer back and asks it again. New endpoint `DELETE /api/me/answers/{field}`: **written, with an API test, not run** (no FastAPI here).
- **Listening state:** pulsing mic (animation only when the user has not asked for reduced motion), live transcript, a clear Stop button. Tested in Chromium with a **fake** speech recogniser; real Tamil recognition on a real phone is untested.
- **Skeleton loaders** for the question and results screens; **logo and welcome illustration** (inline SVG).
- Browser test passes against the mocked API; type-check passes only against offline stand-in types.
- Still not done: native Tamil/Hindi review of the new strings (new: progress, listening, Back, More, welcome), 360px / 200% zoom / TalkBack on a real phone, (skeletons for documents, benefits and applications are now done: see the update below).

## Update: accessibility and loading states (from review)
- **More panel:** `role="menu"` removed (it promises arrow-key behaviour that is not built). It is now a labelled group of plain buttons; the More button has `aria-expanded` and `aria-controls`. The browser test asserts there is no `menu` role.
- **Loading, empty and error states** for Documents, Benefits and Applications: skeleton while loading, a designed empty state ("No applications are being tracked yet", "No documents uploaded yet"), and an error card with a Retry button. Loading and empty states are tested (the request is parked so the skeleton can be seen). The **error and Retry states are not covered by a test**.
- Found while doing this: three clock emoji (Benefits, Partner screens) had slipped through the earlier emoji sweep, because the test's emoji range did not include that block. Replaced with the icon set and the test now covers the whole symbol range.
