# Review worksheet: Destitute widow pension (Tamil Nadu) (TN_WIDOW_PENSION, version demo-2026.11)
Generated 2026-11-21. Status: **demo_unverified**. conditions_complete: **False**

Rules the engine will apply. For EACH one, open the official document and record the page/section that states it.

## WID-1 (require) - NO EVIDENCE YET
- Encoded as: `is_widowed eq True`
- Text shown to farmers: Applicant must be a widow (further conditions apply)
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
- rule WID-1 (require): no official evidence with page/section
- conditions_complete is not true: not every official condition is encoded

## Sign-off
Reviewer 1 (not the submitter): ______  date: ______
Reviewer 2 (required for new schemes and rule/benefit/state/date changes): ______  date: ______
## Pre-filled research notes (NOT a sign-off)
Researched 2026-11-21 from search results. Reviewer: open each source, confirm the wording, record the page or section.

- **WID-1** (is a widow): the official page https://cra.tn.gov.in/eleg_schemes.php lists the criterion for the state's Destitute Widow Pension as "Destitute Widow". Secondary sources **disagree on a minimum age** (30+ for the state scheme in one explainer, 40+ and below-poverty-line for the national IGNWPS in another). Do not encode an age until a reviewer reads the current government order.
- Women aged 60+ may apply under the old-age pension instead (secondary source). Reviewer: confirm.
