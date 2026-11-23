"""Reviewer worksheet for one scheme:  python scripts/review_worksheet.py PM_KISAN > pm_kisan_review.md
Lists every rule with its evidence status, every approval blocker, and the questions a reviewer must answer against the OFFICIAL text.
It does not verify anything and never edits a scheme."""
import os, sys, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from app import engine as e

def _cond(c):
    if "any" in c or "all" in c: return ("ANY of " if "any" in c else "ALL of ") + "[" + "; ".join(_cond(x) for x in (c.get("any") or c["all"])) + "]"
    return f'{c["field"]} {c["op"]} {c["value"]!r}'

def worksheet(s, today=None):
    today = today or dt.date.today(); ev = {}
    for x in s.get("source_evidence", []):
        for rid in x.get("rule_ids", []): ev.setdefault(rid, []).append(x)
    L = [f"# Review worksheet: {s['name']} ({s['scheme_id']}, version {s['version']})", f"Generated {today}. Status: **{s['status']}**. conditions_complete: **{s.get('conditions_complete', False)}**", "",
         "Rules the engine will apply. For EACH one, open the official document and record the page/section that states it.", ""]
    for r in s["rules"]:
        have = ev.get(r["id"], []); ok = any(x.get("page") or x.get("section") for x in have)
        L += [f"## {r['id']} ({r['type']}) - {'evidence recorded' if ok else 'NO EVIDENCE YET'}", f"- Encoded as: `{_cond(r)}`", f"- Text shown to farmers: {r['text']}",
              "- [ ] Condition is stated in the official text (page/section: ______ )", "- [ ] Exceptions/exemptions in the official text are encoded or flagged (list: ______ )",
              "- [ ] Definitions (e.g. who counts as 'family') match the official definition", ""]
    L += ["## Whole-scheme questions", "- [ ] Are there conditions in the official text that are NOT encoded above? (list them; then conditions_complete must stay false)",
          "- [ ] Applicable states/districts, effective date, expiry/deadline are correct", "- [ ] Benefit amount and frequency are correct (if marked verified, add evidence with rule_id 'BENEFIT')",
          "- [ ] Required documents and application steps match the official portal", "- [ ] Official source URL is the current one", "",
          "## Blockers the approval workflow will report today"]
    L += [f"- {b}" for b in e.approval_blockers(s, today)] or ["- none"]
    L += ["", "## Sign-off", "Reviewer 1 (not the submitter): ______  date: ______", "Reviewer 2 (required for new schemes and rule/benefit/state/date changes): ______  date: ______"]
    return "\n".join(L)

if __name__ == "__main__":
    sid = sys.argv[1].upper(); s = next((x for x in e.load_all() if x["scheme_id"] == sid), None)
    if not s: sys.exit("unknown scheme: " + sid)
    print(worksheet(s))
