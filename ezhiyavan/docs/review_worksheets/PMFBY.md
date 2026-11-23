# Review worksheet: PM Fasal Bima Yojana (crop insurance) (PMFBY, version demo-2026.11)
Generated 2026-11-21. Status: **demo_unverified**. conditions_complete: **False**

Rules the engine will apply. For EACH one, open the official document and record the page/section that states it.

## PMF-1 (require) - NO EVIDENCE YET
- Encoded as: `grows_notified_crop eq True`
- Text shown to farmers: Must grow a notified crop in a notified area this season
- [ ] Condition is stated in the official text (page/section: ______ )
- [ ] Exceptions/exemptions in the official text are encoded or flagged (list: ______ )
- [ ] Definitions (e.g. who counts as 'family') match the official definition

## PMF-2 (require) - NO EVIDENCE YET
- Encoded as: `has_bank_account eq True`
- Text shown to farmers: Premium/claims via bank account
- [ ] Condition is stated in the official text (page/section: ______ )
- [ ] Exceptions/exemptions in the official text are encoded or flagged (list: ______ )
- [ ] Definitions (e.g. who counts as 'family') match the official definition

## Whole-scheme questions
- [ ] Are there conditions in the official text that are NOT encoded above? (list them; then conditions_complete must stay false)
- [ ] Applicable states/districts, effective date, expiry/deadline are correct
- [ ] Benefit amount and frequency are correct (if marked verified, add evidence with rule_id 'BENEFIT')
- [ ] Required documents and application steps match the official portal
- [ ] Official source URL is the current one

## Blockers the approval workflow will report today
- rule PMF-1 (require): no official evidence with page/section
- rule PMF-2 (require): no official evidence with page/section
- conditions_complete is not true: not every official condition is encoded

## Sign-off
Reviewer 1 (not the submitter): ______  date: ______
Reviewer 2 (required for new schemes and rule/benefit/state/date changes): ______  date: ______
## Pre-filled research notes (NOT a sign-off)
Researched 2026-11-21 from search results. Reviewer: open each source, confirm the wording, record the page or section.

- **PMF-1** (grows a notified crop in a notified area): the Operational Guidelines cover all farmers including sharecroppers and tenant farmers who have an insurable interest, so no land ownership is required (our rules already do not require it). Sources: PMFBY Operational Guidelines (copy at https://diragri.assam.gov.in/sites/default/files/swf_utility_folder/departments/diragri_medhassu_in_oid_4/menu/document/10%28A%29.1.pdf , "Coverage of Farmers"); PIB 28 Jul 2021, https://pib.gov.in/PressReleasePage.aspx?PRID=1739993 (available to loanee, non-loanee, sharecropper and tenant farmers on a voluntary basis).
- **PMF-2** (bank account): PIB (same release) says claims are transferred electronically to the farmer's bank account. Reviewer: keep as practical requirement or reword.
- **Not encoded:** state-specific proof for tenants and sharecroppers (secondary sources mention landowner consent; the guidelines say it is as notified by the State), season enrolment cut-off dates (manual check already present), the sowing declaration.
- **Finding:** no oversimplification like KCC found. The documents line already says "Land record or tenancy proof".
