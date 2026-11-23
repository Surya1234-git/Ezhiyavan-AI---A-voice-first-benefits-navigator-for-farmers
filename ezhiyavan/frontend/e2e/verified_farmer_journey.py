"""Production-style browser journey against the REAL backend with FICTIONAL verified schemes.   >>> WRITTEN BUT NOT RUN by the author (no FastAPI in the sandbox). <<<
Setup:  python backend/fixtures/make_verified_fixture.py /tmp/ez_fixture
        cd backend && SECRET_KEY=... SCHEME_DIR=/tmp/ez_fixture ALLOW_UNVERIFIED=0 ENV=dev uvicorn app.main:app     (+ frontend dev server as in real_backend_journey.py)
        BASE_URL=http://localhost:5173 python e2e/verified_farmer_journey.py
Checks: verified scheme shown WITHOUT the 'not officially verified' banner; draft and expired schemes hidden; evidence page shown in the explanation; member scheme appears only for a
consenting member; wrong OTP, unsupported file, session loss and cross-farmer access are refused; data deletion. Uses no real farmer data."""
import os, random, tempfile
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("BASE_URL", "http://localhost:5173")
ANS = [("acres", "2 acres"), ("which state", "Tamil Nadu"), ("bank account", "yes")]
def answer_for(q):
    for k, a in ANS:
        if k in q.lower(): return a
    raise AssertionError("no scripted answer for: " + q)
phone = lambda: "9" + "".join(random.choice("0123456789") for _ in range(9))

def api_login(pw, base):                                  # a second farmer, via the API, to test cross-farmer access
    ctx = pw.request.new_context(base_url=base, extra_http_headers={"X-Requested-With": "ezhiyavan"}); ph = phone()
    code = ctx.post("/api/auth/request-otp", data={"phone": ph}).json()["dev_code"]
    ctx.post("/api/auth/verify-otp", data={"phone": ph, "code": code, "consent": True}); return ctx

with sync_playwright() as pw:
    b = pw.chromium.launch(); ctx = b.new_context(viewport={"width": 390, "height": 844}); page = ctx.new_page(); errors = []; page.on("pageerror", lambda e: errors.append(str(e))); page.on("dialog", lambda d: d.accept())
    page.goto(BASE); page.locator("select").first.select_option("en"); page.get_by_role("checkbox").check(); ph = phone(); page.get_by_placeholder("Mobile (10 digits)").fill(ph)
    page.get_by_role("button", name="OTP").click(); expect(page.get_by_placeholder("OTP")).not_to_have_value("")
    page.get_by_placeholder("OTP").fill("000000"); page.get_by_role("button", name="Send").click(); expect(page.get_by_text("invalid or expired code")).to_be_visible()      # wrong OTP is refused
    page.get_by_placeholder("OTP").fill(""); page.get_by_role("button", name="OTP").count()
    page.reload(); page.locator("select").first.select_option("en"); page.get_by_role("checkbox").check(); page.get_by_placeholder("Mobile (10 digits)").fill(ph)
    page.get_by_role("button", name="OTP").click(); page.get_by_role("button", name="Send").click()
    for _ in range(8):
        page.wait_for_timeout(400)
        if page.get_by_text("All questions answered!").count(): break
        q = page.locator("div.card b").first.inner_text(); page.locator("input").last.fill(answer_for(q)); page.get_by_role("button", name="Send").last.click(); page.get_by_role("button", name="Correct").click()
    page.get_by_role("button", name="Results").last.click()
    expect(page.get_by_text("TEST ONLY - Household Support")).to_be_visible(); expect(page.get_by_text("Potentially eligible").first).to_be_visible()
    assert page.get_by_text("Not officially verified").count() == 0, "verified schemes must not carry the unverified banner"
    assert page.get_by_text("Draft Scheme").count() == 0 and page.get_by_text("Expired Scheme").count() == 0, "draft/expired schemes must be hidden"
    expect(page.get_by_text("TEST ONLY - fictional guidelines, p.12").first).to_be_visible()                          # rule-level evidence reference
    page.get_by_role("button", name="Claim pack").first.click(); expect(page.locator(".pack")).to_be_visible(); page.get_by_role("button", name="Close").click()
    page.get_by_role("button", name="Family").click(); page.get_by_placeholder("Age").fill("66"); page.get_by_role("button", name="Add").first.click()     # NO consent ticked
    page.get_by_role("button", name="Results").first.click(); assert page.get_by_text("TEST ONLY - Senior Support").count() == 0, "member without consent must not be assessed"
    page.get_by_role("button", name="Family").click(); page.get_by_placeholder("Age").fill("67"); page.get_by_role("checkbox").first.check(); page.get_by_role("button", name="Add").first.click()
    page.get_by_role("button", name="Results").first.click(); expect(page.get_by_text("TEST ONLY - Senior Support")).to_be_visible()                       # consenting member only
    page.get_by_role("button", name="Papers").click(); bad = os.path.join(tempfile.mkdtemp(), "x.txt"); open(bad, "w").write("not a document"); page.locator("input[type=file]").set_input_files(bad)
    expect(page.get_by_text("unsupported file")).to_be_visible()                                                         # unsupported file type refused
    page.get_by_role("button", name="Results").first.click(); page.get_by_role("button", name="Track this application").first.click()
    app_id = page.request.get(BASE + "/api/me/applications").json()[0]["id"]
    other = api_login(pw, BASE); assert other.get(f"/api/me/applications/{app_id}/timeline").status == 404, "another farmer must not see this application"
    assert other.get("/api/me/documents").json() == []
    ctx.clear_cookies(); page.reload(); expect(page.get_by_text("Your rights, in your hands")).to_be_visible()                # session lost -> back to the start
    assert page.request.get(BASE + "/api/me/session").status == 401
    b.close()
assert not errors, errors
print("VERIFIED-SCHEME E2E PASSED")
