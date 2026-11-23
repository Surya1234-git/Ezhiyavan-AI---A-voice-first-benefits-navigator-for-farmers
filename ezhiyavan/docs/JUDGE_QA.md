# Likely judge questions, with honest answers

**Why not just ask ChatGPT?** A chatbot can state eligibility confidently and be wrong. Here the language model only extracts facts from speech; the farmer confirms them; a deterministic engine applies rules that carry sources. The result is explainable and repeatable.

**How accurate is the speech/understanding?** We have a 105-case benchmark in four language groups, and the parser scores well on it, but the cases are synthetic and the parser was tuned on them, so we do not claim real-world accuracy. The harness reports "unsafe wrong values" separately from safe abstentions, and the test split is locked. The next step is a consented real set.

**Did you check the rules against official sources?** Partly. We audited all seven drafts (`docs/RULE_AUDIT.md`), found and fixed two real errors (KCC and PM-JAY), and pre-filled evidence notes for every scheme. No scheme is marked verified yet: that needs two named human reviewers (`docs/VERIFY_PM_KISAN.md`).

**Are the scheme rules correct?** They are drafts and the app says so. The system refuses to mark a scheme verified until every rule has evidence with a page or section and two different reviewers approve. We built the workflow; the human verification is the next task.

**What if a farmer's answer is wrong or they do not know?** They confirm every answer before it is stored. "I don't know" is stored as unknown and produces "needs confirmation", never a yes or no.

**What about privacy?** Aadhaar, PAN and bank numbers are masked before analysis and never stored as text; uploads are encrypted at rest and a retention job to purge old data is written (not yet run live); farmers can delete everything; partners see only consented cases and every access is logged.

**Does it work offline or on weak networks?** Only the app shell loads offline. Offline answering is not built. Image compression before upload and offline drafting are planned.

**Does it file applications?** No. It prepares a claim pack and links to official portals. Application status is self-reported and labelled that way.

**How would this scale?** Rules are data, so adding a scheme needs no code. Rate limiting has a Redis backend (tested with a fake Redis) and the database layer supports PostgreSQL (untested here). Delivery channels (SMS/WhatsApp) and a real pilot are next.

**What is untested?** The FastAPI endpoints have not been run end to end in our build environment, nor Tamil OCR on real documents, nor the Docker setup. The browser journey was tested against a mocked API. The README lists this plainly.

**Who is the user, and who is the customer?** The farmer uses it free. Help centres and NGOs use the partner screen and impact dashboard to serve more farmers with less repeated explanation.
