"""Production-readiness register. Status comes from EVIDENCE, never from a manual tick:
 - 'auto' checks are computed from the live scheme files;
 - 'report' checks are computed from a machine-generated test report (doc_eval / run_eval JSON) against thresholds;
 - 'evidence' checks can be marked passed only with evidence text/URL, a named independent reviewer and a test date.
Records are append-only in a JSON file (history kept); the latest entry per check wins."""
import datetime as dt, hashlib, json, os
from . import engine as eng

FILE = lambda: os.getenv("READINESS_FILE") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "readiness", "records.json")
STATUSES = ("not_started", "in_progress", "passed", "failed")
CHECKS = [("scheme_verification", "All schemes shown to farmers are verified", "auto"), ("scheme_evidence", "Every rule and exclusion has official evidence (page/section)", "auto"),
          ("two_person_approval", "Every verified scheme has two independent approvers", "auto"), ("expired_excluded", "Expired schemes are excluded from farmers", "auto"),
          ("tamil_ocr", "Tamil OCR evaluated on real, consented Tamil documents", "report"), ("multilingual_benchmark", "Held-out multilingual extraction benchmark", "report"),
          ("api_tests", "API/security test suite passed (against installed dependencies)", "evidence"), ("real_backend_e2e", "Real-backend browser journey passed", "evidence"),
          ("verified_journey_e2e", "Verified-scheme production-style journey passed", "evidence"), ("frontend_build", "Frontend production build (npm run build) passed", "evidence"),
          ("postgres_restore", "PostgreSQL backup restored into a fresh database and verified", "evidence"), ("shared_rate_limit", "Shared (Redis/gateway) rate limiting tested across workers", "evidence"),
          ("monitoring", "Monitoring and critical alerts configured and tested", "evidence"), ("live_otp", "Live OTP delivery tested (sender/DLT registered)", "evidence"),
          ("security_review", "Independent security review completed", "evidence"), ("farmer_pilot", "Supervised pilot report published", "evidence")]
TITLES = {c[0]: c[1] for c in CHECKS}; KIND = {c[0]: c[2] for c in CHECKS}

def _load():
    p = FILE()
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
def _save(d):
    p = FILE(); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=1)

# ---------- evaluators ----------
def auto_status(check_id, today=None):
    today = today or dt.date.today(); all_s = eng.load_all(); shown = eng.load_schemes(today); issues = []
    if check_id == "scheme_verification":
        issues = [f"{s['scheme_id']} is {s.get('status')}" for s in shown if s.get("status") != "verified"] + ([] if shown else ["no scheme is shown to farmers"])
    elif check_id == "scheme_evidence":
        issues = [f"{s['scheme_id']}: {len(eng.approval_blockers(s, today))} evidence gap(s)" for s in shown if eng.approval_blockers(s, today)] + ([] if shown else ["no scheme is shown to farmers"])
    elif check_id == "two_person_approval":
        for s in shown:
            ap = set(s.get("approved_by") or []) if isinstance(s.get("approved_by"), list) else set()
            if len(ap) < 2 or s.get("submitted_by") in ap: issues.append(f"{s['scheme_id']}: needs 2 approvers other than the submitter")
        if not shown: issues.append("no scheme is shown to farmers")
    elif check_id == "expired_excluded":
        live = {s["scheme_id"] for s in shown}; issues = [f"{s['scheme_id']} is expired but still shown" for s in all_s if s.get("expires") and today > dt.date.fromisoformat(s["expires"]) and s["scheme_id"] in live]
    return ("passed" if not issues else "failed"), issues

def eval_ocr_report(r, min_docs=150, min_tamil_docs=100):
    """r = JSON printed by eval/doc_eval.py --json. Fails closed: missing keys, synthetic data, or Tamil data not actually used all fail."""
    issues = []
    try:
        o, ocr, tags = r["overall"], r["ocr"], r["by_tag"]
        if o["docs"] < min_docs: issues.append(f"only {o['docs']} documents (< {min_docs})")
        if o["classification_accuracy"] < 0.95: issues.append(f"classification accuracy {o['classification_accuracy']:.0%} < 95%")
        if o["field_exact_match"] < 0.95: issues.append(f"field exact-match {o['field_exact_match']:.0%} < 95%")
        if o["wrong_high_conf"] > 0: issues.append(f"{o['wrong_high_conf']} wrong value(s) reported with high confidence (must be 0)")
        if "tam" not in str(ocr.get("requested") or ""): issues.append("OCR_LANGS did not request Tamil ('tam')")
        if "tam" not in " ".join(ocr.get("used", {})): issues.append("Tamil language data was never actually used")
        if ocr.get("fallback_docs", 1) > 0: issues.append(f"{ocr.get('fallback_docs')} document(s) were read with a fallback language")
        if any("synthetic" in t.lower() for t in tags): issues.append("report contains SYNTHETIC documents")
        tamil = max([b["docs"] for t, b in tags.items() if t.lower().startswith("language:tamil")] or [0])
        if tamil < min_tamil_docs: issues.append(f"only {tamil} documents tagged language:tamil (< {min_tamil_docs})")
    except (KeyError, TypeError) as e: issues.append(f"report is not a valid doc_eval --json output ({e})")
    return ("passed" if not issues else "failed"), issues

def eval_benchmark_report(r, min_test=90, min_per_lang=15):
    """r = JSON written by eval/run_eval.py --json for the FINAL run on the held-out test split of REAL, consented, human-labelled statements."""
    issues = []
    try:
        if not (r.get("split") == "test" and r.get("final")): issues.append("not a --final run on the test split")
        if r.get("provenance") != "real-consented": issues.append("cases are not all marked provenance=real-consented (synthetic or unlabelled)")
        o = r["result"]["overall"]
        if o["n"] < min_test: issues.append(f"only {o['n']} test cases (< {min_test})")
        if o["unsafe_wrong"] > 0: issues.append(f"{o['unsafe_wrong']} unsafe wrong value(s) (must be 0)")
        for lang, v in r["result"]["by_language"].items():
            if v["n"] < min_per_lang: issues.append(f"{lang}: only {v['n']} cases (< {min_per_lang})")
            if v["accuracy"] is not None and v["accuracy"] < 0.95: issues.append(f"{lang}: accuracy {v['accuracy']:.0%} < 95%")
        if not {"ta", "en", "hi", "mixed"} <= set(r["result"]["by_language"]): issues.append("Tamil, Tanglish(mixed), English and Hindi must all be present")
    except (KeyError, TypeError, AttributeError) as e: issues.append(f"report is not a valid run_eval --json output ({e})")
    return ("passed" if not issues else "failed"), issues

# ---------- recording ----------
class ReadinessError(Exception): pass
def record(check_id, who, status=None, evidence="", reviewer="", tested_on="", report=None, outstanding=None, today=None):
    today = today or dt.date.today()
    if check_id not in TITLES: raise ReadinessError("unknown check")
    if KIND[check_id] == "auto": raise ReadinessError("this check is computed from the live scheme data and cannot be set by hand")
    try: td = dt.date.fromisoformat(tested_on)
    except ValueError: raise ReadinessError("tested_on must be YYYY-MM-DD")
    if td > today: raise ReadinessError("tested_on cannot be in the future")
    if not reviewer.strip(): raise ReadinessError("name the responsible reviewer")
    entry = {"check": check_id, "recorded_by": who, "recorded_at": dt.datetime.utcnow().isoformat(timespec="seconds"), "tested_on": tested_on, "reviewer": reviewer.strip(), "evidence": evidence.strip()[:2000], "outstanding": list(outstanding or [])}
    if KIND[check_id] == "report":
        if not isinstance(report, dict): raise ReadinessError("attach the machine-generated report (JSON) - a manual pass is not accepted for this check")
        st, issues = (eval_ocr_report if check_id == "tamil_ocr" else eval_benchmark_report)(report)
        entry.update(status=st, outstanding=issues, report_sha256=hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest())
    else:
        status = status or "in_progress"
        if status not in STATUSES: raise ReadinessError("bad status")
        if status == "passed":
            ev = entry["evidence"]
            if not (ev.startswith("https://") or len(ev) >= 40): raise ReadinessError("'passed' needs evidence: an https link to the report, or a description of what was run and the result (>= 40 characters)")
            if reviewer.strip().lower() == who.lower(): raise ReadinessError("the reviewer must be someone other than the person recording the result")
        entry["status"] = status
    d = _load(); d.setdefault(check_id, []).append(entry); _save(d); return entry

def board(today=None):
    today = today or dt.date.today(); d = _load(); rows = []
    for cid, title, kind in CHECKS:
        if kind == "auto": st, issues = auto_status(cid, today); rows.append({"id": cid, "title": title, "kind": kind, "status": st, "tested_on": today.isoformat(), "reviewer": "(computed)", "evidence": "computed from live scheme files", "outstanding": issues})
        else:
            e = (d.get(cid) or [None])[-1]
            rows.append({"id": cid, "title": title, "kind": kind, "status": e["status"] if e else "not_started", "tested_on": e["tested_on"] if e else None, "reviewer": e["reviewer"] if e else None,
                         "evidence": e["evidence"] if e else None, "outstanding": e["outstanding"] if e else [], "history": len(d.get(cid, []))})
    n = sum(r["status"] == "passed" for r in rows)
    return {"checks": rows, "passed": n, "total": len(rows), "release_ready": n == len(rows)}
