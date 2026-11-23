"""Document-reading accuracy harness.  python eval/doc_eval.py <dir>  [--json]
<dir> holds pairs:  name.png|jpg|pdf  +  name.json  =  {"doc_type": "land_record", "fields": {"survey_no": "142/3A", "area_acres": 2.5}, "tags": ["district:Thanjavur", "scan:phone-photo"]}
Reports: classification accuracy and abstention, field exact-match, WRONG values (and how many were wrong while marked high-confidence = the dangerous kind),
missing values, and the farmer correction rate (= wrong + missing, over expected fields). Broken down by tag. Use consented, anonymised real documents;
the numbers are only as meaningful as the samples."""
import json, os, sys, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from app import docs as dcs

def _same(k, a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)): return abs(float(a) - float(b)) < 0.01
    return str(a).replace(" ", "").lower() == str(b).replace(" ", "").lower()

def evaluate(folder):
    rows = []; langs = collections.Counter(); fallback = 0; requested = None
    for f in sorted(os.listdir(folder)):
        base, ext = os.path.splitext(f)
        if ext.lower() not in (".png", ".jpg", ".jpeg", ".pdf") or not os.path.exists(os.path.join(folder, base + ".json")): continue
        lab = json.load(open(os.path.join(folder, base + ".json"), encoding="utf-8")); info = dcs.read_document(os.path.join(folder, f))
        requested = info["lang_requested"]
        if info["lang_used"]: langs[info["lang_used"]] += 1; fallback += info["lang_used"] != info["lang_requested"]
        a = dcs.analyze(info["text"], info["mean_conf"]) if info["text"] else None
        rows.append((f, lab, a))
    def blank(): return {"docs": 0, "cls_ok": 0, "cls_abstain": 0, "cls_wrong": 0, "unreadable": 0, "expected": 0, "ok": 0, "wrong": 0, "wrong_high_conf": 0, "missing": 0}
    tot = blank(); by = collections.defaultdict(blank); detail = []
    for f, lab, a in rows:
        for bucket in [tot] + [by[t] for t in lab.get("tags", [])]:
            bucket["docs"] += 1
            if a is None: bucket["unreadable"] += 1
            elif a["detected_type"] == "unknown": bucket["cls_abstain"] += 1
            elif a["detected_type"] == lab["doc_type"]: bucket["cls_ok"] += 1
            else: bucket["cls_wrong"] += 1
            for k, want in lab.get("fields", {}).items():
                bucket["expected"] += 1; got = (a or {}).get("fields", {}).get(k)
                if got is None: bucket["missing"] += 1
                elif _same(k, got, want): bucket["ok"] += 1
                else:
                    bucket["wrong"] += 1
                    if (a or {}).get("field_confidence", {}).get(k) == "high": bucket["wrong_high_conf"] += 1
        for k, want in lab.get("fields", {}).items():
            got = (a or {}).get("fields", {}).get(k)
            if got is None or not _same(k, got, want): detail.append({"file": f, "field": k, "expected": want, "got": got})
    def rates(b):
        n, e = max(b["docs"], 1), max(b["expected"], 1)
        return {**b, "classification_accuracy": round(b["cls_ok"] / n, 3), "field_exact_match": round(b["ok"] / e, 3), "farmer_correction_rate": round((b["wrong"] + b["missing"]) / e, 3)}
    return {"overall": rates(tot), "by_tag": {t: rates(b) for t, b in sorted(by.items())}, "errors": detail,
            "ocr": {"requested": requested, "used": dict(langs), "fallback_docs": fallback}}      # fallback_docs > 0 means Tamil data was NOT used for those documents

if __name__ == "__main__":
    r = evaluate(sys.argv[1])
    if "--json" in sys.argv: print(json.dumps(r, indent=1, ensure_ascii=False)); sys.exit()
    def line(n, b): return f"{n:28} docs={b['docs']:3} cls_acc={b['classification_accuracy']:.0%} (abstained {b['cls_abstain']}, wrong {b['cls_wrong']}, unreadable {b['unreadable']})  fields: exact={b['field_exact_match']:.0%} wrong={b['wrong']} (high-conf wrong {b['wrong_high_conf']}) missing={b['missing']}  farmer_correction_rate={b['farmer_correction_rate']:.0%}"
    print("OCR languages requested:", r["ocr"]["requested"], "| actually used:", r["ocr"]["used"], "| documents read with a FALLBACK language:", r["ocr"]["fallback_docs"])
    print(line("OVERALL", r["overall"]));  [print(line(t, b)) for t, b in r["by_tag"].items()]
    for e in r["errors"]: print("  ERR", e)
