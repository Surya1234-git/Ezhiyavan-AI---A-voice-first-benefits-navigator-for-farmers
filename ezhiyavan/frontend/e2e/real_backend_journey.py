"""Browser end-to-end test against the REAL backend (no mocks).   >>> WRITTEN BUT NOT RUN by the author: the sandbox had no FastAPI/SQLAlchemy. Expect to adjust selectors. <<<
Journey: registration -> profile questions -> family -> document upload -> eligibility/scheme discovery -> claim pack -> application tracking -> data deletion.

Setup (demo mode: dev OTP is shown on screen, unverified demo rules are active):
  cd backend && pip install -r requirements.txt -r requirements-ocr.txt
  export SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))")
  ENV=dev ALLOW_UNVERIFIED=1 uvicorn app.main:app &                 # :8000
  cd ../frontend && npm install && npm run dev &                      # :5173, proxies /api
  pip install playwright && playwright install chromium
  BASE_URL=http://localhost:5173 python e2e/real_backend_journey.py
Needs Tesseract installed for the document step to read text (otherwise the test still passes: the app asks the farmer to type values)."""
import os, random, re, tempfile
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("BASE_URL", "http://localhost:5173")
ANSWERS = [("acres", "2 acres"), ("which state", "Tamil Nadu"), ("income tax", "no"), ("government employee", "no"), ("minister", "no"), ("doctor", "no"), ("bank account", "yes"),
           ("company, trust", "no"), ("pm-jay", "no"), ("insure", "yes")]

def answer_for(q):
    q = q.lower()
    for k, a in ANSWERS:
        if k in q: return a
    raise AssertionError("no scripted answer for question: " + q)

def make_pdf(path):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (1400, 420), "white"); d = ImageDraw.Draw(img); f = ImageFont.load_default(size=36)
    for i, ln in enumerate(["PATTA NO: 1234", "SURVEY NO. 45/2A", "EXTENT 2.0 ACRES"]): d.text((40, 40 + 70 * i), ln, fill="black", font=f)
    img.save(path)                                                   # image-only PDF: exercises the scanned-PDF OCR path

dialogs = []
with sync_playwright() as pw:
    b = pw.chromium.launch(); page = b.new_context(viewport={"width": 390, "height": 844}).new_page()
    page.on("dialog", lambda d: (dialogs.append(d.message), d.accept())); errors = []; page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE); page.locator("select").first.select_option("en")
    page.get_by_role("checkbox").check(); page.get_by_placeholder("Mobile (10 digits)").fill("9" + "".join(random.choice("0123456789") for _ in range(9)))
    page.get_by_role("button", name="OTP").click(); expect(page.get_by_placeholder("OTP")).not_to_have_value("")            # dev code is prefilled only when the backend runs with ENV=dev
    page.get_by_role("button", name="Send").click()
    for _ in range(15):                                              # profile questions, answered through the real extraction + confirm flow
        page.wait_for_timeout(400)
        if page.get_by_text("All questions answered!").count(): break
        q = page.locator("div.card b").first.inner_text(); page.locator("input").last.fill(answer_for(q))
        page.get_by_role("button", name="Send").last.click(); page.get_by_role("button", name="Correct").click()
    expect(page.get_by_text("All questions answered!")).to_be_visible(); page.get_by_role("button", name="Results").last.click()
    expect(page.get_by_text("PM-KISAN Samman Nidhi")).to_be_visible(); expect(page.get_by_text("Not officially verified").first).to_be_visible()   # demo drafts must be labelled
    page.get_by_role("button", name="Claim pack").first.click(); expect(page.locator(".pack")).to_be_visible(); page.get_by_role("button", name="Close").click()
    page.get_by_role("button", name="Family").click(); page.get_by_placeholder("Age").fill("66"); page.get_by_role("checkbox").first.check(); page.get_by_role("button", name="Add").first.click()
    expect(page.get_by_text("spouse · 66")).to_be_visible(); page.get_by_role("button", name="Results").first.click()
    expect(page.get_by_text("Social pension for senior citizens (Tamil Nadu)")).to_be_visible()                           # member-level scheme for the consenting member
    pdf = os.path.join(tempfile.mkdtemp(), "land.pdf"); make_pdf(pdf)
    page.get_by_role("button", name="Papers").click(); page.locator("input[type=file]").set_input_files(pdf)
    expect(page.get_by_text("Read only – authenticity NOT verified")).to_be_visible(); expect(page.locator("b", has_text="land_record").first).to_be_visible()
    page.get_by_role("button", name="Check and save").click(); page.wait_for_timeout(500)
    page.get_by_role("button", name="Results").first.click(); page.get_by_role("button", name="Track this application").first.click()
    page.get_by_role("button", name="Apply").click(); expect(page.get_by_text("PM_KISAN").first).to_be_visible()
    page.get_by_role("button", name="Submitted").first.click(); page.get_by_text("History").first.click()
    expect(page.get_by_text("Application submitted")).to_be_visible(); expect(page.get_by_text("Every step is reported by you")).to_be_visible()      # timeline is self-reported, never official
    apps = page.request.get(BASE + "/api/me/applications").json(); assert apps and apps[0]["status"] == "submitted" and apps[0]["source"] == "self-reported"     # stored server-side, labelled self-reported
    page.get_by_role("button", name="Delete my data").click(); page.get_by_role("button", name="Yes, delete everything").click(); expect(page.get_by_text("Your rights, in your hands")).to_be_visible()                 # erasure returns to the start
    assert page.request.get(BASE + "/api/me/session").status == 401
    b.close()
assert not errors, errors
print("REAL-BACKEND E2E PASSED")
