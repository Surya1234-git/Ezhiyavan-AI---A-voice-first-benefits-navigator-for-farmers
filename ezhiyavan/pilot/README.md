# Supervised pilot kit

**Before anything else**: get informed, written (or recorded) consent from each participant, explain what data is stored, that the information shown is NOT an official decision, and that they can stop and have their data deleted at any time. Do not enrol anyone who cannot consent for themselves without a responsible adult. Use the app only with schemes whose rules a qualified person has verified (`/#/admin` trust banner must say trustworthy), otherwise tell participants clearly it is a demonstration.

## What to record (one row per session in `session_log_template.csv`)
Observer fills it in; do not rely on the app's own counters for judgement calls.
- `completed_profile` / `completed_without_help`: did they finish the questions, and did they need the helper to do it?
- `minutes_to_claim_pack`: stopwatch from first screen to a generated claim pack (blank if never reached).
- `ai_corrections`: times the farmer pressed "Change answer" (or the helper corrected a misread). `tamil_misunderstandings`: times the app misread Tamil/Tanglish (write the phrase in `notes`, with permission).
- `document_corrections`: extracted document values the farmer had to change or type in.
- `serious_error`: anything that could mislead (wrong eligibility shown, wrong person's data used, document misread without a warning, privacy slip). Describe it in `notes`.
- `application_initiated`: they started the official application. `benefit_confirmed`: **only** if the observer saw an official notice or payment. Never infer it.
- `satisfaction_1to5`, and free-text `notes` (failures included).

## Reporting rules
- `python pilot/analyze.py sessions.csv` prints counts and withholds percentages below 20 sessions.
- Report failures, abandoned journeys and limitations next to the successes; give n for every number.
- Do not describe eligibility discovered, claim packs prepared or applications initiated as "benefits delivered".
- Expert-check a sample of eligibility results against the verified rules and record disagreements as `serious_error` if farmers saw them.
