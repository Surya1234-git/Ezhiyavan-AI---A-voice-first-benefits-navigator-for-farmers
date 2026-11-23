# Review worksheet: Social pension for senior citizens (Tamil Nadu) (TN_OLD_AGE_PENSION, version demo-2026.11)
Generated 2026-11-21. Status: **demo_unverified**. conditions_complete: **False**

Rules the engine will apply. For EACH one, open the official document and record the page/section that states it.

## PEN-1 (require) - NO EVIDENCE YET
- Encoded as: `age gte 60`
- Text shown to farmers: Applicant must be 60 or older (further income/destitution conditions apply)
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
- rule PEN-1 (require): no official evidence with page/section
- conditions_complete is not true: not every official condition is encoded

## Sign-off
Reviewer 1 (not the submitter): ______  date: ______
Reviewer 2 (required for new schemes and rule/benefit/state/date changes): ______  date: ______
## Pre-filled research notes (NOT a sign-off)
Researched 2026-11-21 from search results. Reviewer: open each source, confirm the wording, record the page or section.

- **PEN-1** (age 60 or older): matches the Tamil Nadu Revenue Department policy note 2021-22 (https://cms.tn.gov.in/cms_migrated/document/docfiles/revenue_e_pn_2021_22.pdf): Indira Gandhi National Old Age Pension, age 60+, destitute, below poverty line. Reviewer: confirm the current year's note and which TN pension schemes apply.
- **Missing scheme worth adding (for farmers):** the **Chief Minister's Uzhavar Padhukappu Thittam** old-age pension for farmers and landless agricultural labourers is listed on https://cra.tn.gov.in/about_schemes.php . This app does not include it. It is very relevant to your users. Add it only after a reviewer has read its eligibility rules.
- Destitution / BPL conditions are not encoded; `conditions_complete` stays false.
