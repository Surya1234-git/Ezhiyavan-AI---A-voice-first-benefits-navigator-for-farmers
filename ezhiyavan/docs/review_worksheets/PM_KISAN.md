# Review worksheet: PM-KISAN Samman Nidhi (PM_KISAN, version demo-2026.11c)
Generated 2026-11-22. Status: **demo_unverified**. conditions_complete: **False**

Rules the engine will apply. For EACH one, open the official document and record the page/section that states it.

## PMK-1 (require) - evidence recorded
- Encoded as: `land_owned_acres gt 0`
- Text shown to farmers: Must own cultivable land
- [ ] Condition is stated in the official text (page/section: ______ )
- [ ] Exceptions/exemptions in the official text are encoded or flagged (list: ______ )
- [ ] Definitions (e.g. who counts as 'family') match the official definition

## PMK-2 (exclude) - evidence recorded
- Encoded as: `institutional_landholder eq True`
- Text shown to farmers: Institutional landholders are excluded
- [ ] Condition is stated in the official text (page/section: ______ )
- [ ] Exceptions/exemptions in the official text are encoded or flagged (list: ______ )
- [ ] Definitions (e.g. who counts as 'family') match the official definition

## PMK-3 (exclude) - evidence recorded
- Encoded as: `ANY of [income_tax_self eq True; income_tax_spouse eq True]`
- Text shown to farmers: Income tax payers (previous assessment year) in the beneficiary family - the applicant or their spouse - are excluded
- [ ] Condition is stated in the official text (page/section: ______ )
- [ ] Exceptions/exemptions in the official text are encoded or flagged (list: ______ )
- [ ] Definitions (e.g. who counts as 'family') match the official definition

## PMK-3b (flag) - evidence recorded
- Encoded as: `income_tax_other_family eq True`
- Text shown to farmers: Someone else in the household pays income tax. Whether this matters depends on the official definition of the beneficiary family (husband, wife and minor children) - needs a manual check
- [ ] Condition is stated in the official text (page/section: ______ )
- [ ] Exceptions/exemptions in the official text are encoded or flagged (list: ______ )
- [ ] Definitions (e.g. who counts as 'family') match the official definition

## PMK-4 (exclude) - evidence recorded
- Encoded as: `government_employee eq True`
- Text shown to farmers: Serving or retired government employees (except MTS/Class IV/Group D) and pensioners with Rs 10,000+/month are excluded
- [ ] Condition is stated in the official text (page/section: ______ )
- [ ] Exceptions/exemptions in the official text are encoded or flagged (list: ______ )
- [ ] Definitions (e.g. who counts as 'family') match the official definition

## PMK-5 (require) - evidence recorded
- Encoded as: `has_bank_account eq True`
- Text shown to farmers: A bank account is needed for payment
- [ ] Condition is stated in the official text (page/section: ______ )
- [ ] Exceptions/exemptions in the official text are encoded or flagged (list: ______ )
- [ ] Definitions (e.g. who counts as 'family') match the official definition

## PMK-6 (exclude) - evidence recorded
- Encoded as: `constitutional_post_holder eq True`
- Text shown to farmers: Current/former holders of constitutional posts (ministers, MPs, MLAs, mayors, district panchayat chairpersons) are excluded
- [ ] Condition is stated in the official text (page/section: ______ )
- [ ] Exceptions/exemptions in the official text are encoded or flagged (list: ______ )
- [ ] Definitions (e.g. who counts as 'family') match the official definition

## PMK-7 (exclude) - evidence recorded
- Encoded as: `professional_registered eq True`
- Text shown to farmers: Practising professionals (doctors, engineers, lawyers, CAs, architects) are excluded
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
- conditions_complete is not true: not every official condition is encoded

## Sign-off
Reviewer 1 (not the submitter): ______  date: ______
Reviewer 2 (required for new schemes and rule/benefit/state/date changes): ______  date: ______

## Reading notes (NOT a sign-off): what was actually read, and a correction
**Read in full:** the PM-KISAN FAQ (Ministry of Agriculture and Farmers Welfare, 23 Nov 2021, PIB copy of https://pmkisan.gov.in/Documents/RevisedFAQ.pdf), https://static.pib.gov.in/WriteReadData/specificdocs/documents/2021/nov/doc2021112361.pdf . Evidence entries in `pm_kisan.json` cite its question numbers. A human reviewer must still confirm them and say whether the 2021 FAQ is the current text.
**Not read:** the Operational Guidelines PDF (https://pmkisan.gov.in/Documents/RevisedPM-KISANOperationalGuidelines(English).pdf): the fetch was blocked. Reviewer: read it and see whether it adds conditions the FAQ does not.

- **PMK-1** matches FAQ Q5, Q6, Q12, Q13: the land must be in the farmer's own name, and tenant farmers are **not** eligible (land holding is the sole criterion). So PM-KISAN correctly excludes tenants, unlike KCC.
- **PMK-2, 3, 4, 6, 7** match the exclusion list in FAQ Q7. The family is husband, wife and minor children (Q5), so adult children and parents are not part of it. Reviewer: decide whether the PMK-3b flag ("someone else in the household pays income tax") is still needed.
- **PMK-5** matches FAQ Q20 (bank account details are compulsory; no benefit without them).
- **CORRECTION:** an earlier version of this worksheet said the guidelines also exclude non-resident Indians. That came from a secondary source and is **not in the FAQ I read**. It is unconfirmed. Do not encode it unless the Operational Guidelines say so.
- **Not encoded (found in the FAQ):** the land cut-off date of 1 Feb 2019 with a succession exception (Q10, Q11); the FAQ says changes after the cut-off are not considered "for next five years", so whether it still applies in 2026 needs the revenue office or a newer document. Cultivable land in actual agricultural use (Q23, Q25). Each farmer family on a shared holding is eligible separately (Q8). Aadhaar number is required (Q15).
- Keep `conditions_complete` false until these are encoded or ruled out of scope by the reviewers.
