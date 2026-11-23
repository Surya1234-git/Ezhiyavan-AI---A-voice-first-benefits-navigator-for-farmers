# Review worksheet: Kisan Credit Card (KCC, version demo-2026.11b)
Generated 2026-11-21. Status: **demo_unverified**. conditions_complete: **False**

Rules the engine will apply. For EACH one, open the official document and record the page/section that states it.

## KCC-1 (require) - NO EVIDENCE YET
- Encoded as: `ANY of [land_owned_acres gt 0; cultivates_leased_land eq True; does_allied_activity eq True]`
- Text shown to farmers: Must be an owner cultivator, a tenant farmer / oral lessee / sharecropper, or a farmer doing allied activities such as animal husbandry or fisheries
- [ ] Condition is stated in the official text (page/section: ______ )
- [ ] Exceptions/exemptions in the official text are encoded or flagged (list: ______ )
- [ ] Definitions (e.g. who counts as 'family') match the official definition

## KCC-2 (require) - NO EVIDENCE YET
- Encoded as: `has_bank_account eq True`
- Text shown to farmers: Applied through a bank
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
- rule KCC-1 (require): no official evidence with page/section
- rule KCC-2 (require): no official evidence with page/section
- conditions_complete is not true: not every official condition is encoded

## Sign-off
Reviewer 1 (not the submitter): ______  date: ______
Reviewer 2 (required for new schemes and rule/benefit/state/date changes): ______  date: ______

## Pre-filled research notes (NOT a sign-off)
Researched 2026-11-21 from search results of the official documents. Exact paragraph/page numbers were not captured. The reviewer must open each source, confirm the wording and record the page or section.

- **KCC-1** (now: owns land OR cultivates leased land OR does allied activities). Source: RBI, *Kisan Credit Card (KCC) Scheme Directions, 2026 (Commercial Banks)*, 19 Jun 2026, https://www.rbi.org.in/scripts/BS_ViewMasDirections.aspx?id=13522
  - Para 11 (eligibility for crop working capital): owner cultivators; tenant farmers, oral lessees and sharecroppers; SHGs / JLGs of such farmers.
  - Para 14 (allied activities): animal husbandry farmers, fishers, fish farmers, and farmers (including tenant farmers and sharecroppers) doing allied activities; SHGs / JLGs of such individuals.
  - The 2026 Directions apply to loans sanctioned from 1 Jan 2027; earlier loans stay under the earlier guidelines until renewal. An earlier RBI revised KCC scheme circular (rbi.org.in .../CRB5100512KC.pdf) lists the same three groups. Reviewer: confirm which text applies on the date of use.
  - **Not encoded:** SHG / JLG members, Flexi-KCC for marginal farmers, the bank's credit assessment. Keep `conditions_complete` false until you decide how to handle them.
- **KCC-2** (bank account). I did not find an official line making a bank account a *condition*; KCC is issued by banks. Reviewer: keep as a practical requirement, reword, or remove.
