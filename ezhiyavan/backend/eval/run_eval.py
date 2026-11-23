"""Extraction accuracy harness with a leak-proof split.
  python eval/run_eval.py [cases.jsonl]                 -> scores the DEVELOPMENT split (dev + val). Use this while tuning.
  python eval/run_eval.py cases.jsonl --split test --final -> scores the held-out TEST split. Run it ONCE, after development is finished.
The split is deterministic (hash of id+language: 70% dev / 15% val / 15% test), so a case never moves between splits. Every --final run is appended to
eval/FINAL_RUNS.log with the SHA-256 of the cases file; if you change the cases file or the parser and run --final again, the log shows it (that is tuning on the test set).
Reports accuracy per language AND unsafe errors: a wrong non-empty value (e.g. a son's tax status assigned to the applicant) is far worse than abstaining (None).
The bundled cases.jsonl is SYNTHETIC and was written by the developer: it exercises the harness only. Replace it with consented, human-labelled real statements."""
import collections, datetime as dt, hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
from app.extract import extract, extract_smart

def split_of(c):
    h = int(hashlib.sha256(f"{c['id']}|{c['lang']}".encode()).hexdigest(), 16) % 100
    return "dev" if h < 70 else ("val" if h < 85 else "test")

def same(a, b):
    if a is None or b is None: return a is b
    if isinstance(a, float) or isinstance(b, float): return abs(float(a) - float(b)) < 0.01
    return a == b

def score(cases, fn):
    """-> per-language and overall counts. outcome: correct | unsafe_wrong (non-empty wrong value) | abstained (None though a value was expected)."""
    by = collections.defaultdict(lambda: collections.Counter()); errs = []
    for c in cases:
        got = fn(c)
        if same(got, c["expected"]): o = "correct"
        elif got is None: o = "abstained"
        else: o = "unsafe_wrong"
        by[c["lang"]][o] += 1; by[c["lang"]]["n"] += 1
        if o != "correct": errs.append({**c, "got": got, "outcome": o})
    tot = collections.Counter()
    for v in by.values(): tot.update(v)
    full = lambda v: {"n": 0, "correct": 0, "unsafe_wrong": 0, "abstained": 0, **v}
    rate = lambda v0: (lambda v: {**v, "accuracy": round(v["correct"] / v["n"], 3) if v["n"] else None, "unsafe_rate": round(v["unsafe_wrong"] / v["n"], 3) if v["n"] else None})(full(v0))
    return {"overall": rate(tot), "by_language": {l: rate(v) for l, v in sorted(by.items())}, "errors": sorted(errs, key=lambda e: e["outcome"] != "unsafe_wrong")}

def run(path, split=None, final=False, json_out=None):
    cases = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    want = {"dev", "val"} if split is None else {split}
    if "test" in want and not final: sys.exit("The test split is locked. It may only be scored once, at the end, with --final.")
    sel = [c for c in cases if split_of(c) in want]
    systems = {"rules": lambda c: extract(c["field"], c["text"])}
    if os.getenv("ANTHROPIC_API_KEY"): systems["llm+rules"] = lambda c: extract_smart(c["field"], c["text"], c["lang"])["value"]
    out = {}
    for name, fn in systems.items():
        r = score(sel, fn); out[name] = r; o = r["overall"]
        print(f"\n== {name} on {'+'.join(sorted(want))}: {o['correct']}/{o['n']} correct ({100 * o['accuracy']:.0f}%), unsafe wrong values: {o['unsafe_wrong']}, abstained: {o['abstained']}   [SYNTHETIC unless you replaced the cases file]")
        for l, v in r["by_language"].items(): print(f"   {l:6} {v['correct']}/{v['n']}  unsafe={v['unsafe_wrong']}  abstained={v['abstained']}")
        for e in r["errors"]: print(f"   {e['outcome'].upper():12} [{e['lang']}/{e['field']}] {e['text']!r} expected={e['expected']!r} got={e['got']!r}")
    if json_out:    # machine-readable evidence for the admin readiness register (app/readiness.py)
        best = "llm+rules" if "llm+rules" in out else "rules"
        prov = "real-consented" if sel and all(c.get("provenance") == "real-consented" for c in sel) else "synthetic-or-unlabelled"
        json.dump({"split": "test" if want == {"test"} else "+".join(sorted(want)), "final": final, "provenance": prov, "system": best, "n": len(sel),
                   "cases_sha256": hashlib.sha256(open(path, "rb").read()).hexdigest(), "result": out[best]}, open(json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if final:
        sha = hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]; log = os.path.join(HERE, "FINAL_RUNS.log")
        prev = [l.split()[2] for l in open(log, encoding="utf-8")] if os.path.exists(log) else []
        with open(log, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.utcnow().isoformat(timespec='seconds')} cases_sha256={sha} n={len(sel)} unsafe={out['rules']['overall']['unsafe_wrong']} acc={out['rules']['overall']['accuracy']}\n")
        if prev and f"cases_sha256={sha}" not in prev: print("\nWARNING: the cases file changed since an earlier --final run. Scores after tuning on the test set are not independent evidence.")
    return out

if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--") and x not in (sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None, sys.argv[sys.argv.index("--split") + 1] if "--split" in sys.argv else None)]; sp = sys.argv[sys.argv.index("--split") + 1] if "--split" in sys.argv else None
    jo = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    run(a[0] if a and a[0].endswith(".jsonl") else os.path.join(HERE, "cases.jsonl"), sp, "--final" in sys.argv, jo)
