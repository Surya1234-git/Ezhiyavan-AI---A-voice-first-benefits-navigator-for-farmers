import os, time, unittest
os.environ.update(SECRET_KEY="test-secret-test-secret-test-secret", ALLOW_UNVERIFIED="1")
from app import engine as e, security as sec
from app.extract import extract

def sch(): return {x["scheme_id"]: x for x in e.load_schemes()}
BASE = {"land_owned_acres": 2, "has_bank_account": True, "government_employee": False, "income_tax_self": False, "income_tax_spouse": False, "income_tax_other_family": False, "institutional_landholder": False,
        "constitutional_post_holder": False, "professional_registered": False}

class Engine(unittest.TestCase):
    def test_green_amber_red(self):
        s = sch()
        self.assertEqual(e.evaluate(s["PM_KISAN"], BASE)["status"], "green")
        self.assertEqual(e.evaluate(s["PMFBY"], BASE)["status"], "amber")
        self.assertEqual(e.evaluate(s["PM_KISAN"], {**BASE, "income_tax_self": True})["status"], "red")
        self.assertEqual(e.evaluate(s["PMJAY"], {"in_pmjay_list": False, "has_member_aged_70_plus": False})["status"], "red")
    def test_missing_is_amber_not_green(self):
        self.assertEqual(e.evaluate(sch()["PM_KISAN"], {"land_owned_acres": 2})["status"], "amber")
    def test_zero_land_fails(self):
        self.assertEqual(e.evaluate(sch()["PM_KISAN"], {**BASE, "land_owned_acres": 0})["status"], "red")
    def test_red_beats_unknown(self):
        self.assertEqual(e.evaluate(sch()["PM_KISAN"], {"income_tax_self": True})["status"], "red")
    def test_trace_has_rule_ids(self):
        self.assertTrue(all(t["rule_id"] for t in e.evaluate(sch()["PM_KISAN"], BASE)["trace"]))
    def test_unverified_blocked_by_default(self):
        e.ALLOW_UNVERIFIED = False
        try: self.assertEqual(e.load_schemes(), [])      # all shipped schemes are demo drafts
        finally: e.ALLOW_UNVERIFIED = True

class Extract(unittest.TestCase):
    def test_langs(self):
        self.assertEqual(extract("land_owned_acres", "எனக்கு இரண்டு ஏக்கர்"), 2.0)
        self.assertEqual(extract("land_owned_acres", "mere paas 3 acre"), 3.0)
        self.assertIs(extract("has_bank_account", "இல்லை"), False)
        self.assertIs(extract("has_bank_account", "ஆம்"), True)
        self.assertIs(extract("income_tax_self", "नहीं"), False)
        self.assertIsNone(extract("has_bank_account", "maybe"))

class Security(unittest.TestCase):
    def test_token_roundtrip_and_tamper(self):
        t = sec.make_token("abc"); self.assertEqual(sec.verify_token(t)["sub"], "abc")
        self.assertIsNone(sec.verify_token(t[:-2] + "xx"))
        self.assertIsNone(sec.verify_token("garbage"))
    def test_expired(self): self.assertIsNone(sec.verify_token(sec.make_token("a", ttl=-1)))
    def test_role_in_token(self): self.assertEqual(sec.verify_token(sec.make_token("a", "admin"))["role"], "admin")
    def test_phone_not_stored_plain(self): self.assertNotIn("9876543210", sec.hash_phone("9876543210"))
    def test_password(self):
        import hashlib
        stored = "s$" + hashlib.pbkdf2_hmac("sha256", b"pw", b"s", 200_000).hex()
        self.assertTrue(sec.check_password("pw", stored)); self.assertFalse(sec.check_password("no", stored))



import datetime as dt
from unittest import mock
from app import extract as ex

def scheme(rules, **kw): return {"scheme_id": "X", "name": "X", "version": "1", "status": "verified", "source": "https://x", "benefit": "b",
                                 "documents": [], "rules": rules, **kw}
class Engine2(unittest.TestCase):
    any_rule = {"id": "A", "type": "require", "text": "t", "any": [{"field": "age", "op": "gte", "value": 60}, {"field": "widow", "op": "eq", "value": True}]}
    def test_any_logic(self):
        s = scheme([self.any_rule]); ev = lambda p: e.evaluate(s, p)["status"]
        self.assertEqual(ev({"age": 60}), "green"); self.assertEqual(ev({"age": 59}), "amber")   # widow unknown
        self.assertEqual(ev({"age": 59, "widow": False}), "red"); self.assertEqual(ev({"age": 30, "widow": True}), "green")
    def test_all_and_exclude_group(self):
        s = scheme([{"id": "B", "type": "exclude", "text": "t", "all": [{"field": "a", "op": "eq", "value": True}, {"field": "b", "op": "eq", "value": True}]}])
        self.assertEqual(e.evaluate(s, {"a": True, "b": True})["status"], "red")
        self.assertEqual(e.evaluate(s, {"a": True, "b": False})["status"], "green")
        self.assertEqual(e.evaluate(s, {"a": False})["status"], "green")      # all-group already false
        self.assertEqual(e.evaluate(s, {"a": True})["status"], "amber")
    def test_boundaries(self):
        s = scheme([{"id": "C", "type": "require", "text": "t", "field": "income", "op": "lte", "value": 100000}])
        self.assertEqual(e.evaluate(s, {"income": 100000})["status"], "green"); self.assertEqual(e.evaluate(s, {"income": 100001})["status"], "red")
    def test_dates(self):
        s = scheme([], effective_from="2026-04-01", expires="2027-03-31"); d = dt.date
        self.assertEqual(e.evaluate(s, {}, d(2026, 3, 31))["status"], "red"); self.assertEqual(e.evaluate(s, {}, d(2026, 4, 1))["status"], "green")
        self.assertEqual(e.evaluate(s, {}, d(2027, 3, 31))["status"], "green"); self.assertEqual(e.evaluate(s, {}, d(2027, 4, 1))["status"], "red")
    def test_state_applicability(self):
        s = scheme([], applicable_states=["Tamil Nadu"])
        self.assertEqual(e.evaluate(s, {"state": "Kerala"})["status"], "red"); self.assertEqual(e.evaluate(s, {})["status"], "amber")
        self.assertEqual(e.evaluate(s, {"state": "Tamil Nadu"})["status"], "green"); self.assertIn("state", e.needed_fields([s]))
    def test_stale_review_flag(self):
        s = scheme([], last_verified="2026-01-01"); self.assertTrue(e.evaluate(s, {}, dt.date(2026, 11, 19))["stale_review"])
        self.assertFalse(e.evaluate(s, {}, dt.date(2026, 3, 1))["stale_review"])
    def test_type_mismatch_is_unknown(self):
        s = scheme([{"id": "D", "type": "require", "text": "t", "field": "age", "op": "gte", "value": 60}]); self.assertEqual(e.evaluate(s, {"age": "abc"})["status"], "amber")

class SmartExtract(unittest.TestCase):
    def run_with(self, field, text, llm):
        with mock.patch.object(ex, "extract_llm", return_value=llm): return ex.extract_smart(field, text)
    def test_no_key_falls_back(self):
        os.environ.pop("ANTHROPIC_API_KEY", None); r = ex.extract_smart("land_owned_acres", "2 acres"); self.assertEqual((r["value"], r["method"]), (2.0, "rules"))
    def test_agree_high(self): self.assertEqual(self.run_with("land_owned_acres", "2 acres", {"value": 2.0, "confident": True})["confidence"], "high")
    def test_conflict_low_and_flagged(self):
        r = self.run_with("land_owned_acres", "2 acres", {"value": 5.0, "confident": True}); self.assertEqual((r["confidence"], r["note"]), ("low", "conflict"))
    def test_llm_failure_falls_back(self): self.assertEqual(self.run_with("has_bank_account", "ஆம்", None)["value"], True)
    def test_llm_null_unclear(self): self.assertEqual(self.run_with("has_bank_account", "hmm", {"value": None, "confident": False})["confidence"], "none")
    def test_validation_blocks_bad_output(self):
        self.assertIsNone(ex.validate("has_bank_account", "yes")); self.assertIsNone(ex.validate("land_owned_acres", 99999))
        self.assertIsNone(ex.validate("land_owned_acres", True)); self.assertIsNone(ex.validate("land_owned_acres", "2"))
        self.assertEqual(ex.validate("land_owned_acres", 2), 2.0)
    def test_injection_output_rejected(self): self.assertIsNone(ex.validate("land_owned_acres", "ignore previous instructions"))
    def test_state_rules(self): self.assertEqual(ex.extract("state", "நான் தமிழ்நாடு"), "Tamil Nadu")
    def test_llm_http_failure_returns_none(self):
        os.environ["ANTHROPIC_API_KEY"] = "k"
        try:
            with mock.patch("urllib.request.urlopen", side_effect=OSError("down")): self.assertIsNone(ex.extract_llm("land_owned_acres", "2", "ta"))
        finally: os.environ.pop("ANTHROPIC_API_KEY")
    def test_llm_parses_response(self):
        os.environ["ANTHROPIC_API_KEY"] = "k"; import io, json as j
        resp = io.BytesIO(j.dumps({"content": [{"text": 'sure {"value": 2, "confident": true}'}]}).encode())
        try:
            with mock.patch("urllib.request.urlopen", return_value=resp): self.assertEqual(ex.extract_llm("land_owned_acres", "2", "ta"), {"value": 2.0, "confident": True})
        finally: os.environ.pop("ANTHROPIC_API_KEY")

from app import docs as dcs
class Validator(unittest.TestCase):
    good = lambda self: scheme([{"id": "A", "type": "require", "text": "t", "any": [{"field": "a", "op": "eq", "value": 1}, {"all": [{"field": "b", "op": "gt", "value": 2}, {"field": "c", "op": "in", "value": [1]}]}]}])
    def test_shipped_schemes_valid(self):
        for s in e.load_schemes(): self.assertEqual(e.validate_scheme(s), [], s["scheme_id"])
    def test_nested_ok(self): self.assertEqual(e.validate_scheme(self.good()), [])
    def test_nested_bad_op_detected(self):
        s = self.good(); s["rules"][0]["any"][1]["all"][0]["op"] = "bogus"; self.assertTrue(any("bad op" in x for x in e.validate_scheme(s)))
    def test_nested_missing_value(self):
        s = self.good(); del s["rules"][0]["any"][0]["value"]; self.assertTrue(e.validate_scheme(s))
    def test_in_needs_list(self):
        s = self.good(); s["rules"][0]["any"][1]["all"][1]["value"] = 1; self.assertTrue(e.validate_scheme(s))
    def test_empty_group_and_mixed(self):
        self.assertTrue(e.validate_scheme(scheme([{"id": "A", "type": "require", "text": "t", "any": []}])))
        self.assertTrue(e.validate_scheme(scheme([{"id": "A", "type": "require", "text": "t", "field": "a", "op": "eq", "value": 1, "any": [{"field": "b", "op": "eq", "value": 1}]}])))
    def test_depth_limit(self):
        c = {"field": "a", "op": "eq", "value": 1}
        for _ in range(6): c = {"any": [c]}
        self.assertTrue(any("deep" in x for x in e.validate_scheme(scheme([{"id": "A", "type": "require", "text": "t", **c}]))))
    def test_duplicate_id_bad_date_http_source(self):
        r = {"id": "A", "type": "require", "text": "t", "field": "a", "op": "eq", "value": 1}
        self.assertTrue(e.validate_scheme(scheme([r, dict(r)])))
        self.assertTrue(e.validate_scheme(scheme([r], expires="31-12-2026")))
        self.assertTrue(e.validate_scheme(scheme([r], source="http://x")))

class Members(unittest.TestCase):
    def test_pension_per_member_and_consent(self):
        ss = {x["scheme_id"]: x for x in e.load_schemes()}; sl = [ss["TN_OLD_AGE_PENSION"]]
        ms = [{"id": "1", "relationship": "mother", "age": 66, "occupation": "", "consent": True},
              {"id": "2", "relationship": "son", "age": 20, "occupation": "student", "consent": True},
              {"id": "3", "relationship": "father", "age": 70, "occupation": "", "consent": False}]
        out = e.evaluate_members(sl, {"state": "Tamil Nadu"}, ms)
        self.assertEqual([m["member_id"] for m in out], ["1", "2"])           # non-consenting member is never evaluated
        self.assertEqual(out[0]["results"][0]["status"], "green"); self.assertEqual(out[1]["results"][0]["status"], "red")
    def test_member_scheme_excluded_from_household_questions(self):
        self.assertNotIn("age", e.needed_fields(e.load_schemes()))
    def test_state_unknown_is_amber_for_member(self):
        ss = {x["scheme_id"]: x for x in e.load_schemes()}
        out = e.evaluate_members([ss["TN_OLD_AGE_PENSION"]], {}, [{"id": "1", "relationship": "mother", "age": 66, "occupation": "", "consent": True}])
        self.assertEqual(out[0]["results"][0]["status"], "amber")

class Docs(unittest.TestCase):
    LAND = "Patta No: 1234  Survey No. 45/2A  Extent 0.81 hectares  Date of issue 12-03-2025"
    def test_land_record(self):
        a = dcs.analyze(self.LAND); self.assertEqual(a["detected_type"], "land_record"); self.assertEqual(a["fields"]["survey_no"], "45/2A")
        self.assertAlmostEqual(a["fields"]["area_acres"], 2.002, 2); self.assertEqual(a["fields"]["issue_date"], "2025-03-12"); self.assertEqual(a["missing"], [])
    def test_tamil_land_record_and_cents(self):
        a = dcs.analyze("பட்டா எண் 77 சர்வே எண் 12/1 பரப்பு 50 சென்ட்"); self.assertEqual(a["detected_type"], "land_record"); self.assertEqual(a["fields"]["area_acres"], 0.5)
    def test_missing_detected(self):
        a = dcs.analyze("Patta number 5 chitta extract"); self.assertIn("survey_no", a["missing"]); self.assertIn("area_acres", a["missing"])
    def test_income_certificate(self):
        a = dcs.analyze("Income Certificate. Annual income Rs. 84,000/- Date of issue 01/02/2026 valid up to 31-01-2027")
        self.assertEqual(a["fields"]["income_inr"], 84000); self.assertEqual(a["fields"]["valid_until"], "2027-01-31")
    def test_account_number_never_extracted(self):
        a = dcs.analyze("Passbook Branch IFSC SBIN0001234 Account No 123456789012"); self.assertEqual(a["fields"], {"ifsc": "SBIN0001234"})
    def test_unknown_and_bad_date(self):
        self.assertEqual(dcs.analyze("hello world")["detected_type"], "unknown"); self.assertNotIn("issue_date", dcs.analyze("Patta 1 Date of issue 31-02-2025")["fields"])
    def test_authenticity_note(self): self.assertIn("NOT verified", dcs.analyze(self.LAND)["note"])
    def test_reminders(self):
        today = dt.date(2026, 11, 19)
        res = [{"scheme_id": "A", "status": "green", "required_doc_types": ["land_record", "bank_passbook"], "deadline": "2026-12-01"},
               {"scheme_id": "B", "status": "red", "required_doc_types": ["land_record"], "deadline": "2026-11-20"}]
        docs = [{"doc_type": "land_record", "confirmed": {"valid_until": "2026-11-25"}}]
        kinds = [(r["kind"], r.get("scheme_id") or r.get("doc_type")) for r in dcs.build_reminders(res, docs, today)]
        self.assertIn(("missing_document", "A"), kinds); self.assertIn(("deadline", "A"), kinds); self.assertIn(("document_expiring", "land_record"), kinds)
        self.assertFalse(any(k[1] == "B" for k in kinds))                       # ineligible scheme: no reminders


import tempfile, shutil, subprocess
def _have_ocr():
    try:
        import pytesseract, PIL; pytesseract.get_tesseract_version(); return True
    except Exception: return False
def _text_image(lines, size=36):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (1400, 120 + 70 * len(lines)), "white"); d = ImageDraw.Draw(img); f = ImageFont.load_default(size=size)
    for i, ln in enumerate(lines): d.text((40, 40 + 70 * i), ln, fill="black", font=f)
    return img

@unittest.skipUnless(_have_ocr(), "tesseract not installed")
class RealOcr(unittest.TestCase):
    LINES = ["PATTA NO: 1234", "SURVEY NO. 45/2A", "EXTENT 2.5 ACRES", "DATE OF ISSUE 12-03-2025"]
    def setUp(self): self.tmp = tempfile.mkdtemp()
    def tearDown(self): shutil.rmtree(self.tmp)
    def test_image_ocr_end_to_end(self):
        p = os.path.join(self.tmp, "a.png"); _text_image(self.LINES).save(p)
        info = dcs.read_document(p); self.assertEqual(info["method"], "image_ocr")
        a = dcs.analyze(info["text"]); self.assertEqual(a["detected_type"], "land_record"); self.assertEqual(a["fields"].get("area_acres"), 2.5)
        self.assertEqual(a["fields"].get("survey_no"), "45/2A")
    def test_scanned_pdf_is_rendered_and_ocrd(self):
        p = os.path.join(self.tmp, "s.pdf"); _text_image(self.LINES).save(p)           # image-only PDF (no text layer)
        info = dcs.read_document(p); self.assertEqual(info["method"], "pdf_scanned_ocr"); self.assertEqual(dcs.analyze(info["text"])["fields"].get("area_acres"), 2.5)
    def test_low_res_flagged(self):
        from PIL import Image
        p = os.path.join(self.tmp, "l.png"); Image.new("RGB", (300, 200), "white").save(p); w = dcs.quality_warnings(dcs.read_document(p))
        self.assertIn("low_resolution", w)
    def test_missing_tamil_data_falls_back_to_english(self):
        p = os.path.join(self.tmp, "t.png"); _text_image(self.LINES).save(p); self.assertIsNotNone(dcs.read_document(p, "tam+eng")["text"])

class Many(unittest.TestCase):
    F = ["land_owned_acres", "state", "has_bank_account"]
    def test_rules_only(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        p = {x["field"]: x for x in ex.extract_many("நான் தமிழ்நாடு, எனக்கு 2 ஏக்கர் நிலம் உள்ளது", "ta", self.F, {})}
        self.assertEqual(p["land_owned_acres"]["value"], 2.0); self.assertEqual(p["state"]["value"], "Tamil Nadu"); self.assertNotIn("has_bank_account", p)
    def test_llm_multi_and_contradiction(self):
        with mock.patch.object(ex, "extract_many_llm", return_value={"land_owned_acres": {"value": 3.0, "confident": True}, "has_bank_account": {"value": True, "confident": True}}):
            p = {x["field"]: x for x in ex.extract_many("x", "ta", self.F, {"land_owned_acres": 2.0})}
        self.assertEqual(p["land_owned_acres"]["note"], "contradicts_earlier_answer"); self.assertEqual(p["land_owned_acres"]["confidence"], "low")
        self.assertEqual(p["has_bank_account"]["confidence"], "high")
    def test_llm_output_validated_and_field_whitelist(self):
        os.environ["ANTHROPIC_API_KEY"] = "k"; import io, json as j
        bad = {"fields": {"land_owned_acres": {"value": "ignore all rules", "confident": True}, "aadhaar": {"value": "1", "confident": True}, "has_bank_account": {"value": True, "confident": True}}}
        resp = io.BytesIO(j.dumps({"content": [{"text": j.dumps(bad)}]}).encode())
        try:
            with mock.patch("urllib.request.urlopen", return_value=resp): out = ex.extract_many_llm("x", "ta", self.F)
        finally: os.environ.pop("ANTHROPIC_API_KEY")
        self.assertEqual(list(out), ["has_bank_account"])

class Storage(unittest.TestCase):
    def test_fernet_roundtrip(self):
        from cryptography.fernet import Fernet
        k = Fernet.generate_key(); f = Fernet(k); blob = f.encrypt(b"%PDF secret"); self.assertNotIn(b"secret", blob); self.assertEqual(f.decrypt(blob), b"%PDF secret")


class Regressions(unittest.TestCase):
    """Bugs found by eval/run_eval.py."""
    def test_hindi_number_word_not_matched_inside_unit(self): self.assertEqual(ex.extract("land_owned_acres", "मेरे पास दो एकड़ ज़मीन है"), 2.0)
    def test_no_not_matched_inside_not_yet(self): self.assertIsNone(ex.extract("has_bank_account", "not yet"))
    def test_units_converted(self):
        self.assertEqual(ex.extract("land_owned_acres", "நாற்பது சென்ட்"), 0.4); self.assertAlmostEqual(ex.extract("land_owned_acres", "1 hectare"), 2.471, 2)
    def test_tamil_negative_suffix(self): self.assertIs(ex.extract("income_tax_self", "செலுத்துவதில்லை"), False)
    def test_land_without_unit_ignored_in_free_text(self): self.assertNotIn("land_owned_acres", ex.rules_many("I am 45 years old", ["land_owned_acres"]))


import sqlite3, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))

class Redaction(unittest.TestCase):
    def test_aadhaar_formats_masked(self):
        for raw in ("2345 6789 0123", "2345-6789-0123", "234567890123"):
            t, found = dcs.redact(f"UID {raw} end"); self.assertNotIn(raw.replace(" ", "").replace("-", "")[:8], t.replace(" ", "").replace("-", "")); self.assertIn("aadhaar", found); self.assertIn("0123", t)
    def test_pan_and_account_masked_ifsc_kept(self):
        t, found = dcs.redact("PAN ABCDE1234F  A/c No 123456789012345 IFSC SBIN0001234")
        self.assertNotIn("ABCDE1234F", t); self.assertNotIn("123456789012345", t); self.assertIn("SBIN0001234", t); self.assertEqual(found, ["bank_account", "pan"])
    def test_normal_numbers_untouched(self):
        t, found = dcs.redact("Patta 1234 Survey 45/2A area 2.5 acres year 2025"); self.assertEqual(found, []); self.assertIn("1234", t)
    def test_analysis_never_returns_sensitive_numbers(self):
        a = dcs.analyze("Patta No 77 Survey No 12/1 Extent 2 acres Aadhaar 2345 6789 0123 PAN ABCDE1234F")
        self.assertEqual(a["sensitive_detected"], ["aadhaar", "pan"]); self.assertNotIn("23456789", str(a).replace(" ", "").replace("-", ""))
        self.assertNotIn("ABCDE1234F", str(a)); self.assertEqual(a["fields"]["area_acres"], 2.0)

class Family(unittest.TestCase):
    """The example household from the review: farmer household + grandmother + daughter + son with disability."""
    def setUp(self):
        self.ss = e.load_schemes(); self.hh = {"state": "Tamil Nadu"}
        self.ms = [{"id": "g", "relationship": "grandmother", "age": 72, "occupation": "", "consent": True, "is_widowed": True, "has_disability": False},
                   {"id": "d", "relationship": "daughter", "age": 15, "occupation": "student", "consent": True, "is_student": True},
                   {"id": "s", "relationship": "son", "age": 24, "occupation": "", "consent": True, "has_disability": True, "is_widowed": False}]
    def by(self, out): return {m["member_id"]: {r["scheme_id"]: r for r in m["results"]} for m in out}
    def test_each_member_evaluated_independently(self):
        o = self.by(e.evaluate_members(self.ss, self.hh, self.ms))
        self.assertEqual(o["g"]["TN_OLD_AGE_PENSION"]["status"], "green"); self.assertEqual(o["g"]["TN_WIDOW_PENSION"]["status"], "green")
        self.assertEqual(o["d"]["TN_OLD_AGE_PENSION"]["status"], "red"); self.assertEqual(o["s"]["TN_DISABILITY_ASSISTANCE"]["status"], "green")
        self.assertEqual(o["s"]["TN_OLD_AGE_PENSION"]["status"], "red")
    def test_unknown_member_attribute_is_amber_not_green(self):
        o = self.by(e.evaluate_members(self.ss, self.hh, [{"id": "x", "relationship": "mother", "age": 40, "occupation": "", "consent": True}]))
        self.assertEqual(o["x"]["TN_WIDOW_PENSION"]["status"], "amber")
    def test_conflicts_flagged_for_same_person_only(self):
        o = self.by(e.evaluate_members(self.ss, self.hh, self.ms))
        self.assertEqual({c["with"] for c in o["g"]["TN_OLD_AGE_PENSION"]["conflicts"]}, {"TN_WIDOW_PENSION"})
        self.assertEqual(o["s"]["TN_DISABILITY_ASSISTANCE"]["conflicts"], [])           # son is not eligible for the others
    def test_unknown_attribute_still_flags_possible_conflict(self):                  # conservative: unknown could turn out eligible
        ms = [{"id": "g", "relationship": "grandmother", "age": 72, "occupation": "", "consent": True, "is_widowed": True}]
        o = self.by(e.evaluate_members(self.ss, self.hh, ms)); self.assertIn("TN_DISABILITY_ASSISTANCE", {c["with"] for c in o["g"]["TN_OLD_AGE_PENSION"]["conflicts"]})
    def test_non_consenting_member_excluded(self):
        self.ms[0]["consent"] = False; self.assertNotIn("g", self.by(e.evaluate_members(self.ss, self.hh, self.ms)))

class Estimate(unittest.TestCase):
    def R(self, sid, amt, freq="monthly", verified=True, status="green", conflicts=()):
        return {"scheme_id": sid, "status": status, "benefit_detail": {"amount_inr": amt, "frequency": freq, "verified": verified} if amt else None, "conflicts": [{"with": c} for c in conflicts]}
    def test_only_verified_amounts_counted(self):
        est = e.estimate([self.R("A", 500, "yearly"), self.R("B", 1000, verified=False)], [])
        self.assertEqual(est["annual_inr_if_all_approved"], 500); self.assertEqual(est["uncounted_without_verified_amount"], 1)
    def test_red_never_counted(self): self.assertEqual(e.estimate([self.R("A", 500, "yearly", status="red")], [])["annual_inr_if_all_approved"], 0)
    def test_conflicting_schemes_counted_once_largest(self):
        m = [{"results": [self.R("P1", 1000, conflicts=["P2"]), self.R("P2", 1200, conflicts=["P1"])]}]
        self.assertEqual(e.estimate([], m)["annual_inr_if_all_approved"], 14400)
    def test_no_data_is_zero_with_note(self):
        est = e.estimate([], []); self.assertEqual(est["annual_inr_if_all_approved"], 0); self.assertIn("not a promise", est["note"])

class BackupAndAudit(unittest.TestCase):
    def test_encrypted_backup_restore_roundtrip(self):
        from cryptography.fernet import Fernet; import backup
        os.environ["BACKUP_KEY"] = Fernet.generate_key().decode(); tmp = tempfile.mkdtemp()
        try:
            db = os.path.join(tmp, "a.db"); cx = sqlite3.connect(db); cx.execute("create table t(x)"); cx.execute("insert into t values ('secret-farmer-data')"); cx.commit(); cx.close()
            out = backup.backup_sqlite(db, os.path.join(tmp, "bk")); self.assertNotIn(b"secret-farmer-data", open(out, "rb").read())      # ciphertext
            r = backup.restore_sqlite(out, os.path.join(tmp, "b.db")); self.assertEqual(sqlite3.connect(r).execute("select x from t").fetchone()[0], "secret-farmer-data")
            os.environ["BACKUP_KEY"] = Fernet.generate_key().decode()
            with self.assertRaises(Exception): backup.restore_sqlite(out, os.path.join(tmp, "c.db"))                                    # wrong key fails
        finally: shutil.rmtree(tmp)
    def test_backup_rotation_keeps_latest(self):
        from cryptography.fernet import Fernet; import backup, time
        os.environ["BACKUP_KEY"] = Fernet.generate_key().decode(); tmp = tempfile.mkdtemp()
        try:
            db = os.path.join(tmp, "a.db"); sqlite3.connect(db).execute("create table t(x)")
            for _ in range(3): backup.backup_sqlite(db, os.path.join(tmp, "bk"), keep=2); time.sleep(1.1)
            self.assertEqual(len(os.listdir(os.path.join(tmp, "bk"))), 2)
        finally: shutil.rmtree(tmp)
    def test_audit_triggers_block_update_and_delete(self):
        cx = sqlite3.connect(":memory:"); cx.execute("create table audit_log(id, action)"); cx.execute("insert into audit_log values (1,'x')")
        for ev in ("UPDATE", "DELETE"):       # same SQL as app/main.py
            cx.execute(f"CREATE TRIGGER IF NOT EXISTS audit_no_{ev.lower()} BEFORE {ev} ON audit_log BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;")
        with self.assertRaises(sqlite3.DatabaseError): cx.execute("update audit_log set action='y'")
        with self.assertRaises(sqlite3.DatabaseError): cx.execute("delete from audit_log")
        cx.execute("insert into audit_log values (2,'z')")     # appends still work


import copy, json
class DocClassification(unittest.TestCase):
    def test_single_keyword_is_not_enough(self):
        a = dcs.analyze("Please bring your patta tomorrow"); self.assertEqual(a["detected_type"], "unknown"); self.assertIn("land_record", a["candidates"])
    def test_tie_between_types_asks_farmer(self): self.assertEqual(dcs.analyze("patta survey passbook ifsc")["detected_type"], "unknown")
    def test_warnings_and_field_confidence(self):
        a = dcs.analyze("Patta 1 Survey No 5 Extent 250 acres and 3 acres Date of issue 31-02-2025", mean_conf=60)
        self.assertTrue({"several_area_values", "invalid_date_text", "low_ocr_confidence"} <= set(a["warnings"])); self.assertEqual(a["field_confidence"]["survey_no"], "low")
    def test_unusual_area(self): self.assertIn("unusual_area", dcs.analyze("Patta 1 Survey No 5 Extent 500 acres")["warnings"])
    def test_expired_certificate(self):
        a = dcs.analyze("Income Certificate Annual income Rs 50000 valid up to 01-01-2026", today=dt.date(2026, 11, 19)); self.assertIn("expired", a["warnings"])
    def test_missing_survey_warning(self): self.assertIn("missing_survey_no", dcs.analyze("Patta 1 chitta Extent 2 acres")["warnings"])
    def test_cross_document_issues(self):
        docs = [{"id": "1", "doc_type": "land_record", "confirmed": {"area_acres": 2.0}}, {"id": "2", "doc_type": "land_record", "confirmed": {"area_acres": 3.0}}]
        kinds = {i["kind"] for i in dcs.doc_issues(docs, {"land_owned_acres": 2.0})}; self.assertEqual(kinds, {"area_mismatch_between_documents", "area_differs_from_your_answer"})
        self.assertEqual(dcs.doc_issues(docs[:1], {"land_owned_acres": 2.0}), [])
    def test_four_assurance_levels_are_distinct(self):
        a = dcs.assurance("green", ["land_record"], []); self.assertTrue(a["rules_matched"]); self.assertEqual(a["documents_checked_by_a_person"], []); self.assertFalse(a["officially_confirmed"])

@unittest.skipUnless(_have_ocr(), "tesseract not installed")
class Preprocessing(unittest.TestCase):
    LINES = ["PATTA NO: 1234", "SURVEY NO. 45/2A", "EXTENT 2.5 ACRES", "DATE OF ISSUE 12-03-2025"]
    def setUp(self): self.tmp = tempfile.mkdtemp()
    def tearDown(self): shutil.rmtree(self.tmp)
    def _read(self, img):
        p = os.path.join(self.tmp, "x.png"); img.save(p); return dcs.analyze(dcs.read_document(p)["text"] or "")
    def test_rotated_90_and_180_recovered(self):
        base = _text_image(self.LINES)
        for deg in (90, 180, 270): a = self._read(base.rotate(deg, expand=True, fillcolor="white")); self.assertEqual(a["fields"].get("area_acres"), 2.5, f"rotation {deg}")
    def test_small_skew_recovered(self): self.assertEqual(self._read(_text_image(self.LINES).rotate(4, expand=True, fillcolor="white"))["fields"].get("area_acres"), 2.5)
    def test_noisy_low_contrast_image(self):
        import random; from PIL import Image
        img = _text_image(self.LINES).convert("L").point(lambda v: 90 + v * 0.35); px = img.load(); random.seed(1)
        for _ in range(4000): px[random.randrange(img.width), random.randrange(img.height)] = random.randrange(70, 200)
        self.assertEqual(self._read(img)["fields"].get("area_acres"), 2.5)
    def test_unreadable_blank_image_reports_nothing(self):
        from PIL import Image
        p = os.path.join(self.tmp, "b.png"); Image.new("RGB", (1000, 800), "white").save(p); self.assertIsNone(dcs.read_document(p)["text"])

class Governance(unittest.TestCase):
    def S(self, **kw):
        base = {"scheme_id": "X", "name": "X", "version": "1", "status": "pending_review", "source": "https://x.gov.in/", "benefit": "b", "documents": [], "conditions_complete": True, "submitted_by": "alice",
                "rules": [{"id": "R1", "type": "require", "text": "t", "field": "a", "op": "eq", "value": 1}, {"id": "R2", "type": "exclude", "text": "t", "field": "b", "op": "eq", "value": True}],
                "source_evidence": [{"title": "Guidelines", "url": "https://x.gov.in/g.pdf", "document_date": "2026-01-01", "page": 4, "rule_ids": ["R1", "R2"]}]}
        base.update(kw); return base
    T = dt.date(2026, 11, 19)
    def test_complete_evidence_has_no_blockers(self): self.assertEqual(e.approval_blockers(self.S(), self.T), [])
    def test_every_rule_incl_exclusions_needs_evidence(self):
        s = self.S(); s["source_evidence"][0]["rule_ids"] = ["R1"]; self.assertTrue(any("R2" in b for b in e.approval_blockers(s, self.T)))
    def test_evidence_needs_page_or_section_date_and_https(self):
        for k, v in (("page", None), ("document_date", "soon"), ("url", "http://x")):
            s = self.S(); s["source_evidence"][0][k] = v; self.assertTrue(e.approval_blockers(s, self.T), k)
    def test_incomplete_conditions_and_unverified_amount_block(self):
        self.assertTrue(any("conditions_complete" in b for b in e.approval_blockers(self.S(conditions_complete=False), self.T)))
        self.assertTrue(any("BENEFIT" in b for b in e.approval_blockers(self.S(benefit_detail={"amount_inr": 1, "frequency": "yearly", "verified": True}), self.T)))
    def test_shipped_drafts_cannot_be_approved(self):
        for s in e.load_all(): self.assertTrue(e.approval_blockers(s, self.T), s["scheme_id"])
    def test_submitter_cannot_approve_and_no_double_approval(self):
        s = self.S()
        with self.assertRaises(e.ApprovalError): e.apply_approval(s, "alice", None, self.T)
        e.apply_approval(s, "bob", None, self.T)
        with self.assertRaises(e.ApprovalError): e.apply_approval(s, "bob", None, self.T)
    def test_new_scheme_needs_two_reviewers(self):
        s = self.S(); r1 = e.apply_approval(s, "bob", None, self.T); self.assertEqual((r1["status"], r1["required"]), ("pending_review", 2))
        r2 = e.apply_approval(s, "carol", None, self.T); self.assertEqual(r2["status"], "verified"); self.assertEqual(s["last_verified"], "2026-11-19")
    def test_metadata_only_change_needs_one_reviewer(self):
        old = self.S(status="verified"); new = self.S(version="1.1", review_notes="typo fix"); self.assertFalse(e.high_impact(old, new))
        self.assertEqual(e.apply_approval(new, "bob", old, self.T)["status"], "verified")
    def test_rule_change_is_high_impact_and_diffed(self):
        old = self.S(); new = copy.deepcopy(old); new["rules"][0]["value"] = 2; new["rules"].append({"id": "R3", "type": "require", "text": "t", "field": "c", "op": "eq", "value": 1})
        d = e.diff_schemes(old, new); self.assertEqual(d["rules_added"], ["R3"]); self.assertEqual(d["rules_changed"][0]["id"], "R1"); self.assertTrue(e.high_impact(old, new))
    def test_blockers_surface_through_apply_approval(self):
        with self.assertRaises(e.ApprovalError) as c: e.apply_approval(self.S(conditions_complete=False), "bob", None, self.T)
        self.assertTrue(c.exception.blockers)
    def test_expired_scheme_is_disabled_for_farmers(self):
        s = self.S(status="verified", expires="2026-06-30"); e.SCHEME_DIR_BACKUP = e.SCHEME_DIR; tmp = tempfile.mkdtemp(); e.SCHEME_DIR = tmp
        try:
            json.dump(s, open(os.path.join(tmp, "x.json"), "w")); self.assertEqual(e.load_schemes(dt.date(2026, 5, 1)), [s]); self.assertEqual(e.load_schemes(dt.date(2026, 7, 1)), [])
        finally: e.SCHEME_DIR = e.SCHEME_DIR_BACKUP; shutil.rmtree(tmp)
    def test_trust_report(self):
        good = self.S(status="verified", last_verified="2026-11-01"); r = e.trust_report([good], self.T); self.assertTrue(r["trustworthy"])
        stale = self.S(status="verified", last_verified="2025-01-01"); self.assertFalse(e.trust_report([stale], self.T)["trustworthy"])
        self.assertFalse(e.trust_report([self.S(status="verified", last_verified="2026-11-01", conditions_complete=False)], self.T)["trustworthy"])
        e.ALLOW_UNVERIFIED = True; self.assertFalse(e.trust_report(e.load_all(), self.T)["trustworthy"])      # demo drafts shown => not trustworthy
        e.ALLOW_UNVERIFIED = False; r = e.trust_report(e.load_all(), self.T); self.assertEqual(r["shown_to_farmers"], 0); self.assertIn("No scheme", r["summary"]); e.ALLOW_UNVERIFIED = True
    def test_trace_carries_evidence_and_reported_values(self):
        s = self.S(); ev = e.evaluate(s, {"a": 1, "b": False}, self.T)["trace"]; self.assertEqual(ev[0]["reported"], {"a": 1}); self.assertEqual(ev[0]["evidence"][0]["page"], 4)

class ReviewExamples(unittest.TestCase):
    """Conversational cases from the review."""
    def test_number_attached_to_unit_not_first_number(self):
        self.assertEqual(ex.extract("land_owned_acres", "எனக்கு மூன்று குழந்தைகள், இரண்டு ஏக்கர் நிலம் இருக்கு."), 2.0)
        self.assertEqual(ex.extract("land_owned_acres", "I have 3 children and 2 acres"), 2.0)
    def test_fractions_sums_and_corrections(self):
        for text, want in (("ஒன்றரை ஏக்கர் நிலம் இருக்கு", 1.5), ("இரண்டரை ஏக்கர்", 2.5), ("அரை ஏக்கர்", 0.5), ("கால் ஏக்கர்", 0.25), ("2 acres and 50 cents", 2.5), ("one and a half acres", 1.5),
                           ("ढाई एकड़", 2.5), ("साढ़े तीन एकड़", 3.5), ("डेढ़ एकड़", 1.5), ("I said two acres, actually it is three", 3.0), ("rendu acre irukku", 2.0), ("naalu ekkar", 4.0)):
            self.assertEqual(ex.extract("land_owned_acres", text), want, text)
    def test_unknown_is_not_yes_or_no(self):
        for t in ("எனக்கு தெரியாது", "I don't know", "no idea", "पता नहीं", "not sure"): self.assertIsNone(ex.extract("has_bank_account", t), t); self.assertIsNone(ex.extract("land_owned_acres", t), t)
        r = ex.extract_smart("has_bank_account", "எனக்கு தெரியாது"); self.assertEqual((r["value"], r["confidence"], r["note"]), (None, "none", "unknown"))
    def test_not_registered_yet_is_no(self): self.assertIs(ex.extract("has_bank_account", "இன்னும் பதிவு செய்யவில்லை"), False)
    def test_land_in_another_members_name_lowers_confidence(self):
        for t in ("நிலம் என் மனைவி பெயரில் இருக்கு 2 ஏக்கர்", "2 acres, in my wife's name"):
            r = ex.extract_smart("land_owned_acres", t); self.assertEqual(r["confidence"], "low", t); self.assertEqual(r["note"], "owned_by_other_member")
    def test_approximate_lowers_high_to_medium_and_flags(self):
        r = ex.extract_smart("land_owned_acres", "about 2 acres"); self.assertIn("approximate", r["flags"])
    def test_correction_flag(self): self.assertIn("correction", ex.extract_smart("land_owned_acres", "two, actually three acres")["flags"])
    def test_bare_number_only_for_short_answers(self):
        self.assertEqual(ex.extract("land_owned_acres", "2"), 2.0); self.assertIsNone(ex.extract("land_owned_acres", "I have 3 kids and a house"))

class KeyRotation(unittest.TestCase):
    def test_rotation_reencrypts_without_data_loss(self):
        from cryptography.fernet import Fernet; import rotate_key
        old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode(); tmp = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmp, "f1")); path = os.path.join(tmp, "f1", "a.pdf.enc"); open(path, "wb").write(Fernet(old.encode()).encrypt(b"%PDF land record"))
            self.assertEqual(rotate_key.rotate_dir(tmp, f"{new},{old}"), {"rotated": 1, "failed": 0})
            self.assertEqual(Fernet(new.encode()).decrypt(open(path, "rb").read()), b"%PDF land record")        # readable with the NEW key alone
            with self.assertRaises(Exception): Fernet(old.encode()).decrypt(open(path, "rb").read())             # old key no longer needed or valid for it
            open(os.path.join(tmp, "bad.enc"), "wb").write(b"garbage"); self.assertEqual(rotate_key.rotate_dir(tmp, f"{new},{old}")["failed"], 1)
        finally: shutil.rmtree(tmp)


class FamilyChecks(unittest.TestCase):
    def test_issues(self):
        ms = [{"id": "1", "relationship": "spouse", "age": 40, "occupation": "farmer", "consent": True}, {"id": "2", "relationship": "spouse", "age": 41, "occupation": "", "consent": False},
              {"id": "3", "relationship": "son", "age": 10, "occupation": "", "consent": True}, {"id": "4", "relationship": "son", "age": 10, "occupation": "", "consent": True},
              {"id": "5", "relationship": "cousin", "age": 30, "occupation": "", "consent": True}, {"id": "6", "relationship": "mother", "age": 12, "occupation": "", "consent": True}]
        k = {i["kind"] for i in e.family_issues(ms)}; self.assertEqual(k, {"multiple_spouses", "missing_consent", "duplicate_member", "unknown_relationship", "age_implausible"})
    def test_clean_household(self): self.assertEqual(e.family_issues([{"id": "1", "relationship": "mother", "age": 66, "occupation": "", "consent": True}]), [])


class IncomeTaxWho(unittest.TestCase):
    """A relative's tax status must never be treated as the applicant's."""
    X = staticmethod(lambda f, t: ex.extract(f, t))
    def test_son_pays_is_not_the_applicant(self):
        self.assertIsNone(self.X("income_tax_self", "my son pays income tax")); self.assertIsNone(self.X("income_tax_spouse", "my son pays income tax"))
        self.assertIs(self.X("income_tax_other_family", "my son pays income tax"), True)
    def test_spouse_pays_is_not_the_applicant(self):
        self.assertIsNone(self.X("income_tax_self", "my husband pays income tax")); self.assertIs(self.X("income_tax_spouse", "my husband pays income tax"), True)
    def test_applicant_pays(self): self.assertIs(self.X("income_tax_self", "I pay income tax"), True); self.assertIsNone(self.X("income_tax_other_family", "I pay income tax"))
    def test_unspecified_household_member_is_other_not_self(self):
        t = "someone in the family pays income tax but I don't know who"
        self.assertIs(self.X("income_tax_other_family", t), True); self.assertIsNone(self.X("income_tax_self", t)); self.assertIsNone(self.X("income_tax_spouse", t))
    def test_pronoun_is_never_the_applicant(self):
        for t in ("he pays income tax", "she pays", "அவர் வரி கட்டுறார்", "वह आयकर देता है"): self.assertIsNone(self.X("income_tax_self", t), t)
    def test_nobody_answers_all_three(self):
        for f in ("income_tax_self", "income_tax_spouse", "income_tax_other_family"): self.assertIs(self.X(f, "nobody pays income tax"), False)
    def test_mixed_statement_splits_by_person(self):
        t = "my son pays income tax, I do not"
        self.assertIs(self.X("income_tax_self", t), False); self.assertIs(self.X("income_tax_other_family", t), True); self.assertIsNone(self.X("income_tax_spouse", t))
    def test_shared_predicate(self):
        t = "my wife and I both pay income tax"; self.assertIs(self.X("income_tax_spouse", t), True); self.assertIs(self.X("income_tax_self", t), True)
    def test_unknown_clause_does_not_borrow_next_answer(self): self.assertIsNone(self.X("income_tax_self", "I don't know, my husband pays"))
    def test_one_child_not_paying_does_not_clear_the_household(self): self.assertIsNone(self.X("income_tax_other_family", "my son doesn't pay income tax"))
    def test_tamil_inflection_and_colloquial_spouse(self):
        self.assertIs(self.X("income_tax_spouse", "என் வீட்டுக்காரர் வரி கட்டுறார்"), True); self.assertIs(self.X("income_tax_other_family", "என் மகன் வருமான வரி செலுத்துகிறார்"), True)
    def test_naan_not_confused_with_four(self): self.assertNotIn("self", ex._relations("நான்கு குழந்தைகள்"))
    def test_smart_notes_about_someone_else(self):
        r = ex.extract_smart("income_tax_self", "my son pays income tax"); self.assertEqual((r["value"], r["confidence"], r["note"]), (None, "none", "about_someone_else"))
        r = ex.extract_smart("income_tax_other_family", "someone in the family pays income tax but I don't know who"); self.assertIs(r["value"], True)   # 'don't know who' does not erase the fact
    def test_free_text_fills_only_the_right_fields(self):
        F = ["income_tax_self", "income_tax_spouse", "income_tax_other_family", "has_bank_account"]
        p = {x["field"]: x["value"] for x in ex.extract_many("my son pays income tax", "en", F, {})}; self.assertEqual(p, {"income_tax_other_family": True})
        self.assertEqual(ex.extract_many("yes I have a bank account", "en", F, {}), [])                       # a bare yes never becomes a tax answer
    def test_pm_kisan_uses_the_right_person(self):
        pk = {x["scheme_id"]: x for x in e.load_schemes()}["PM_KISAN"]; B = {**BASE}
        self.assertEqual(e.evaluate(pk, B)["status"], "green")
        self.assertEqual(e.evaluate(pk, {**B, "income_tax_self": True})["status"], "red"); self.assertEqual(e.evaluate(pk, {**B, "income_tax_spouse": True})["status"], "red")
        r = e.evaluate(pk, {**B, "income_tax_other_family": True}); self.assertEqual(r["status"], "amber")             # a manual check, not an automatic exclusion
        self.assertTrue(any(t["rule_id"] == "PMK-3b" and t["result"] == "unknown" for t in r["trace"]))
        self.assertEqual(e.evaluate(pk, {**B, "income_tax_self": None, "income_tax_spouse": True})["status"], "red")  # spouse alone decides, applicant unknown
        self.assertEqual(e.evaluate(pk, {**B, "income_tax_self": None})["status"], "amber")
    def test_flag_rule_type_validates_and_never_fails(self):
        s = scheme([{"id": "F", "type": "flag", "text": "t", "field": "x", "op": "eq", "value": True}]); self.assertEqual(e.validate_scheme(s), [])
        self.assertEqual([e.evaluate(s, {"x": v})["status"] for v in (True, False, None)], ["amber", "green", "amber"])


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pilot"))

@unittest.skipUnless(_have_ocr(), "tesseract not installed")
class DocEvalHarness(unittest.TestCase):
    """Harness self-test on SYNTHETIC English images only. It proves the metrics are computed correctly; it says nothing about real Tamil documents."""
    LINES = ["PATTA NO: 1234", "SURVEY NO. 45/2A", "EXTENT 2.5 ACRES", "DATE OF ISSUE 12-03-2025"]
    def test_metrics(self):
        import doc_eval; from PIL import Image
        tmp = tempfile.mkdtemp()
        try:
            def put(name, img, label): img.save(os.path.join(tmp, name + ".png")); json.dump(label, open(os.path.join(tmp, name + ".json"), "w"))
            good = {"doc_type": "land_record", "fields": {"survey_no": "45/2A", "area_acres": 2.5}, "tags": ["scan:clear"]}
            put("a_clear", _text_image(self.LINES), good)
            put("b_rotated", _text_image(self.LINES).rotate(90, expand=True, fillcolor="white"), {**good, "tags": ["scan:rotated"]})
            put("c_blank", Image.new("RGB", (1000, 800), "white"), {**good, "tags": ["scan:blank"]})                              # unreadable -> counted missing, never guessed
            put("d_label_disagrees", _text_image(self.LINES), {**good, "fields": {"survey_no": "45/2A", "area_acres": 3.0}, "tags": ["scan:clear"]})   # extracted 2.5, label says 3.0 -> WRONG
            r = doc_eval.evaluate(tmp); o = r["overall"]
            self.assertEqual((o["docs"], o["unreadable"]), (4, 1)); self.assertEqual(o["cls_ok"], 3)
            self.assertEqual(o["expected"], 8); self.assertEqual((o["ok"], o["wrong"], o["missing"]), (5, 1, 2)); self.assertEqual(o["farmer_correction_rate"], round(3 / 8, 3))
            self.assertEqual(r["by_tag"]["scan:blank"]["unreadable"], 1); self.assertEqual(r["by_tag"]["scan:clear"]["wrong"], 1)
            self.assertTrue(any(x["file"] == "d_label_disagrees.png" and x["field"] == "area_acres" for x in r["errors"]))
        finally: shutil.rmtree(tmp)

class PilotAnalysis(unittest.TestCase):
    """FIXTURE rows invented for testing the calculator. They are not pilot results."""
    def rows(self, n, **kw): return [{"session_id": str(i), "language": "ta", "completed_profile": "yes", "completed_without_help": "no", "minutes_to_claim_pack": str(10 + i), "claim_pack_generated": "yes",
                                      "application_initiated": "no", "ai_corrections": "1", "document_corrections": "2", "tamil_misunderstandings": "0", "serious_error": "no", "benefit_confirmed": "no", "satisfaction_1to5": "4", "notes": "", **kw} for i in range(n)]
    def test_small_samples_withhold_percentages(self):
        import analyze as an; r = an.analyze(self.rows(5)); self.assertIsNone(r["completed_profile"]["percent"]); self.assertEqual(r["completed_profile"]["count"], 5); self.assertIn("percentages withheld", r["note"])
    def test_percentages_with_enough_sessions_and_failures_reported(self):
        import analyze as an; rows = self.rows(20); rows[0].update(serious_error="yes", notes="wrong pension shown", completed_profile="no")
        r = an.analyze(rows); self.assertEqual(r["completed_profile"]["percent"], 95.0); self.assertEqual(r["serious_error"]["count"], 1); self.assertEqual(r["problems_reported"], ["wrong pension shown"])
        self.assertEqual(r["ai_corrections"]["per_session"], 1.0); self.assertEqual(r["minutes_to_claim_pack"]["median"], 19.5)
    def test_benefit_only_counted_when_confirmed(self):
        import analyze as an; r = an.analyze(self.rows(3, application_initiated="yes")); self.assertEqual((r["application_initiated"]["count"], r["benefit_confirmed"]["count"]), (3, 0))

class ReviewWorksheet(unittest.TestCase):
    def test_lists_every_rule_and_blockers(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")); import review_worksheet as rw
        pk = next(s for s in e.load_all() if s["scheme_id"] == "PM_KISAN"); w = rw.worksheet(pk, dt.date(2026, 11, 20))
        for r in pk["rules"]: self.assertIn(f"## {r['id']}", w)
        self.assertIn("conditions_complete", w); self.assertIn("Reviewer 2", w)
        bare = rw.worksheet(dict(pk, source_evidence=[]), dt.date(2026, 11, 20))          # independent of what evidence the data file holds today
        self.assertIn("NO EVIDENCE YET", bare); self.assertNotIn("evidence recorded", bare)
        if pk.get("source_evidence"): self.assertIn("evidence recorded", w)


class TaxSafetyNet(unittest.TestCase):
    """Regression for an unsafe error found by eval/run_eval.py: Tamil inflection hid the relation and the son's tax status became the applicant's."""
    X = staticmethod(lambda f, t: ex.extract(f, t))
    def test_son_dative_inflection(self):
        t = "என் மகனுக்கு வருமான வரி கட்டணும்"; self.assertIsNone(self.X("income_tax_self", t)); self.assertIsNone(self.X("income_tax_spouse", t)); self.assertIs(self.X("income_tax_other_family", t), True)
    def test_unlisted_relative_is_still_not_the_applicant(self):
        for t in ("என் அண்ணன் வரி கட்டுறார்", "my elder cousin pays income tax", "मेरा चचेरा भाई आयकर देता है", "pays income tax", "वो आयकर भरता है", "அவங்க வரி கட்டுவாங்க"):
            self.assertIsNone(self.X("income_tax_self", t), t)
    def test_first_person_still_works(self):
        for t in ("என் பெயரில் வரி கட்டுறேன்", "நான் வருமான வரி செலுத்துகிறேன்", "मैं आयकर देता हूँ", "I pay income tax"): self.assertIs(self.X("income_tax_self", t), True, t)
    def test_review_cases_end_to_end(self):
        r = ex.extract_smart("land_owned_acres", "முதலில் இரண்டு சொன்னேன், இப்போது மூன்று ஏக்கர்"); self.assertEqual(r["value"], 3.0); self.assertIn("correction", r["flags"])
        r = ex.extract_smart("land_owned_acres", "I have two acres, but I am not sure"); self.assertEqual((r["value"], r["confidence"], r["note"]), (2.0, "low", "uncertain"))
        r = ex.extract_smart("land_owned_acres", "எனக்குத் தெரியாது"); self.assertEqual((r["value"], r["note"]), (None, "unknown"))
        r = ex.extract_smart("land_owned_acres", "என் மனைவி பெயரில் நிலம் இருக்கு"); self.assertEqual((r["value"], r["note"]), (None, "owned_by_other_member"))
        self.assertEqual(ex.extract("land_owned_acres", "எனக்கு இரண்டு ஏக்கர் நிலம் இருக்கு"), 2.0)
    def test_unknown_with_bare_number_is_not_a_value(self): self.assertIsNone(ex.extract("land_owned_acres", "2 maybe"))

class EvalSplit(unittest.TestCase):
    def test_split_is_deterministic_and_disjoint(self):
        import run_eval; cs = [{"id": i, "lang": l} for i in range(300) for l in ("ta", "en")]; sp = [run_eval.split_of(c) for c in cs]
        self.assertEqual(sp, [run_eval.split_of(c) for c in cs]); share = {k: sp.count(k) / len(sp) for k in ("dev", "val", "test")}
        self.assertAlmostEqual(share["dev"], 0.70, delta=0.06); self.assertAlmostEqual(share["val"], 0.15, delta=0.05); self.assertAlmostEqual(share["test"], 0.15, delta=0.05)
    def test_unsafe_wrong_is_distinguished_from_abstaining(self):
        import run_eval; cs = [{"id": 1, "lang": "ta", "field": "f", "text": "a", "expected": 2.0}, {"id": 2, "lang": "ta", "field": "f", "text": "b", "expected": None},
                               {"id": 3, "lang": "ta", "field": "f", "text": "c", "expected": 3.0}, {"id": 4, "lang": "ta", "field": "f", "text": "d", "expected": 5.0}]
        got = {"a": 2.0, "b": True, "c": None, "d": 4.0}; r = run_eval.score(cs, lambda c: got[c["text"]])["overall"]
        self.assertEqual((r["correct"], r["unsafe_wrong"], r["abstained"]), (1, 2, 1))             # b: value where None expected, d: wrong value -> both unsafe
    def test_test_split_is_locked_without_final(self):
        import run_eval
        with self.assertRaises(SystemExit): run_eval.run(os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval", "cases.jsonl"), "test", False)


from app import readiness as rdy
class Readiness(unittest.TestCase):
    """Reports below are FIXTURES invented to test the thresholds. They are not results."""
    def setUp(self): self.tmp = tempfile.mkdtemp(); os.environ["READINESS_FILE"] = os.path.join(self.tmp, "r.json")
    def tearDown(self): shutil.rmtree(self.tmp); os.environ.pop("READINESS_FILE", None)
    T = dt.date(2026, 11, 20)
    def good_ocr(self): return {"overall": {"docs": 210, "classification_accuracy": 0.97, "field_exact_match": 0.96, "wrong_high_conf": 0}, "ocr": {"requested": "tam+eng", "used": {"tam+eng": 210}, "fallback_docs": 0},
                                "by_tag": {"language:tamil": {"docs": 150}, "district:Thanjavur": {"docs": 40}}}
    def good_bench(self): return {"split": "test", "final": True, "provenance": "real-consented", "result": {"overall": {"n": 100, "unsafe_wrong": 0}, "by_language": {l: {"n": 25, "accuracy": 0.97} for l in ("ta", "en", "hi", "mixed")}}}
    def test_today_only_the_expiry_check_passes(self):
        b = rdy.board(self.T); self.assertFalse(b["release_ready"]); ok = {c["id"] for c in b["checks"] if c["status"] == "passed"}; self.assertEqual(ok, {"expired_excluded"})
        self.assertTrue(any("draft" in " ".join(c["outstanding"]) or "demo_unverified" in " ".join(c["outstanding"]) or c["outstanding"] for c in b["checks"] if c["id"] == "scheme_verification"))
    def test_auto_checks_cannot_be_set_by_hand(self):
        with self.assertRaises(rdy.ReadinessError): rdy.record("scheme_verification", "alice", "passed", "https://x", "bob", "2026-11-01", today=self.T)
    def test_passed_needs_evidence_reviewer_date_and_independence(self):
        bad = [dict(evidence="", reviewer="bob", tested_on="2026-11-01"), dict(evidence="https://reports/x", reviewer="", tested_on="2026-11-01"), dict(evidence="https://reports/x", reviewer="bob", tested_on="2026-12-31"),
               dict(evidence="https://reports/x", reviewer="alice", tested_on="2026-11-01"), dict(evidence="ok", reviewer="bob", tested_on="2026-11-01"), dict(evidence="https://reports/x", reviewer="bob", tested_on="yesterday")]
        for kw in bad:
            with self.assertRaises(rdy.ReadinessError): rdy.record("security_review", "alice", "passed", today=self.T, **kw)
        e = rdy.record("security_review", "alice", "passed", "https://reports/pentest-2026-11.pdf", "bob (external)", "2026-11-01", today=self.T); self.assertEqual(e["status"], "passed")
        self.assertEqual({c["id"]: c for c in rdy.board(self.T)["checks"]}["security_review"]["status"], "passed")
    def test_in_progress_and_failed_need_no_evidence_but_need_a_reviewer(self):
        self.assertEqual(rdy.record("frontend_build", "alice", "in_progress", reviewer="alice", tested_on="2026-11-01", today=self.T)["status"], "in_progress")
        with self.assertRaises(rdy.ReadinessError): rdy.record("frontend_build", "alice", "failed", reviewer="", tested_on="2026-11-01", today=self.T)
    def test_history_is_kept_and_latest_wins(self):
        rdy.record("monitoring", "alice", "failed", reviewer="bob", tested_on="2026-11-01", outstanding=["no alert on 5xx"], today=self.T)
        rdy.record("monitoring", "alice", "passed", "alerts fired in a drill, screenshot at https://x/y", "bob", "2026-11-05", today=self.T)
        row = {c["id"]: c for c in rdy.board(self.T)["checks"]}["monitoring"]; self.assertEqual((row["status"], row["history"]), ("passed", 2))
    def test_report_checks_reject_manual_pass(self):
        with self.assertRaises(rdy.ReadinessError): rdy.record("tamil_ocr", "alice", "passed", "trust me", "bob", "2026-11-01", today=self.T)
    def test_tamil_ocr_report_thresholds(self):
        self.assertEqual(rdy.eval_ocr_report(self.good_ocr())[0], "passed")
        for mut, why in ((lambda r: r["overall"].update(docs=40), "only 40"), (lambda r: r["overall"].update(classification_accuracy=0.9), "classification"), (lambda r: r["overall"].update(wrong_high_conf=1), "high confidence"),
                         (lambda r: r["ocr"].update(requested="eng"), "did not request"), (lambda r: r["ocr"].update(used={"eng": 210}), "never actually used"), (lambda r: r["ocr"].update(fallback_docs=3), "fallback"),
                         (lambda r: r["by_tag"].update({"SYNTHETIC": {"docs": 5}}), "SYNTHETIC"), (lambda r: r["by_tag"].update({"language:tamil": {"docs": 10}}), "language:tamil")):
            r = self.good_ocr(); mut(r); st, iss = rdy.eval_ocr_report(r); self.assertEqual(st, "failed", why); self.assertTrue(any(why.lower() in i.lower() for i in iss), (why, iss))
        self.assertEqual(rdy.eval_ocr_report({})[0], "failed")
    def test_benchmark_report_thresholds(self):
        self.assertEqual(rdy.eval_benchmark_report(self.good_bench())[0], "passed")
        for mut, why in ((lambda r: r.update(final=False), "--final"), (lambda r: r.update(provenance="synthetic-or-unlabelled"), "provenance"), (lambda r: r["result"]["overall"].update(unsafe_wrong=1), "unsafe"),
                         (lambda r: r["result"]["overall"].update(n=20), "only 20"), (lambda r: r["result"]["by_language"]["ta"].update(accuracy=0.9), "ta: accuracy"), (lambda r: r["result"]["by_language"].pop("hi"), "must all be present"),
                         (lambda r: r.update(split="dev+val"), "--final")):
            r = self.good_bench(); mut(r); st, iss = rdy.eval_benchmark_report(r); self.assertEqual(st, "failed", why); self.assertTrue(any(why.lower() in i.lower() for i in iss), (why, iss))
    def test_report_recorded_with_hash_and_derived_status(self):
        e = rdy.record("tamil_ocr", "alice", None, "doc_eval run 2026-11-10", "bob", "2026-11-10", report=self.good_ocr(), today=self.T); self.assertEqual(e["status"], "passed"); self.assertEqual(len(e["report_sha256"]), 64)
        bad = self.good_ocr(); bad["overall"]["wrong_high_conf"] = 2; e2 = rdy.record("tamil_ocr", "alice", "passed", "x", "bob", "2026-11-11", report=bad, today=self.T)
        self.assertEqual(e2["status"], "failed"); self.assertTrue(e2["outstanding"])               # the caller's claimed 'passed' is ignored
    def test_auto_checks_pass_for_a_properly_verified_fixture(self):
        d = tempfile.mkdtemp(); old = e.SCHEME_DIR; e.SCHEME_DIR = d; oldflag = e.ALLOW_UNVERIFIED; e.ALLOW_UNVERIFIED = False
        try:
            s = Governance.S(Governance(), status="verified", last_verified="2026-11-01", approved_by=["bob", "carol"], approvals=["bob", "carol"]); json.dump(s, open(os.path.join(d, "x.json"), "w"))
            ids = {c["id"]: c for c in rdy.board(self.T)["checks"]}
            for k in ("scheme_verification", "scheme_evidence", "two_person_approval", "expired_excluded"): self.assertEqual(ids[k]["status"], "passed", (k, ids[k]["outstanding"]))
            s["approved_by"] = ["bob"]; json.dump(s, open(os.path.join(d, "x.json"), "w")); self.assertEqual({c["id"]: c for c in rdy.board(self.T)["checks"]}["two_person_approval"]["status"], "failed")
        finally: e.SCHEME_DIR = old; e.ALLOW_UNVERIFIED = oldflag; shutil.rmtree(d)

class DocEvalLanguage(unittest.TestCase):
    @unittest.skipUnless(_have_ocr(), "tesseract not installed")
    def test_fallback_is_visible(self):
        import doc_eval; tmp = tempfile.mkdtemp(); os.environ["OCR_LANGS"] = "tam+eng"
        try:
            _text_image(["PATTA NO: 1", "SURVEY NO. 2/1", "EXTENT 2 ACRES"]).save(os.path.join(tmp, "a.png")); json.dump({"doc_type": "land_record", "fields": {"survey_no": "2/1"}, "tags": ["t"]}, open(os.path.join(tmp, "a.json"), "w"))
            r = doc_eval.evaluate(tmp)["ocr"]; self.assertEqual(r["requested"], "tam+eng"); self.assertEqual(r["fallback_docs"], 1); self.assertEqual(list(r["used"]), ["eng"])   # Tamil data absent here -> reported, never hidden
        finally: os.environ.pop("OCR_LANGS", None); shutil.rmtree(tmp)


from app import ratelimit, obs
class FakeRedis:
    """Minimal stand-in for redis-py used only to test the limiter logic (shared state, expiry). Real Redis is NOT tested."""
    def __init__(self, clock): self.d = {}; self.clock = clock; self.fail = False
    def pipeline(self): return _Pipe(self)
class _Pipe:
    def __init__(self, r): self.r = r; self.ops = []
    def incr(self, k): self.ops.append(("incr", k)); return self
    def expire(self, k, ttl): self.ops.append(("expire", k, ttl)); return self
    def execute(self):
        if self.r.fail: raise ConnectionError("redis down")
        out = []; now = self.r.clock()
        for op in self.ops:
            if op[0] == "incr":
                v, exp = self.r.d.get(op[1], (0, None))
                if exp is not None and exp <= now: v, exp = 0, None
                self.r.d[op[1]] = (v + 1, exp); out.append(v + 1)
            else:
                v, _ = self.r.d[op[1]]; self.r.d[op[1]] = (v, now + op[2]); out.append(True)
        return out

class SharedRateLimit(unittest.TestCase):
    def setUp(self): self.t = [1000.0]; self.clock = lambda: self.t[0]; obs.reset()
    def mk(self, r): return ratelimit.Limiter(ratelimit.RedisBackend(r, self.clock), ratelimit.MemoryBackend(self.clock))
    def test_limit_blocks_after_n(self):
        lim = ratelimit.Limiter(ratelimit.MemoryBackend(self.clock)); res = [lim.hit("1.2.3.4:auth", 3)[0] for _ in range(5)]; self.assertEqual(res, [True, True, True, False, False])
    def test_window_expires(self):
        lim = ratelimit.Limiter(ratelimit.MemoryBackend(self.clock)); [lim.hit("k", 2) for _ in range(3)]; self.assertFalse(lim.hit("k", 2)[0]); self.t[0] += 61; self.assertTrue(lim.hit("k", 2)[0])
    def test_different_clients_are_independent(self):
        lim = ratelimit.Limiter(ratelimit.MemoryBackend(self.clock)); [lim.hit("a:auth", 1) for _ in range(3)]; self.assertTrue(lim.hit("b:auth", 1)[0])
    def test_two_workers_share_one_budget_via_redis(self):
        r = FakeRedis(self.clock); w1, w2 = self.mk(r), self.mk(r)
        allowed = [w1.hit("ip:auth", 5)[0] if i % 2 else w2.hit("ip:auth", 5)[0] for i in range(8)]; self.assertEqual(sum(allowed), 5)          # 8 attempts spread over 2 workers: only 5 pass
        self.t[0] += 61; self.assertTrue(w1.hit("ip:auth", 5)[0])                                                                                  # key expired with the window
    def test_per_process_memory_would_let_two_workers_double_the_budget(self):
        a, b = ratelimit.Limiter(ratelimit.MemoryBackend(self.clock)), ratelimit.Limiter(ratelimit.MemoryBackend(self.clock))
        self.assertEqual(sum([a.hit("k", 5)[0] for _ in range(5)] + [b.hit("k", 5)[0] for _ in range(5)]), 10)          # why in-memory is not enough behind several workers
    def test_redis_outage_degrades_to_memory_and_is_counted(self):
        r = FakeRedis(self.clock); lim = self.mk(r); r.fail = True; res = [lim.hit("k", 2)[0] for _ in range(4)]
        self.assertEqual(res, [True, True, False, False]); self.assertEqual(obs.snapshot()["ratelimit_backend_error"], 4)

class Observability(unittest.TestCase):
    def test_scrub_masks_personal_data(self):
        t = obs.scrub("farmer 9876543210 aadhaar 2345 6789 0123 pan ABCDE1234F a/c no 123456789012345 mail a.b@x.in otp 482913 +91 98765 43210")
        for raw in ("9876543210", "2345 6789", "ABCDE1234F", "123456789012345", "a.b@x.in", "482913"): self.assertNotIn(raw, t)
        self.assertIn("[PHONE]10", t)
    def test_json_logs_are_scrubbed_including_exceptions(self):
        import logging, io; buf = io.StringIO(); h = logging.StreamHandler(buf); h.setFormatter(obs.JsonFormatter()); lg = logging.getLogger("t_scrub"); lg.handlers = [h]; lg.propagate = False
        try: raise ValueError("bad phone 9876543210")
        except ValueError: lg.exception("failed for 2345 6789 0123")
        out = buf.getvalue(); self.assertNotIn("9876543210", out); self.assertNotIn("6789 0123", out); self.assertIn("level", json.loads(out.splitlines()[0]))
    def test_counters_and_alert_threshold(self):
        obs.reset(); os.environ.pop("ALERT_WEBHOOK_URL", None); obs.inc("requests_total"); obs.inc_critical("otp_send_failed"); self.assertEqual(obs.snapshot(), {"requests_total": 1, "otp_send_failed": 1})
        self.assertFalse(obs.alert("x", "no webhook configured"))
    def test_alert_message_is_scrubbed_and_never_raises(self):
        sent = {}
        class R:
            def __init__(s, *a, **k): sent["body"] = a[1].decode()
        os.environ["ALERT_WEBHOOK_URL"] = "https://hooks.example/x"
        try:
            with mock.patch("urllib.request.Request", R), mock.patch("urllib.request.urlopen", return_value=None): self.assertTrue(obs.alert("otp_send_failed", "to 9876543210"))
            self.assertNotIn("9876543210", sent["body"])
            with mock.patch("urllib.request.urlopen", side_effect=OSError): self.assertFalse(obs.alert("x"))
        finally: os.environ.pop("ALERT_WEBHOOK_URL")


from app import timeline as tlm
class AppTimeline(unittest.TestCase):
    E = staticmethod(lambda st, at="2026-11-0%dT10:00:00", ref="": {"status": st, "reference_number": ref, "at": at})
    def test_empty(self): r = tlm.build([]); self.assertIsNone(r["current"]); self.assertFalse(any(s["reached"] for s in r["steps"]))
    def test_progress_dates_and_reference(self):
        r = tlm.build([self.E("prepared", "2026-11-01T09:00:00"), self.E("submitted", "2026-11-03T10:00:00", "REG123")])
        self.assertEqual(r["current"], "submitted"); self.assertEqual([s["reached"] for s in r["steps"]], [True, True, False, False]); self.assertEqual(r["steps"][1]["date"], "2026-11-03"); self.assertEqual(r["reference_number"], "REG123")
    def test_nothing_is_ever_official(self):
        r = tlm.build([self.E("prepared"), self.E("submitted"), self.E("under_review"), self.E("approved")])
        self.assertTrue(all(s["official_confirmation"] is False and s["source"] == "self-reported" for s in r["steps"])); self.assertEqual(r["decision_as_reported"], "approved"); self.assertIn("not an official", r["disclaimer"])
    def test_skipped_steps_still_show_the_stage_reached(self):
        r = tlm.build([self.E("rejected")]); self.assertEqual(r["current"], "decision"); self.assertEqual(r["decision_as_reported"], "rejected"); self.assertTrue(all(s["reached"] for s in r["steps"]))
    def test_unknown_status_ignored(self): self.assertIsNone(tlm.build([self.E("weird")])["current"])


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures"))
class VerifiedFixtureJourney(unittest.TestCase):
    """The verified-scheme path at engine level with FICTIONAL fixture schemes (the browser version needs the real backend)."""
    def setUp(self):
        import make_verified_fixture as mv; self.d = tempfile.mkdtemp(); mv.make(self.d, self.T); self.old = (e.SCHEME_DIR, e.ALLOW_UNVERIFIED); e.SCHEME_DIR = self.d; e.ALLOW_UNVERIFIED = False
    def tearDown(self): e.SCHEME_DIR, e.ALLOW_UNVERIFIED = self.old; shutil.rmtree(self.d)
    T = dt.date.today()
    def test_only_verified_unexpired_schemes_are_active(self):
        self.assertEqual({s["scheme_id"] for s in e.load_schemes(self.T)}, {"TEST_HOUSEHOLD", "TEST_MEMBER"})          # draft and expired stay hidden
    def test_fixture_is_valid_and_fully_evidenced(self):
        for s in e.load_all(): self.assertEqual(e.validate_scheme(s), [], s["scheme_id"])
        for s in e.load_schemes(self.T): self.assertEqual(e.approval_blockers(s, self.T), [], s["scheme_id"])
    def test_explanation_cites_the_evidence_page_and_has_no_unverified_flag(self):
        hh = next(s for s in e.load_schemes(self.T) if s["scheme_id"] == "TEST_HOUSEHOLD"); r = e.evaluate(hh, {"state": "Tamil Nadu", "land_owned_acres": 2, "has_bank_account": True}, self.T)
        self.assertEqual(r["status"], "green"); self.assertEqual(r["rule_status"], "verified"); self.assertTrue(all(t["evidence"] and t["evidence"][0]["page"] == 12 for t in r["trace"] if t["rule_id"].startswith("T-")))
    def test_scheme_expiring_between_profile_and_discovery(self):
        tomorrow = self.T + dt.timedelta(days=1); s = json.load(open(os.path.join(self.d, "test_household.json"))); s["expires"] = self.T.isoformat(); json.dump(s, open(os.path.join(self.d, "test_household.json"), "w"))
        self.assertIn("TEST_HOUSEHOLD", {x["scheme_id"] for x in e.load_schemes(self.T)}); self.assertNotIn("TEST_HOUSEHOLD", {x["scheme_id"] for x in e.load_schemes(tomorrow)})     # valid on its last day, gone after
    def test_member_scheme_only_for_consenting_member(self):
        ms = [{"id": "a", "relationship": "mother", "age": 66, "occupation": "", "consent": False}, {"id": "b", "relationship": "father", "age": 67, "occupation": "", "consent": True}]
        out = e.evaluate_members(e.load_schemes(self.T), {"state": "Tamil Nadu"}, ms, self.T); self.assertEqual([m["member_id"] for m in out], ["b"]); self.assertEqual(out[0]["results"][0]["status"], "green")
    def test_trust_report_and_readiness_auto_checks_pass_for_the_fixture(self):
        self.assertTrue(e.trust_report([s for s in e.load_all() if s["scheme_id"] in ("TEST_HOUSEHOLD", "TEST_MEMBER")], self.T)["trustworthy"])
        ids = {c["id"]: c["status"] for c in rdy.board(self.T)["checks"]}; self.assertEqual({k: ids[k] for k in ("scheme_verification", "scheme_evidence", "two_person_approval", "expired_excluded")}, {k: "passed" for k in ("scheme_verification", "scheme_evidence", "two_person_approval", "expired_excluded")})

if __name__ == "__main__": unittest.main()
