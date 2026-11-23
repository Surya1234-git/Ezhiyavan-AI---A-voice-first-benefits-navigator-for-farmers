"""Deterministic eligibility engine. No LLM involved.
Rule = {id, type: require|exclude, text, and EITHER field/op/value OR any:[conds] / all:[conds]}.
Three-valued logic: pass / fail / unknown. Scheme-level: effective_from, expires, applicable_states, stale-review warning."""
import json, os, glob, datetime as dt
SCHEME_DIR = os.getenv("SCHEME_DIR") or os.path.join(os.path.dirname(__file__), "..", "schemes")   # SCHEME_DIR lets tests/staging use fixture schemes
ALLOW_UNVERIFIED = os.getenv("ALLOW_UNVERIFIED", "0") == "1"  # demo only; default: verified rules only
REVIEW_MAX_DAYS = int(os.getenv("REVIEW_MAX_DAYS", "180"))

def load_all():
    """Every scheme file regardless of status (admin views)."""
    out = []
    for p in sorted(glob.glob(os.path.join(SCHEME_DIR, "*.json"))):
        with open(p, encoding="utf-8") as f: out.append(json.load(f))
    return out

def load_schemes(today=None):
    """Schemes shown to farmers: verified (or demo drafts only when ALLOW_UNVERIFIED=1) and NOT expired (expired schemes are disabled automatically)."""
    today = today or dt.date.today(); out = []
    for s in load_all():
        if s.get("expires") and today > dt.date.fromisoformat(s["expires"]): continue
        if s.get("status") == "verified" or (ALLOW_UNVERIFIED and s.get("status") == "demo_unverified"): out.append(s)
    return out

OPS = {"eq": lambda a, b: a == b, "ne": lambda a, b: a != b, "gt": lambda a, b: a > b, "gte": lambda a, b: a >= b,
       "lt": lambda a, b: a < b, "lte": lambda a, b: a <= b, "in": lambda a, b: a in b, "not_in": lambda a, b: a not in b}

def _cond(c, profile):
    """True / False / None(unknown) for a leaf condition or any/all group."""
    if "any" in c or "all" in c:
        vals = [_cond(x, profile) for x in (c.get("any") or c.get("all"))]
        if "any" in c:
            return True if True in vals else (None if None in vals else False)
        return False if False in vals else (None if None in vals else True)
    v = profile.get(c["field"])
    if v is None: return None
    try: return OPS[c["op"]](v, c["value"])
    except TypeError: return None

def _fields(c):
    if "any" in c or "all" in c: return [f for x in (c.get("any") or c["all"]) for f in _fields(x)]
    return [c["field"]]

def evaluate(scheme, profile, today=None):
    today = today or dt.date.today(); trace, status = [], "green"
    ev = {}
    for e in scheme.get("source_evidence", []):
        for rid in e.get("rule_ids", []): ev.setdefault(rid, []).append({k: e.get(k) for k in ("title", "url", "document_date", "page", "section")})
    rtype = {r["id"]: r.get("type") for r in scheme.get("rules", [])}      # require / exclude / flag: lets the UI word a pass correctly ("Met" vs "Not excluded")
    def add(rid, res, text, field="-"):
        nonlocal status
        reported = {f: profile[f] for f in field.split(",") if f in profile}
        trace.append({"rule_id": rid, "type": rtype.get(rid), "field": field, "result": res, "text": text, "reported": reported, "evidence": ev.get(rid, [])})
        if res == "fail": status = "red"
        elif res == "unknown" and status != "red": status = "amber"
    ef, ex = scheme.get("effective_from"), scheme.get("expires")
    if ef and today < dt.date.fromisoformat(ef): add("DATES", "fail", f"Rule not effective until {ef}")
    if ex and today > dt.date.fromisoformat(ex): add("DATES", "fail", f"Scheme/rule expired on {ex}")
    st = scheme.get("applicable_states")
    if st:
        v = profile.get("state"); add("GEO", "unknown" if v is None else ("pass" if v in st else "fail"),
                                      "Applies in: " + ", ".join(st), "state")
    for r in scheme["rules"]:
        c = _cond(r, profile)
        if r["type"] == "flag": res = "unknown" if (c is None or c) else "pass"       # "flag": if true, a human must decide (never silently pass or fail)
        else: res = "unknown" if c is None else (("pass" if c else "fail") if r["type"] == "require" else ("fail" if c else "pass"))
        add(r["id"], res, r["text"], ",".join(dict.fromkeys(_fields(r))))
    lv = scheme.get("last_verified")
    stale = bool(lv) and (today - dt.date.fromisoformat(lv)).days > REVIEW_MAX_DAYS
    return {"scheme_id": scheme["scheme_id"], "name": scheme["name"], "version": scheme["version"],
            "rule_status": scheme["status"], "source": scheme["source"], "last_verified": lv, "stale_review": stale,
            "conditions_complete": scheme.get("conditions_complete", False),
            "benefit": scheme["benefit"], "benefit_detail": scheme.get("benefit_detail"), "deadline": scheme.get("deadline"),
            "documents": scheme["documents"], "required_doc_types": scheme.get("required_doc_types", []), "application_steps": scheme.get("application_steps", []), "manual_checks": scheme.get("manual_checks", []), "status": status, "trace": trace}

def needed_fields(schemes):
    """Household-level questions only; member-level schemes use each member's own record."""
    seen = []
    for s in schemes:
        if s.get("applies_to") == "member":
            if s.get("applicable_states") and "state" not in seen: seen.append("state")
            continue
        fl = (["state"] if s.get("applicable_states") else []) + [f for r in s["rules"] for f in _fields(r)]
        for f in fl:
            if f not in seen: seen.append(f)
    return seen

def redundant_fields(schemes, profile):
    """Fields that need not be asked: every household rule that mentions them is an 'any' group another answer has already satisfied
    (e.g. no need to ask 'do you lease land?' once the farmer has said they own land)."""
    refs = {}
    for s in schemes:
        if s.get("applies_to") == "member": continue
        for r in s["rules"]:
            for f in set(_fields(r)): refs.setdefault(f, []).append(r)
    return {f for f, rs in refs.items() if f not in profile and all("any" in r and _cond(r, profile) is True for r in rs)}

def evaluate_members(schemes, household, members, today=None):
    """Evaluate member-level schemes separately for each CONSENTED member. members: dicts with id, relationship, age, occupation, consent."""
    out = []
    for m in members:
        if not m.get("consent"): continue
        prof = {**household, "age": m["age"], "relationship": m["relationship"], "occupation": m.get("occupation") or None}
        prof.update({k: m[k] for k in ("has_disability", "is_widowed", "is_student") if m.get(k) is not None})   # unknown (None) stays unknown
        res = [evaluate(s, prof, today) for s in schemes if s.get("applies_to") == "member"]
        out.append({"member_id": m["id"], "relationship": m["relationship"], "age": m["age"], "results": mark_conflicts(res, schemes)})
    return out

def mark_conflicts(results, schemes):
    """Flag schemes of the SAME person that may not be combinable (scheme field conflicts_with + conflict_note). Informational only."""
    meta = {s["scheme_id"]: s for s in schemes}; live = {r["scheme_id"] for r in results if r["status"] != "red"}
    for r in results:
        s = meta[r["scheme_id"]]; r["conflicts"] = [{"with": o, "note": s.get("conflict_note", "May not be combinable - confirm with the department")}
                                                    for o in s.get("conflicts_with", []) if o in live and r["status"] != "red"]
    return results

_PER_YEAR = {"yearly": 1, "monthly": 12, "quarterly": 4}
def annual_amount(r):
    bd = r.get("benefit_detail") or {}
    return bd["amount_inr"] * _PER_YEAR[bd["frequency"]] if bd.get("verified") and bd.get("frequency") in _PER_YEAR else None

def estimate(household_results, member_results):
    """Upper bound per year IF every counted scheme were approved. Only OFFICIALLY VERIFIED amounts count; within one person, conflicting schemes
    count once (the largest). Never a promise of money."""
    total, counted, skipped = 0, [], 0
    def pick(results):
        nonlocal total, skipped
        chosen = []
        live = [r for r in results if r["status"] != "red"]
        for r in sorted(live, key=lambda x: -(annual_amount(x) or 0)):
            amt = annual_amount(r)
            if amt is None: skipped += 1; continue
            if any(c["with"] in {x["scheme_id"] for x in chosen} for c in r.get("conflicts", [])): continue
            chosen.append(r); total += amt; counted.append(r["scheme_id"])
    pick(household_results)
    for m in member_results: pick(m["results"])
    return {"annual_inr_if_all_approved": total, "counted": counted, "uncounted_without_verified_amount": skipped,
            "note": "Upper bound, not a promise. Only schemes with officially verified amounts are counted."}

def validate_scheme(s):
    """Structural validation incl. nested any/all. Returns list of error strings (empty = ok)."""
    errs = [f"missing {k}" for k in ("scheme_id", "name", "version", "source", "rules", "benefit", "documents") if k not in s]
    if errs: return errs
    if not str(s["source"]).startswith("https://"): errs.append("source must be an https official URL")
    if s.get("applies_to", "household") not in ("household", "member"): errs.append("applies_to must be household|member")
    for k in ("effective_from", "expires", "deadline", "last_verified"):
        if s.get(k):
            try: dt.date.fromisoformat(s[k])
            except Exception: errs.append(f"{k} must be YYYY-MM-DD")
    st = s.get("applicable_states")
    if st is not None and not (isinstance(st, list) and st and all(isinstance(x, str) for x in st)): errs.append("applicable_states must be a non-empty list of strings")
    bd = s.get("benefit_detail")
    if bd is not None and not (isinstance(bd, dict) and isinstance(bd.get("amount_inr"), (int, float)) and isinstance(bd.get("frequency"), str) and isinstance(bd.get("verified"), bool)):
        errs.append("benefit_detail needs amount_inr(number), frequency(str), verified(bool)")
    if not isinstance(s["rules"], list): return errs + ["rules must be a list"]
    def chk(c, depth, path):
        if depth > 4: errs.append(f"{path}: nested too deep"); return
        if not isinstance(c, dict): errs.append(f"{path}: not an object"); return
        groups = [k for k in ("any", "all") if k in c]
        if len(groups) + ("field" in c) != 1: errs.append(f"{path}: needs exactly one of field / any / all"); return
        if "field" in c:
            if not isinstance(c["field"], str) or not c["field"]: errs.append(f"{path}: bad field")
            if c.get("op") not in OPS: errs.append(f"{path}: bad op {c.get('op')}")
            if "value" not in c: errs.append(f"{path}: missing value")
            elif c.get("op") in ("in", "not_in") and not isinstance(c["value"], list): errs.append(f"{path}: in/not_in needs a list")
        else:
            lst = c[groups[0]]
            if not isinstance(lst, list) or not lst: errs.append(f"{path}: empty {groups[0]}"); return
            for i, x in enumerate(lst): chk(x, depth + 1, f"{path}.{groups[0]}[{i}]")
    ids = set()
    for r in s["rules"]:
        rid = r.get("id") if isinstance(r, dict) else None
        if not rid or rid in ids: errs.append(f"rule id missing or duplicate: {rid}")
        ids.add(rid)
        if not isinstance(r, dict): errs.append("rule is not an object"); continue
        if r.get("type") not in ("require", "exclude", "flag"): errs.append(f"rule {rid}: type must be require|exclude|flag")
        if not r.get("text"): errs.append(f"rule {rid}: missing text")
        chk(r, 0, f"rule {rid}")
    return errs


# ---------------- governance: evidence, diff, approvals, trust ----------------
HIGH_IMPACT_KEYS = ("benefit_detail", "applicable_states", "expires", "effective_from", "applies_to", "conflicts_with")
DIFF_KEYS = HIGH_IMPACT_KEYS + ("source", "documents", "required_doc_types", "deadline", "version")

def diff_schemes(old, new):
    o = {r["id"]: r for r in old.get("rules", [])}; n = {r["id"]: r for r in new.get("rules", [])}
    return {"rules_added": sorted(set(n) - set(o)), "rules_removed": sorted(set(o) - set(n)),
            "rules_changed": [{"id": i, "before": o[i], "after": n[i]} for i in sorted(set(o) & set(n)) if o[i] != n[i]],
            "fields_changed": {k: {"before": old.get(k), "after": new.get(k)} for k in DIFF_KEYS if old.get(k) != new.get(k)}}

def high_impact(old, new):
    if old is None: return True
    d = diff_schemes(old, new)
    return bool(d["rules_added"] or d["rules_removed"] or d["rules_changed"] or any(k in d["fields_changed"] for k in HIGH_IMPACT_KEYS))

def approval_blockers(s, today=None):
    """Reasons a scheme may NOT be approved yet. Every rule (incl. every exclusion) needs official evidence with a page or section."""
    today = today or dt.date.today(); b = []
    evid = s.get("source_evidence") or []
    for i, e in enumerate(evid):
        if not (str(e.get("url", "")).startswith("https://") and e.get("title")): b.append(f"evidence #{i + 1}: needs title and https url")
        try: dt.date.fromisoformat(e.get("document_date") or "")
        except ValueError: b.append(f"evidence #{i + 1}: document_date must be YYYY-MM-DD")
        if not (e.get("page") or e.get("section")): b.append(f"evidence #{i + 1}: needs page or section")
    good = {rid for e in evid if str(e.get("url", "")).startswith("https://") and (e.get("page") or e.get("section")) for rid in e.get("rule_ids", [])}
    for r in s.get("rules", []):
        if r["id"] not in good: b.append(f"rule {r['id']} ({r['type']}): no official evidence with page/section")
    bd = s.get("benefit_detail")
    if bd and bd.get("verified") and "BENEFIT" not in good: b.append("benefit amount marked verified but no evidence for rule_id 'BENEFIT'")
    if not s.get("conditions_complete"): b.append("conditions_complete is not true: not every official condition is encoded")
    if s.get("expires") and today > dt.date.fromisoformat(s["expires"]): b.append("scheme already expired")
    return b

class ApprovalError(Exception):
    def __init__(self, msg, blockers=None): super().__init__(msg); self.blockers = blockers or []

def apply_approval(s, who, old=None, today=None):
    """Mutates s. New schemes and any rule/benefit/state/date change are HIGH impact -> two distinct approvers (neither the submitter)."""
    today = today or dt.date.today()
    if s.get("submitted_by") == who: raise ApprovalError("the submitter cannot approve their own submission")
    if who in s.get("approvals", []): raise ApprovalError("you have already approved this version")
    b = approval_blockers(s, today)
    if b: raise ApprovalError("approval blocked", b)
    need = 2 if high_impact(old, s) else 1
    s["approvals"] = [*s.get("approvals", []), who]
    if len(s["approvals"]) >= need: s.update(status="verified", last_verified=today.isoformat(), approved_by=list(s["approvals"]))
    return {"status": s["status"], "approvals": len(s["approvals"]), "required": need}

def trust_report(schemes, today=None):
    """Answers: can we trust the scheme information currently shown to farmers?"""
    today = today or dt.date.today(); rows = []
    for s in schemes:
        exp = s.get("expires"); lv = s.get("last_verified"); live = s.get("status") == "verified" or (ALLOW_UNVERIFIED and s.get("status") == "demo_unverified")
        expired = bool(exp) and today > dt.date.fromisoformat(exp)
        rows.append({"scheme_id": s["scheme_id"], "status": s.get("status"), "shown_to_farmers": live and not expired, "evidence_blockers": len(approval_blockers(s, today)),
                     "expired": expired, "expiring_within_30_days": bool(exp) and not expired and (dt.date.fromisoformat(exp) - today).days <= 30,
                     "stale_review": bool(lv) and (today - dt.date.fromisoformat(lv)).days > REVIEW_MAX_DAYS, "last_verified": lv})
    shown = [r for r in rows if r["shown_to_farmers"]]
    bad = [r["scheme_id"] for r in shown if r["status"] != "verified" or r["stale_review"] or r["evidence_blockers"]]
    return {"schemes": rows, "shown_to_farmers": len(shown), "trustworthy": bool(shown) and not bad, "problems": bad,
            "summary": "All schemes shown to farmers are verified, evidenced and current." if shown and not bad else
                       ("No scheme is currently shown to farmers." if not shown else "NOT trustworthy: " + ", ".join(bad) + " shown without complete verification/evidence.")}


REL_OK = {"spouse", "son", "daughter", "father", "mother", "grandfather", "grandmother", "brother", "sister", "other"}
def family_issues(members):
    """Data-quality checks on household records. Informational: the farmer decides what to fix."""
    out = []; seen = {}
    for m in members:
        key = (m["relationship"], m["age"], (m.get("occupation") or "").lower())
        if key in seen: out.append({"kind": "duplicate_member", "members": [seen[key], m["id"]]})
        seen.setdefault(key, m["id"])
        if m["relationship"] not in REL_OK: out.append({"kind": "unknown_relationship", "members": [m["id"]]})
        if not m.get("consent"): out.append({"kind": "missing_consent", "members": [m["id"]]})
        if m["relationship"] in ("father", "mother", "grandfather", "grandmother") and m["age"] < 18: out.append({"kind": "age_implausible", "members": [m["id"]]})
        if m["age"] > 105: out.append({"kind": "age_implausible", "members": [m["id"]]})
    sp = [m["id"] for m in members if m["relationship"] == "spouse"]
    if len(sp) > 1: out.append({"kind": "multiple_spouses", "members": sp})
    return out
