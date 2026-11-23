# 3-minute pitch (and demo script)

**One line:** Ezhiyavan AI tells a farmer, in their own language and in under two minutes, which schemes they may qualify for and what to do next, and every answer can be traced to a rule.

## Script
| Time | Say | Show |
|---|---|---|
| 0:00 | "Over 9.34 crore farmers received over ₹18,690 crore from PM-KISAN on 30 October 2026 (PIB). Murugan owns two acres, and doesn't know what else he qualifies for. The rules are scattered, the forms are in English, and nobody explains why a form was rejected." | Title slide |
| 0:25 | "So we built a navigator he can talk to in Tamil. The important design choice: the AI never decides eligibility." | Architecture slide: listen -> confirm -> rules engine |
| 0:45 | Live demo (below) | The app on a phone |
| 2:00 | "Why trust it? Every result shows the rule and its source. A rule only goes live after two different reviewers approve it against the official document. Farmers can report a rule that looks wrong." | Admin screen: trust banner, readiness register, reports |
| 2:30 | "Where we are honestly: the engine and workflow are built and tested; the scheme rules are drafts awaiting human verification. Next: verify PM-KISAN and KCC with a help centre and run a supervised pilot." | Roadmap slide |
| 2:50 | "We are looking for a partner CSC or NGO to verify the rules and pilot with real farmers." | Contact |

## Live demo (about 75 seconds)
1. Open the app (Tamil). Log in; in demo mode the OTP fills itself. *(Or run `make seed` first and skip to step 4.)*
2. Land question: tap the mic and say "two acres", or type it. Show **what was understood** and tap **Correct**.
3. A yes/no question: tap **I don't know** to show it is stored as unknown, then answer the rest with one tap.
4. Results: point to the single draft banner, the headline, the tick-list ("✓ Met · ? Needs confirmation"), **Do this first**, then tap **Read aloud**.
5. Open **Claim pack** and show the printable checklist.
6. Tap **See details** on the card, scroll to **Does this rule look wrong?**, send a report, then show it in the admin screen with the impact totals.
7. Show **Find a help centre** (opens a map search).

**Backup:** record this once as a 2-minute video. If the network or microphone fails, switch to typing and say so calmly.

## Slides (6)
1. Problem (one story, one sourced number). 2. The idea: AI listens, rules decide. 3. Demo screenshots. 4. Trust: evidence, two reviewers, reports, unverified labels. 5. What is tested and what is not. 6. Next steps and the ask.

## A sourced scale number (primary source)
The 24th PM-KISAN instalment was released on 30 October 2026: **over ₹18,690 crore to 9.34 crore farmers**, taking cumulative payments past ₹4.64 lakh crore (PIB Backgrounder, 30 Oct 2026: https://www.pib.gov.in/PressReleseDetailm.aspx?PRID=2330414&reg=48&lang=2 ; the 29 Oct pre-release is https://www.pib.gov.in/PressReleasePage.aspx?PRID=2330171&reg=48&lang=2 ). Use the PIB wording "over ₹18,690 crore": some news agencies print ₹18,680 crore. PIB also says registration is through the portal, the mobile app or Common Service Centres, which supports your help-centre story. I did not find an official figure for eligible-but-not-enrolled farmers, so do not claim a gap number.

## A strong honesty story
"We audited our own draft rules against official documents (`docs/RULE_AUDIT.md`) and found two errors: KCC wrongly excluded tenant farmers and allied-activity farmers, and PM-JAY missed the 2024 expansion to everyone aged 70 or above. We fixed both, and we are explicit about what is still unchecked. The remaining rules stay marked as drafts until two reviewers sign off."

## Numbers to source before you present
Fill these with figures you can cite, or leave them out: number of eligible farmers in your district or state; share of farmers who have not claimed a scheme; time a typical application takes. Do not state a figure you cannot source.

## Do not say
- "Verified" or "official" about the scheme rules (they are drafts).
- Any accuracy percentage as real-world accuracy (the benchmark is synthetic).
- That the app submits applications or confirms approval (it does neither).
