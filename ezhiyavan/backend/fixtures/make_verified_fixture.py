"""Writes FICTIONAL, clearly-labelled test schemes (never real government data) used to test the verified-scheme path end to end:
  python backend/fixtures/make_verified_fixture.py /tmp/ez_fixture
  SCHEME_DIR=/tmp/ez_fixture ALLOW_UNVERIFIED=0 ENV=dev uvicorn app.main:app      # then run frontend/e2e/verified_farmer_journey.py
Contents: a verified household scheme with page-level evidence, a verified member (age 60+) scheme, a DRAFT scheme (must stay hidden) and an EXPIRED scheme (must stay hidden)."""
import datetime as dt, json, os, sys

def evidence(rule_ids, page):
    return [{"title": "TEST ONLY - fictional guidelines", "url": "https://example.gov.in/test-guidelines.pdf", "document_date": "2026-01-01", "page": page, "rule_ids": rule_ids}]

def make(out, today=None):
    today = today or dt.date.today(); os.makedirs(out, exist_ok=True)
    base = dict(version="1.0", source="https://example.gov.in/", documents=["Land record", "Bank passbook"], conditions_complete=True, submitted_by="reviewer_a", approvals=["reviewer_b", "reviewer_c"], approved_by=["reviewer_b", "reviewer_c"],
                last_verified=(today - dt.timedelta(days=10)).isoformat(), status="verified", required_doc_types=["land_record", "bank_passbook"], application_steps=["Open the (fictional) portal", "Keep documents ready"], applicable_states=["Tamil Nadu"])
    S = {
        "test_household": {**base, "scheme_id": "TEST_HOUSEHOLD", "name": "TEST ONLY - Household Support", "benefit": "Fictional benefit for testing",
            "rules": [{"id": "T-1", "type": "require", "field": "land_owned_acres", "op": "gt", "value": 0, "text": "Must own land"}, {"id": "T-2", "type": "require", "field": "has_bank_account", "op": "eq", "value": True, "text": "Must have a bank account"}],
            "source_evidence": evidence(["T-1", "T-2"], 12)},
        "test_member": {**base, "scheme_id": "TEST_MEMBER", "name": "TEST ONLY - Senior Support", "applies_to": "member", "benefit": "Fictional benefit for seniors", "required_doc_types": [],
            "rules": [{"id": "M-1", "type": "require", "field": "age", "op": "gte", "value": 60, "text": "Must be 60 or older"}], "source_evidence": evidence(["M-1"], 3)},
        "test_draft": {**base, "scheme_id": "TEST_DRAFT", "name": "TEST ONLY - Draft Scheme (must be hidden)", "status": "demo_unverified", "last_verified": None, "approved_by": [], "approvals": [], "benefit": "x",
            "rules": [{"id": "D-1", "type": "require", "field": "land_owned_acres", "op": "gt", "value": 0, "text": "t"}], "source_evidence": []},
        "test_expired": {**base, "scheme_id": "TEST_EXPIRED", "name": "TEST ONLY - Expired Scheme (must be hidden)", "benefit": "x", "expires": (today - dt.timedelta(days=1)).isoformat(),
            "rules": [{"id": "E-1", "type": "require", "field": "land_owned_acres", "op": "gt", "value": 0, "text": "t"}], "source_evidence": evidence(["E-1"], 1)},
    }
    for k, v in S.items(): json.dump(v, open(os.path.join(out, k + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return sorted(S)

if __name__ == "__main__": print(make(sys.argv[1] if len(sys.argv) > 1 else "/tmp/ez_fixture"))
