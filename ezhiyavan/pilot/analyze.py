"""Pilot analysis from the observer log (see session_log_template.csv).  python pilot/analyze.py sessions.csv
It computes only what was OBSERVED, prints n next to every figure, and refuses to print percentages for fewer than MIN_N sessions.
'benefit_confirmed' counts only rows where an official notice/payment was seen by the observer; everything else is 'initiated' or 'prepared'."""
import csv, statistics, sys, collections
MIN_N = 20
def yes(v): return str(v).strip().lower() in ("y", "yes", "1", "true")
def num(v):
    try: return float(v)
    except (TypeError, ValueError): return None

def analyze(rows):
    n = len(rows); out = {"sessions": n, "note": ""}
    def pct(k):
        c = sum(1 for r in rows if yes(r.get(k)))
        return {"count": c, "of": n, "percent": round(100 * c / n, 1) if n >= MIN_N else None}
    for k in ("completed_profile", "completed_without_help", "claim_pack_generated", "application_initiated", "serious_error", "benefit_confirmed"): out[k] = pct(k)
    t = [x for x in (num(r.get("minutes_to_claim_pack")) for r in rows) if x is not None]
    out["minutes_to_claim_pack"] = {"n": len(t), "median": statistics.median(t) if t else None, "max": max(t) if t else None}
    for k in ("ai_corrections", "document_corrections", "tamil_misunderstandings"): v = [num(r.get(k)) or 0 for r in rows]; out[k] = {"total": sum(v), "per_session": round(sum(v) / n, 2) if n else None}
    sat = [x for x in (num(r.get("satisfaction_1to5")) for r in rows) if x is not None]
    out["satisfaction"] = {"n": len(sat), "mean": round(statistics.mean(sat), 2) if sat else None}
    out["by_language"] = {l: sum(1 for r in rows if r.get("language") == l) for l in sorted({r.get("language") for r in rows})}
    out["problems_reported"] = [r["notes"] for r in rows if yes(r.get("serious_error")) and r.get("notes")]
    if n < MIN_N: out["note"] = f"Only {n} sessions (< {MIN_N}): percentages withheld. Report counts and say the sample is too small to generalise."
    return out

if __name__ == "__main__":
    import json; print(json.dumps(analyze(list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))), indent=1, ensure_ascii=False))
