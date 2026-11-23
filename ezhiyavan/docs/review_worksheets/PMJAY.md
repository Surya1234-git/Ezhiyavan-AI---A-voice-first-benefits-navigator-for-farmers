# Review worksheet: PM-JAY (Ayushman Bharat) (PMJAY, version demo-2026.11b)
Generated 2026-11-21. Status: **demo_unverified**. conditions_complete: **False**

Rules the engine will apply. For EACH one, open the official document and record the page/section that states it.

## JAY-1 (require) - NO EVIDENCE YET
- Encoded as: `ANY of [in_pmjay_list eq True; has_member_aged_70_plus eq True]`
- Text shown to farmers: Eligible if the family is on the official beneficiary list, or if any member is aged 70 or above (regardless of income). Land ownership alone does not qualify
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
- rule JAY-1 (require): no official evidence with page/section
- conditions_complete is not true: not every official condition is encoded

## Sign-off
Reviewer 1 (not the submitter): ______  date: ______
Reviewer 2 (required for new schemes and rule/benefit/state/date changes): ______  date: ______

## Pre-filled research notes (NOT a sign-off)
Researched 2026-11-21 from search results of the official documents. Exact paragraph/page numbers were not captured. The reviewer must open each source, confirm the wording and record the page or section.

- **JAY-1, branch 2** (any member aged 70 or above, regardless of income). Sources: National Health Authority FAQs for senior citizens, https://www.nha.gov.in/img/resources/English_FAQs_related_to_the_benefits_for_senior_citizens.pdf (Q1: all senior citizens aged 70 or above, regardless of economic status; age as recorded in Aadhaar; a distinct card is issued); Ministry of Health press release https://mohfw.gov.in/press-info/7914 (expansion announced 29 Oct 2024); Union Cabinet approval of 11 Sep 2024, https://www.pmindia.gov.in/?p=16465137
- **JAY-1, branch 1** (family on the official beneficiary list). Official criteria for who is on the list were **not** checked. Reviewer must do this.
- **Official wording of the 70+ rule:** Rajya Sabha unstarred question 903 (11 Feb 2025), Annexure-I, https://rsdebate.nic.in/bitstream/123456789/758871/1/PQ_267_11022025_U903_p367_p370.pdf : benefits for citizens aged 70+ irrespective of socio-economic status; the only criterion is age 70 as recorded in Aadhaar; Aadhaar e-KYC is mandatory. A Ministry of Health release (https://mohfw.gov.in/press-info/7914) adds that families already covered get an extra top-up of up to Rs 5 lakh for the senior member.
- **Tamil Nadu (partly checked):** a Lok Sabha reply states PM-JAY is implemented in convergence with the state scheme in Tamil Nadu (https://eparlib.nic.in/bitstream/123456789/2971598/1/AU964.pdf, text truncated in my search); the World Bank case study documents the CMCHIS integration (https://documents1.worldbank.org/curated/en/345471588851378588/text/Nuts-and-Bolts-of-the-Chief-Minister-s-Comprehensive-Health-Insurance-Scheme-CMCHIS-A-Case-Study-from-Tamil-Nadu.txt). A Rajya Sabha reply of Feb 2025 says all States/UTs had on-boarded Vay Vandana except West Bengal and Delhi. A separate Tamil Nadu elderly health insurance scheme for 70+ is described only by a secondary source (policybazaar.com), so treat it as **unverified**. Reviewer: confirm how a Tamil Nadu farmer actually enrols (which card, which hospitals) before verifying.
- The question "Is your family on the PM-JAY list?" no longer says "answer no if you don't know". "I don't know" is stored as unknown and gives "needs confirmation", not a rejection.
