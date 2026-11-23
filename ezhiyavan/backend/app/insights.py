"""Pure functions (no web framework): plain-language result summary for farmers and an anonymised impact report for NGOs / reviewers."""
from collections import Counter
from . import engine as eng

def _rule_types(scheme): return {r["id"]: r["type"] for r in scheme["rules"]}

def summarize(results, schemes):
    """results: household results from engine.evaluate. Adds, per scheme, what is still unknown ('to_confirm'), what blocks it ('blocked_by')
    and whether it is a near miss (red because of exactly one failed 'require' rule, e.g. no bank account yet)."""
    meta = {s["scheme_id"]: s for s in schemes}; per, counts = {}, Counter()
    for r in results:
        types = _rule_types(meta[r["scheme_id"]]) if r["scheme_id"] in meta else {}
        unknown = [t["text"] for t in r["trace"] if t["result"] == "unknown"]
        failed = [t for t in r["trace"] if t["result"] == "fail"]
        near = r["status"] == "red" and len(failed) == 1 and types.get(failed[0]["rule_id"]) == "require"
        per[r["scheme_id"]] = {"status": r["status"], "to_confirm": unknown, "blocked_by": [t["text"] for t in failed], "near_miss": near}
        counts[r["status"]] += 1
    live = [r for r in results if r["status"] != "red"]
    first = None
    if live:
        best = sorted(live, key=lambda r: (r["status"] != "green", -(eng.annual_amount(r) or 0)))[0]
        first = {"scheme_id": best["scheme_id"], "name": best["name"], "step": (best.get("application_steps") or [None])[0],
                 "documents": best.get("documents", [])[:4]}
    return {"potential": len(live), "green": counts["green"], "amber": counts["amber"], "red": counts["red"], "per_scheme": per, "do_first": first}

def impact(rows, schemes, min_cell=5):
    """rows: [{'profile': dict, 'doc_types': iterable, 'active_days': int|None}] for farmers. Returns only aggregates (no identifiers).
    With fewer than min_cell farmers the report is flagged small_sample so nobody reads statistics into it."""
    n = len(rows); screened = matched = 0; unlocked = 0; missing = Counter(); by_scheme = Counter(); active = 0
    hh = [s for s in schemes if s.get("applies_to") != "member"]
    for row in rows:
        if row.get("active_days") is not None and row["active_days"] <= 30: active += 1
        prof = row["profile"] or {}
        if not prof: continue
        screened += 1
        res = [eng.evaluate(s, prof) for s in hh]; live = [r for r in res if r["status"] != "red"]
        if live: matched += 1
        for r in live:
            by_scheme[r["name"]] += 1
            for d in r.get("required_doc_types", []):
                if d not in set(row.get("doc_types") or ()): missing[d] += 1
        unlocked += eng.estimate(res, [])["annual_inr_if_all_approved"]
    return {"farmers_total": n, "farmers_screened": screened, "farmers_with_potential_scheme": matched, "active_last_30_days": active,
            "potential_matches_by_scheme": dict(by_scheme.most_common()), "most_common_missing_documents": missing.most_common(5),
            "annual_inr_if_all_approved_verified_amounts_only": unlocked, "small_sample": n < min_cell,
            "note": "Aggregates only. Amounts count officially verified schemes only; with unverified demo rules this is 0 by design."}
