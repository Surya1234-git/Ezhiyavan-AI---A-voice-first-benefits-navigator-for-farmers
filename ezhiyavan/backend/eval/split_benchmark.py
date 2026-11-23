"""Write the dev / val / test files of a labelled benchmark:  python eval/split_benchmark.py cases.jsonl outdir
Same deterministic rule as run_eval.py. Keep outdir/test.jsonl away from whoever tunes the parser."""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_eval import split_of
src, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True); n = collections.Counter(); fh = {k: open(os.path.join(out, k + ".jsonl"), "w", encoding="utf-8") for k in ("dev", "val", "test")}
for l in open(src, encoding="utf-8"):
    if l.strip(): c = json.loads(l); k = split_of(c); fh[k].write(json.dumps(c, ensure_ascii=False) + "\n"); n[(k, c["lang"])] += 1
for f in fh.values(): f.close()
print(dict(n))
