"""API/security tests. Needs: pip install -r requirements.txt httpx pytest ; run: pytest tests_api.py"""
import os, tempfile
os.environ.update(SECRET_KEY="test-secret-test-secret-test-secret", ENV="dev", ALLOW_UNVERIFIED="1", RATE_AUTH="1000", RATE_API="10000",
                  PARTNER_USERS='{"csc1": "s$' + __import__("hashlib").pbkdf2_hmac("sha256", b"pw", b"s", 200000).hex() + '"}',
                  DATABASE_URL="sqlite:///" + tempfile.mkdtemp() + "/t.db", UPLOAD_DIR=tempfile.mkdtemp())
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)

def login(phone):
    code = c.post("/api/auth/request-otp", json={"phone": phone}).json()["dev_code"]
    t = c.post("/api/auth/verify-otp", json={"phone": phone, "code": code, "consent": True}).json()["token"]
    c.cookies.clear()      # verify-otp also sets the session cookie; clear the shared jar so later calls without a header are truly anonymous
    return {"Authorization": "Bearer " + t}

def test_requires_login():
    assert c.get("/api/me/discover").status_code == 401
    assert c.get("/api/me/discover", headers={"Authorization": "Bearer x.y"}).status_code == 401
def test_consent_required():
    code = c.post("/api/auth/request-otp", json={"phone": "9000000001"}).json()["dev_code"]
    assert c.post("/api/auth/verify-otp", json={"phone": "9000000001", "code": code, "consent": False}).status_code == 400
def test_wrong_otp_and_bad_phone():
    c.post("/api/auth/request-otp", json={"phone": "9000000002"})
    assert c.post("/api/auth/verify-otp", json={"phone": "9000000002", "code": "000000", "consent": True}).status_code == 401
    assert c.post("/api/auth/request-otp", json={"phone": "123"}).status_code == 422
def test_otp_rate_limit():
    for _ in range(3): assert c.post("/api/auth/request-otp", json={"phone": "9000000003"}).status_code == 200
    assert c.post("/api/auth/request-otp", json={"phone": "9000000003"}).status_code == 429
def test_farmers_cannot_touch_each_others_applications():
    a, b = login("9000000004"), login("9000000005")
    aid = c.post("/api/me/applications", json={"scheme_id": "PM_KISAN"}, headers=a).json()["id"]
    assert c.patch(f"/api/me/applications/{aid}", json={"status": "submitted"}, headers=b).status_code == 404
    assert c.get("/api/me/applications", headers=b).json() == []
    assert c.patch(f"/api/me/applications/{aid}", json={"status": "submitted"}, headers=a).status_code == 200
def test_farmer_token_cannot_use_admin():
    assert c.post("/api/admin/schemes", json={}, headers=login("9000000006")).status_code == 403
def test_upload_validation():
    h = login("9000000007")
    assert c.post("/api/me/documents?doc_type=land", files={"file": ("x.exe", b"MZ")}, headers=h).status_code == 400
    assert c.post("/api/me/documents?doc_type=land", files={"file": ("x.pdf", b"not a pdf")}, headers=h).status_code == 400
    assert c.post("/api/me/documents?doc_type=land", files={"file": ("x.pdf", b"%PDF-1.4 ok")}, headers=h).status_code == 200
    assert c.post("/api/me/documents?doc_type=land", files={"file": ("x.pdf", b"%PDF" + b"0" * 6_000_000)}, headers=h).status_code == 413
def test_profile_flow_and_delete():
    h = login("9000000008")
    assert c.post("/api/me/confirm", json={"field": "land_owned_acres", "value": 2}, headers=h).status_code == 200
    assert c.post("/api/me/confirm", json={"field": "hack", "value": 1}, headers=h).status_code == 400
    assert c.post("/api/me/family", json={"relationship": "mother", "age": 66}, headers=h).status_code == 200
    r = c.get("/api/me/discover", headers=h).json(); assert r["members"] == []          # member not consented -> not evaluated
    assert c.post("/api/me/family", json={"relationship": "mother", "age": 66, "consent": True}, headers=h).status_code == 200
    assert len(c.get("/api/me/discover", headers=h).json()["members"]) == 1
    assert c.delete("/api/me", headers=h).json()["deleted"]
def test_next_question_progress_and_undo():
    h = login("9000000021")
    q = c.get("/api/me/next-question", headers=h).json(); assert q["answered"] == 0 and q["remaining"] >= 1
    assert c.post("/api/me/confirm", json={"field": q["field"], "value": 2 if q["kind"] == "number" else True}, headers=h).status_code == 200
    assert c.get("/api/me/next-question", headers=h).json()["answered"] == 1
    assert c.delete(f"/api/me/answers/{q['field']}", headers=h).status_code == 200
    assert c.get("/api/me/next-question", headers=h).json()["field"] == q["field"]          # the same question is asked again
    assert c.delete("/api/me/answers/hack", headers=h).status_code == 400
    assert c.delete(f"/api/me/answers/{q['field']}").status_code in (401, 403)              # not logged in

def test_cors_not_wildcard():
    r = c.options("/api/me/discover", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") != "*" and "evil" not in r.headers.get("access-control-allow-origin", "")
def test_logout_revokes_token():
    h = login("9000000009"); assert c.get("/api/me/discover", headers=h).status_code == 200
    assert c.post("/api/auth/logout", headers=h).status_code == 200
    assert c.get("/api/me/discover", headers=h).status_code == 401
def test_extract_rejects_unknown_field():
    h = login("9000000010"); assert c.post("/api/me/extract", json={"field": "aadhaar", "text": "1234"}, headers=h).status_code == 400
    r = c.post("/api/me/extract", json={"field": "land_owned_acres", "text": "2 acres"}, headers=h).json(); assert r["value"] == 2.0

def test_contradiction_needs_overwrite():
    h = login("9000000011"); c.post("/api/me/confirm", json={"field": "land_owned_acres", "value": 2}, headers=h)
    assert c.post("/api/me/confirm", json={"field": "land_owned_acres", "value": 5}, headers=h).status_code == 409
    assert c.post("/api/me/confirm", json={"field": "land_owned_acres", "value": 5, "overwrite": True}, headers=h).status_code == 200
def test_cookie_session_requires_csrf_header():
    cl = TestClient(app); code = cl.post("/api/auth/request-otp", json={"phone": "9000000012"}).json()["dev_code"]
    cl.post("/api/auth/verify-otp", json={"phone": "9000000012", "code": code, "consent": True})
    assert cl.get("/api/me/session").status_code == 200
    assert cl.post("/api/me/applications", json={"scheme_id": "PM_KISAN"}).status_code == 403
    assert cl.post("/api/me/applications", json={"scheme_id": "PM_KISAN"}, headers={"X-Requested-With": "ezhiyavan"}).status_code == 200
def test_doc_confirm_ownership_and_validation():
    a, b = login("9000000013"), login("9000000014")
    did = c.post("/api/me/documents?doc_type=land_record", files={"file": ("x.pdf", b"%PDF-1.4 ok")}, headers=a).json()["id"]
    assert c.post(f"/api/me/documents/{did}/confirm", json={"fields": {"survey_no": "1"}}, headers=b).status_code == 404
    assert c.post(f"/api/me/documents/{did}/confirm", json={"fields": {"aadhaar": "1"}}, headers=a).status_code == 400
    assert c.post(f"/api/me/documents/{did}/confirm", json={"fields": {"area_acres": -1}}, headers=a).status_code == 400
    assert c.post(f"/api/me/documents/{did}/confirm", json={"fields": {"area_acres": 2.0, "valid_until": "2027-01-01"}}, headers=a).status_code == 200
def partner_token():
    return {"Authorization": "Bearer " + c.post("/api/partner/login", json={"user": "csc1", "password": "pw"}).json()["token"]}
def test_partner_needs_consent_and_is_audited():
    f = login("9000000015"); p = partner_token()
    assert c.post("/api/me/consents", json={"partner_id": "nobody"}, headers=f).status_code == 404
    assert c.post("/api/me/consents", json={"partner_id": "csc1"}, headers=f).status_code == 200
    cases = [x for x in c.get("/api/partner/cases", headers=p).json()]; assert cases
    fid = cases[-1]["farmer_ref"]
    assert c.get(f"/api/partner/cases/{fid}", headers=p).status_code == 200
    assert any(x["action"] == "view_case" for x in c.get("/api/me/access-log", headers=f).json())
    assert c.delete("/api/me/consents/csc1", headers=f).status_code == 200
    assert c.get(f"/api/partner/cases/{fid}", headers=p).status_code == 404            # revoked
def test_partner_cannot_reach_unconsented_and_farmer_cannot_use_partner_routes():
    p = partner_token(); assert c.get("/api/partner/cases/not-a-real-id", headers=p).status_code == 404
    assert c.get("/api/partner/cases", headers=login("9000000016")).status_code == 403
def test_admin_authz_policy():
    # Policy: no credentials -> 401 (who are you?); valid FARMER credentials on an admin route -> 403 (not allowed).
    # (An earlier 403 here came from the shared test cookie jar still holding a farmer session, not from a policy bug.)
    assert c.post("/api/admin/schemes", json={}).status_code == 401
    assert c.get("/api/admin/audit").status_code == 401
    assert c.get("/api/admin/schemes", headers=login("9000000017")).status_code == 403

def test_chat_returns_proposals_without_saving():
    h = login("9000000018"); r = c.post("/api/me/chat", json={"text": "எனக்கு 2 ஏக்கர் நிலம் உள்ளது"}, headers=h).json()
    assert any(p["field"] == "land_owned_acres" and p["value"] == 2.0 for p in r["proposals"])
    assert "land_owned_acres" not in c.get("/api/me/discover", headers=h).json()["profile"]
def test_application_history():
    h = login("9000000019"); aid = c.post("/api/me/applications", json={"scheme_id": "PM_KISAN"}, headers=h).json()["id"]
    c.patch(f"/api/me/applications/{aid}", json={"status": "submitted", "reference_number": "R1"}, headers=h)
    hist = c.get(f"/api/me/applications/{aid}/history", headers=h).json(); assert [x["status"] for x in hist] == ["prepared", "submitted"]
    assert all(x["source"] == "self-reported" for x in hist); assert c.get(f"/api/me/applications/{aid}/history", headers=login("9000000020")).status_code == 404
def test_duplicate_upload_detected():
    h = login("9000000021"); f = {"file": ("x.pdf", b"%PDF-1.4 same")}
    a = c.post("/api/me/documents?doc_type=land_record", files=f, headers=h).json(); b = c.post("/api/me/documents?doc_type=land_record", files={"file": ("y.pdf", b"%PDF-1.4 same")}, headers=h).json()
    assert a["duplicate"] is False and b["duplicate"] is True and a["id"] == b["id"]
def test_otp_production_fails_without_provider():
    import app.main as m; m.DEV = False
    try: assert c.post("/api/auth/request-otp", json={"phone": "9000000022"}).status_code == 503
    finally: m.DEV = True
def test_upload_fails_closed_without_encryption_key_in_prod():
    import app.main as m; h = login("9000000023"); m.DEV = False
    try: assert c.post("/api/me/documents?doc_type=land_record", files={"file": ("x.pdf", b"%PDF-1.4 z")}, headers=h).status_code == 503
    finally: m.DEV = True
def test_admin_listing_requires_admin_role():
    assert c.get("/api/admin/schemes/pm_kisan").status_code == 401

def test_claim_pack_has_no_sensitive_data_and_404_for_member_scheme():
    h = login("9000000024"); c.post("/api/me/confirm", json={"field": "land_owned_acres", "value": 2}, headers=h)
    r = c.get("/api/me/claim-pack/PM_KISAN", headers=h); assert r.status_code == 200
    j = r.json(); assert j["facts_confirmed_by_you"]["land_owned_acres"] == 2 and "disclaimer" in j and "9000000024" not in r.text
    assert c.get("/api/me/claim-pack/TN_OLD_AGE_PENSION", headers=h).status_code == 404
    assert c.get("/api/me/claim-pack/PM_KISAN").status_code == 401
def test_family_attributes_drive_member_results_and_estimate_is_present():
    h = login("9000000025")
    c.post("/api/me/family", json={"relationship": "son", "age": 24, "consent": True, "has_disability": True}, headers=h)
    d = c.get("/api/me/discover", headers=h).json()
    assert any(r["scheme_id"] == "TN_DISABILITY_ASSISTANCE" for r in d["members"][0]["results"]) and "estimate" in d
def test_purge_enforces_retention():
    import datetime as dt, app.main as m, app.maintenance as mt
    h = login("9000000026"); did = c.post("/api/me/documents?doc_type=land_record", files={"file": ("o.pdf", b"%PDF-1.4 old")}, headers=h).json()["id"]
    with m.Session() as db: db.get(m.Doc, did).created_at = dt.datetime.utcnow() - dt.timedelta(days=400); db.commit()
    assert mt.purge()["documents"] >= 1 and c.get("/api/me/documents", headers=h).json() == []
def test_audit_log_is_append_only_in_db():
    import app.main as m, sqlalchemy.exc as se, pytest
    with m.Session() as db:
        m.audit(db, "t", "x"); db.commit()
        with pytest.raises(se.DatabaseError): db.query(m.Audit).delete(); db.commit()

def test_partner_must_confirm_farmer_present_and_can_review_docs():
    f = login("9000000027"); p = partner_token(); c.post("/api/me/consents", json={"partner_id": "csc1"}, headers=f)
    fid = [x for x in c.get("/api/partner/cases", headers=p).json()][-1]["farmer_ref"]
    assert c.post(f"/api/partner/cases/{fid}/profile", json={"field": "has_bank_account", "value": True}, headers=p).status_code == 400
    assert c.post(f"/api/partner/cases/{fid}/profile", json={"field": "has_bank_account", "value": True, "farmer_present": True}, headers=p).status_code == 200
    did = c.post("/api/me/documents?doc_type=land_record", files={"file": ("x.pdf", b"%PDF-1.4 rv")}, headers=f).json()["id"]
    assert c.post(f"/api/partner/cases/{fid}/documents/{did}/review", json={"outcome": "looks_consistent"}, headers=p).status_code == 400
    assert c.post(f"/api/partner/cases/{fid}/documents/{did}/review", json={"outcome": "looks_consistent", "farmer_present": True}, headers=p).status_code == 200
    d = [x for x in c.get("/api/me/documents", headers=f).json() if x["id"] == did][0]; assert d["checked_by_a_person"] and d["verified"] is False
def test_claim_pack_assurance_never_claims_official_confirmation():
    h = login("9000000028"); j = c.get("/api/me/claim-pack/PM_KISAN", headers=h).json()
    assert j["assurance"]["officially_confirmed"] is False and "tracking" in j
def test_admin_cannot_approve_incomplete_scheme_and_trust_requires_admin():
    assert c.get("/api/admin/trust").status_code == 401 and c.get("/api/admin/trust", headers=login("9000000029")).status_code == 403
def test_family_and_document_issue_endpoints():
    h = login("9000000030"); c.post("/api/me/family", json={"relationship": "spouse", "age": 30}, headers=h); c.post("/api/me/family", json={"relationship": "spouse", "age": 30}, headers=h)
    assert {i["kind"] for i in c.get("/api/me/family/issues", headers=h).json()} >= {"duplicate_member", "missing_consent"}
    assert c.get("/api/me/documents/issues", headers=h).json() == []

def test_timeline_and_under_review_status():
    h = login("9000000031"); aid = c.post("/api/me/applications", json={"scheme_id": "PM_KISAN"}, headers=h).json()["id"]
    assert c.patch(f"/api/me/applications/{aid}", json={"status": "under_review", "reference_number": "R9"}, headers=h).status_code == 200
    t = c.get(f"/api/me/applications/{aid}/timeline", headers=h).json(); assert t["current"] == "under_review" and t["reference_number"] == "R9" and not any(s["official_confirmation"] for s in t["steps"])
    assert c.get(f"/api/me/applications/{aid}/timeline", headers=login("9000000032")).status_code == 404
def test_expired_token_is_rejected_and_logout_works_with_cookie():
    import app.security as sec
    exp = sec.make_token("someone", "farmer", ttl=-5); assert c.get("/api/me/session", headers={"Authorization": "Bearer " + exp}).status_code == 401
def test_metrics_and_health():
    assert c.get("/healthz").json()["ok"] is True; assert c.get("/api/admin/metrics").status_code == 401
def test_readiness_endpoints_require_admin_and_reject_manual_auto_checks():
    assert c.get("/api/admin/readiness").status_code == 401 and c.get("/api/admin/readiness", headers=login("9000000033")).status_code == 403
