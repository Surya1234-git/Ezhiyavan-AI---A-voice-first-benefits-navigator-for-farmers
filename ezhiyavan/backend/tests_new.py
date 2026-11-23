"""Tests for the pure-logic modules added in the hackathon build (no web framework needed):  python -m unittest tests_new.py"""
import os, unittest, tempfile, json
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only-0123456789")
os.environ["ALLOW_UNVERIFIED"] = "1"
from app import engine as eng, insights
from app.validation import validate_value
from app.netutil import client_ip

class Validation(unittest.TestCase):
    def test_bool_fields_only_accept_booleans(self):
        self.assertIs(validate_value("has_bank_account", True), True)
        for bad in ("yes", 1, 0, [], {}): self.assertRaises(ValueError, validate_value, "has_bank_account", bad)
    def test_unknown_is_always_allowed(self):
        for f in ("has_bank_account", "land_owned_acres", "state"): self.assertIsNone(validate_value(f, None))
    def test_land_range(self):
        self.assertEqual(validate_value("land_owned_acres", 2), 2.0)
        for bad in (-1, 10001, float("nan"), float("inf"), True, "2"): self.assertRaises(ValueError, validate_value, "land_owned_acres", bad)
    def test_text_limits(self):
        self.assertEqual(validate_value("state", "  Tamil Nadu "), "Tamil Nadu")
        for bad in ("", "   ", "x" * 81, 5): self.assertRaises(ValueError, validate_value, "state", bad)

class ClientIp(unittest.TestCase):
    def test_ignores_header_unless_proxy_trusted(self): self.assertEqual(client_ip("1.1.1.1", "9.9.9.9", False), "9.9.9.9")
    def test_forged_leftmost_entry_is_not_used(self):
        self.assertEqual(client_ip("6.6.6.6, 203.0.113.7", "10.0.0.1", True, 1), "203.0.113.7")      # attacker sent 6.6.6.6; the proxy appended the real address
    def test_two_hops(self): self.assertEqual(client_ip("6.6.6.6, 203.0.113.7, 10.1.1.1", "10.0.0.1", True, 2), "203.0.113.7")
    def test_falls_back_to_socket_peer(self):
        self.assertEqual(client_ip("", "10.0.0.1", True), "10.0.0.1"); self.assertEqual(client_ip("1.1.1.1", "10.0.0.1", True, 3), "10.0.0.1")

class Summary(unittest.TestCase):
    def setUp(self): self.schemes = eng.load_schemes()
    def run_profile(self, prof):
        res = [eng.evaluate(s, prof) for s in self.schemes if s.get("applies_to") != "member"]; return res, insights.summarize(res, self.schemes)
    def test_counts_add_up(self):
        res, sm = self.run_profile({"land_owned_acres": 2.0, "has_bank_account": True})
        self.assertEqual(sm["green"] + sm["amber"] + sm["red"], len(res)); self.assertEqual(sm["potential"], sm["green"] + sm["amber"])
        self.assertEqual(set(sm["per_scheme"]), {r["scheme_id"] for r in res})
    def test_near_miss_only_for_single_failed_requirement(self):
        res, sm = self.run_profile({"land_owned_acres": 2.0, "has_bank_account": False})
        kcc = sm["per_scheme"]["KCC"]; self.assertEqual(kcc["status"], "red"); self.assertTrue(kcc["near_miss"]); self.assertTrue(kcc["blocked_by"])
    def test_exclusion_is_never_a_near_miss(self):
        res, sm = self.run_profile({"land_owned_acres": 2.0, "has_bank_account": True, "government_employee": True})
        self.assertEqual(sm["per_scheme"]["PM_KISAN"]["status"], "red"); self.assertFalse(sm["per_scheme"]["PM_KISAN"]["near_miss"])
    def test_do_first_prefers_green_and_names_a_scheme(self):
        _, sm = self.run_profile({"land_owned_acres": 0, "has_bank_account": False}); self.assertIsNone(sm["do_first"]) if sm["potential"] == 0 else None
        res, sm = self.run_profile({"land_owned_acres": 2.0, "has_bank_account": True}); self.assertIsNotNone(sm["do_first"])
        if sm["green"]: self.assertEqual(res[[r["scheme_id"] for r in res].index(sm["do_first"]["scheme_id"])]["status"], "green")

class Impact(unittest.TestCase):
    def setUp(self): self.schemes = eng.load_schemes()
    def test_small_sample_flag_and_no_identifiers(self):
        out = insights.impact([{"profile": {"land_owned_acres": 2.0, "has_bank_account": True}, "doc_types": [], "active_days": 1}], self.schemes)
        self.assertTrue(out["small_sample"]); self.assertEqual(out["farmers_total"], 1); self.assertEqual(out["farmers_screened"], 1)
        self.assertNotIn("farmer_id", json.dumps(out))
    def test_counts_and_missing_docs(self):
        rows = [{"profile": {"land_owned_acres": 2.0, "has_bank_account": True}, "doc_types": ["land_record"], "active_days": 3} for _ in range(5)]
        rows += [{"profile": {}, "doc_types": [], "active_days": 400}]
        out = insights.impact(rows, self.schemes)
        self.assertFalse(out["small_sample"]); self.assertEqual(out["farmers_total"], 6); self.assertEqual(out["farmers_screened"], 5)
        self.assertEqual(out["active_last_30_days"], 5); self.assertGreaterEqual(out["farmers_with_potential_scheme"], 1)
        self.assertIn("bank_passbook", dict(out["most_common_missing_documents"]))
    def test_unverified_amounts_are_never_counted(self):
        out = insights.impact([{"profile": {"land_owned_acres": 2.0, "has_bank_account": True}, "doc_types": [], "active_days": 1}] * 5, self.schemes)
        self.assertEqual(out["annual_inr_if_all_approved_verified_amounts_only"], 0)

class RuleCorrections(unittest.TestCase):
    """KCC also covers tenant farmers / oral lessees / sharecroppers and allied-activity farmers (RBI KCC Directions 2026, paras 11 and 14);
    PM-JAY covers everyone aged 70+ regardless of income (Cabinet decision 11 Sep 2024, launched 29 Oct 2024)."""
    def setUp(self): self.s = {x["scheme_id"]: x for x in eng.load_schemes()}
    def st(self, sid, prof): return eng.evaluate(self.s[sid], prof)["status"]
    def test_kcc_tenant_without_land_is_not_excluded(self):
        self.assertNotEqual(self.st("KCC", {"land_owned_acres": 0, "cultivates_leased_land": True, "has_bank_account": True}), "red")
    def test_kcc_allied_activity_only_is_not_excluded(self):
        self.assertNotEqual(self.st("KCC", {"land_owned_acres": 0, "cultivates_leased_land": False, "does_allied_activity": True, "has_bank_account": True}), "red")
    def test_kcc_no_land_no_lease_no_allied_is_red(self):
        self.assertEqual(self.st("KCC", {"land_owned_acres": 0, "cultivates_leased_land": False, "does_allied_activity": False, "has_bank_account": True}), "red")
    def test_kcc_unknown_lease_status_is_not_red(self):
        self.assertNotEqual(self.st("KCC", {"land_owned_acres": 0, "has_bank_account": True}), "red")
    def test_kcc_owner_needs_no_lease_answers(self): self.assertNotEqual(self.st("KCC", {"land_owned_acres": 2.0, "has_bank_account": True}), "red")
    def test_pmjay_age_70_plus_is_eligible_without_being_on_the_list(self):
        self.assertNotEqual(self.st("PMJAY", {"in_pmjay_list": False, "has_member_aged_70_plus": True}), "red")
    def test_pmjay_dont_know_is_not_a_no(self): self.assertNotEqual(self.st("PMJAY", {"in_pmjay_list": None}), "red")
    def test_redundant_questions_are_skipped_for_owners(self):
        sch = eng.load_schemes(); red = eng.redundant_fields(sch, {"land_owned_acres": 2.0})
        self.assertIn("cultivates_leased_land", red); self.assertIn("does_allied_activity", red); self.assertNotIn("has_bank_account", red)
    def test_questions_are_still_asked_when_land_is_zero_or_unknown(self):
        sch = eng.load_schemes()
        for prof in ({"land_owned_acres": 0}, {"land_owned_acres": None}, {}):
            red = eng.redundant_fields(sch, prof); self.assertNotIn("cultivates_leased_land", red); self.assertNotIn("does_allied_activity", red)
    def test_every_field_has_a_question_in_all_languages_and_a_kind(self):
        from app.questions import question
        from app.extract import kind
        for f in eng.needed_fields(eng.load_schemes()):
            if f == "state": continue
            for lang in ("en", "ta", "hi"): self.assertTrue(question(f, lang) and len(question(f, lang)) > 8, (f, lang))
            self.assertIn(kind(f), ("bool", "number"), f)
    def test_new_yes_no_fields_parse_yes_no_and_dont_know(self):
        from app.extract import extract
        for f in ("cultivates_leased_land", "does_allied_activity", "has_member_aged_70_plus"):
            self.assertIs(extract(f, "yes"), True); self.assertIs(extract(f, "no"), False); self.assertIsNone(extract(f, "I don't know"))

class TraceType(unittest.TestCase):
    def test_every_trace_entry_names_its_rule_type(self):
        for s in eng.load_schemes():
            for item in eng.evaluate(s, {})["trace"]:
                if item["rule_id"] in ("GEO", "DATES"): self.assertIsNone(item["type"])          # built-in state/date checks are not scheme rules
                else: self.assertIn(item["type"], ("require", "exclude", "flag"), (s["scheme_id"], item))
    def test_exclusion_rules_are_typed_exclude(self):
        pk = next(s for s in eng.load_schemes() if s["scheme_id"] == "PM_KISAN")
        types = {i["rule_id"]: i["type"] for i in eng.evaluate(pk, {})["trace"]}
        self.assertEqual(types["PMK-1"], "require"); self.assertEqual(types["PMK-3"], "exclude"); self.assertEqual(types["PMK-3b"], "flag")

class StaticChecker(unittest.TestCase):
    """scripts/check_names.py must catch the bug class that once stopped the API from starting."""
    def run_check(self, code):
        import importlib.util, pathlib
        spec = importlib.util.spec_from_file_location("check_names", pathlib.Path(__file__).resolve().parent.parent / "scripts" / "check_names.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f: f.write(code)
        try: return mod.check(f.name)
        finally: os.unlink(f.name)
    def test_dependency_used_before_definition_is_reported(self):
        out = self.run_check("def Depends(x): return x\n@route\ndef metrics(who=Depends(admin)): pass\ndef admin(): pass\n")
        self.assertTrue(any("before it is defined" in x and "'admin'" in x for x in out), out)
    def test_decorator_using_later_name_is_reported(self):
        self.assertTrue(any("before it is defined" in x for x in self.run_check("@later\ndef f(): pass\ndef later(fn): return fn\n")))
    def test_undefined_name_is_reported(self): self.assertTrue(any("undefined name 'nope'" in x for x in self.run_check("def f():\n    return nope\n")))
    def test_correct_order_and_late_runtime_use_are_fine(self):
        self.assertEqual(self.run_check("def admin(): pass\ndef m(who=admin): pass\ndef a():\n    return b()\ndef b(): return 1\n"), [])
    def test_real_backend_has_no_findings(self):
        import glob, importlib.util, pathlib
        root = pathlib.Path(__file__).resolve().parent
        spec = importlib.util.spec_from_file_location("check_names", root.parent / "scripts" / "check_names.py"); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        self.assertEqual([p for f in glob.glob(str(root / "app" / "*.py")) for p in mod.check(f)], [])

if __name__ == "__main__": unittest.main()
