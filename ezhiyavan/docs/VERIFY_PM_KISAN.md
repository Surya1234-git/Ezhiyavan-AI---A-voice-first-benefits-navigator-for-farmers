# Verifying PM-KISAN for real (two reviewers)

The software cannot do this for you, and it should not: the point is that two people check the official text.

1. **Reviewer A** (not the person who will approve): open `docs/review_worksheets/PM_KISAN.md` and the official guidelines. For every rule, find the clause or page and write it in the worksheet.
2. `backend/schemes/pm_kisan.json` already cites the 2021 PM-KISAN FAQ by question number (read in full by the assistant, still to be confirmed by you). Read the Operational Guidelines too (`docs/review_worksheets/PM_KISAN_evidence_DRAFT.json` has the entry to fill with `document_date`, `page` or `section`), and check whether they add conditions the FAQ does not.
3. Decide the open items in the worksheet (the 1 Feb 2019 land cut-off date, the PMK-3b flag, and whether the NRI exclusion exists at all: it is unconfirmed). Only then set `conditions_complete` to `true`.
4. Submit the scheme from the admin screen (`POST /api/admin/schemes`). Its status becomes `pending_review`.
5. **Reviewer B** logs in with a *different* admin account, reads the diff (`GET /api/admin/schemes/PM_KISAN/diff`) and approves it (`POST /api/admin/schemes/PM_KISAN/approve`). New schemes need two different approvers, and the submitter cannot approve.
6. Only after both approvals does the scheme become `verified`. Put both reviewers' names and the source pages on the demo slide.

`approval_blockers` in `app/engine.py` lists anything still missing. Admin setup is described in `docs/DETAILS.md`.
