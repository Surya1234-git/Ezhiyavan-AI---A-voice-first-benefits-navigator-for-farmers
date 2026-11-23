"""Browser end-to-end test of the frontend in real Chromium with a MOCKED API (page.route). It proves the UI flows work and render;
it does NOT test the real backend. Usage (after building a bundle, see README):  python e2e/farmer_journey.py <dir-with-bundle.js-bundle.css-and-public-files>
Needs: pip install playwright && playwright install chromium"""
import json, sys, os, threading, http.server, socketserver, functools, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend")); from app import timeline as TL; from app.questions import question as Q_TEXT      # the REAL timeline logic backs the mocked endpoint
from playwright.sync_api import sync_playwright, expect

DIST = sys.argv[1]
html = open(os.path.join(os.path.dirname(__file__), "..", "index.html"), encoding="utf-8").read()
html = re.sub(r'<script type="module" src="/src/main.tsx"></script>', '<link rel="stylesheet" href="/bundle.css"><script type="module" src="/bundle.js"></script>', html)
open(os.path.join(DIST, "index.html"), "w", encoding="utf-8").write(html)
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=DIST)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Q, directory=DIST)); PORT = srv.server_address[1]; threading.Thread(target=srv.serve_forever, daemon=True).start()   # ephemeral port: no clashes

S = {"in": False, "profile": {}, "docs": [], "family": [], "calls": [], "fail_discover_once": True, "apps": [], "events": [], "offline": False}
QS = [("land_owned_acres", "உங்களிடம் எவ்வளவு ஏக்கர் விவசாய நிலம் சொந்தமாக உள்ளது?"), ("has_bank_account", "உங்களுக்கு வங்கிக் கணக்கு உள்ளதா?"), ("government_employee", Q_TEXT("government_employee", "ta"))]
RES = {"scheme_id": "PM_KISAN", "name": "PM-KISAN Samman Nidhi", "version": "demo-2026.11", "rule_status": "demo_unverified", "source": "https://pmkisan.gov.in/", "last_verified": None, "stale_review": False,
       "benefit": "Income support", "benefit_detail": None, "deadline": None, "documents": ["Land record"], "required_doc_types": ["land_record"], "application_steps": ["Open pmkisan.gov.in"], "manual_checks": ["Check eKYC"],
       "status": "amber", "trace": [{"rule_id": "PMK-1", "field": "land_owned_acres", "result": "pass", "text": "Must own cultivable land", "reported": {"land_owned_acres": 2.0}, "evidence": []},
                 {"rule_id": "PMK-3", "field": "income_tax_payer", "result": "unknown", "text": "Income tax payers are excluded", "reported": {}, "evidence": []}]}

def api(route):
    r = route.request; p = r.url.split("/api", 1)[1]; m = r.method; body = r.post_data_json if r.post_data and "json" in (r.headers.get("content-type") or "") else None
    S["calls"].append((m, p, body)); ok = lambda j=None, st=200: route.fulfill(status=st, content_type="application/json", body=json.dumps(j if j is not None else {"ok": True}))
    if p == "/me/session": return ok(st=200 if S["in"] else 401)
    if p == "/auth/request-otp": return ok({"sent": True, "dev_code": "123456"})
    if p == "/auth/verify-otp": S["in"] = True; return ok()
    if S.get("hold") == p and m == "GET": S["held"] = route; S["hold"] = None; return              # park this request so the test can look at the loading state
    if p.startswith("/me/answers/") and m == "DELETE": S["profile"].pop(p.rsplit("/", 1)[1], None); S["undone"] = p.rsplit("/", 1)[1]; return ok()
    if p == "/auth/logout": S["in"] = False; return ok()
    if p == "/me" and m == "DELETE": S["deleted"] = True; S["in"] = False; return ok()
    if p.startswith("/me/next-question"):
        n = len(S["profile"]); return ok({"field": QS[n][0], "kind": "number" if QS[n][0] == "land_owned_acres" else "bool", "question": QS[n][1], "answered": n, "remaining": len(QS) - n} if n < len(QS) else {"done": True, "answered": n, "remaining": 0})
    if p == "/me/extract":
        if body["text"] == "தெரியாது": return ok({"field": body["field"], "value": None, "confidence": "none", "method": "rules", "note": "unknown", "flags": ["unknown"]})
        return ok({"field": body["field"], "value": 2.0 if body["field"] == "land_owned_acres" else True, "confidence": "high", "method": "rules", "note": None, "flags": []})
    if p == "/me/confirm": S["profile"][body["field"]] = body["value"]; return ok({"profile": S["profile"]})
    if p == "/me/discover" and S["fail_discover_once"] and len(S["profile"]) >= len(QS): S["fail_discover_once"] = False; return ok({"detail": "boom"}, 500)
    if p == "/me/discover": return ok({"profile": S["profile"], "results": [RES], "members": [], "estimate": {"annual_inr_if_all_approved": 0, "counted": [], "uncounted_without_verified_amount": 1, "note": "n"}, "disclaimer": "Potential eligibility only.",
        "summary": {"potential": 1, "green": 0, "amber": 1, "red": 0, "do_first": {"scheme_id": "PM_KISAN", "name": "PM-KISAN Samman Nidhi", "step": "Open pmkisan.gov.in", "documents": ["Land record"]},
                    "per_scheme": {"PM_KISAN": {"status": "amber", "to_confirm": ["Income tax payers are excluded"], "blocked_by": [], "near_miss": False}}}})
    if p == "/me/report-rule": S.setdefault("reports", []).append(body); return ok({"ok": True, "id": "r1"})
    if p == "/admin/impact": return ok({"farmers_total": 12, "farmers_screened": 9, "farmers_with_potential_scheme": 7, "active_last_30_days": 10, "small_sample": False, "potential_matches_by_scheme": {"PM-KISAN Samman Nidhi": 7},
                                       "most_common_missing_documents": [["land_record", 4]], "annual_inr_if_all_approved_verified_amounts_only": 0, "note": "Aggregates only."})
    if p == "/admin/reports" and m == "GET": return ok([{"id": "r1", "scheme_id": "PM_KISAN", "rule_id": "PMK-3", "text": "Income tax rule looks wrong", "status": "open", "at": "2026-11-21T09:00:00"}])
    if p == "/admin/reports/r1/close": S["closed"] = True; return ok()
    if p == "/me/reminders": return ok([{"kind": "missing_document", "scheme_id": "PM_KISAN", "doc_type": "land_record"}])
    if p == "/me/family": 
        if m == "POST": S["family"].append({"id": "m1", "relationship": body["relationship"], "age": body["age"], "occupation": body["occupation"], "consent": body["consent"]}); return ok()
        return ok(S["family"])
    if S["offline"]: return route.abort()
    if p in ("/me/consents", "/me/family/issues", "/me/documents/issues"): return ok([])
    if p == "/me/applications":
        if m == "GET": return ok(S["apps"])
        S["apps"].append({"id": "a1", "scheme_id": body["scheme_id"], "status": "prepared", "reference_number": "", "source": "self-reported"}); S["events"].append({"status": "prepared", "reference_number": "", "at": "2026-11-20T09:00:00"}); return ok({"id": "a1"})
    if p == "/me/applications/a1" and m == "PATCH":
        S["apps"][0].update(status=body["status"], reference_number=body["reference_number"]); S["events"].append({"status": body["status"], "reference_number": body["reference_number"], "at": "2026-11-21T09:00:00"}); return ok()
    if p == "/me/applications/a1/timeline": return ok(TL.build(S["events"]))
    if p == "/admin/login": return ok({"token": "t"})
    if p == "/admin/schemes" or p == "/admin/audit": return ok([])
    if p == "/admin/trust": return ok({"trustworthy": False, "summary": "NOT trustworthy: X", "shown_to_farmers": 1, "schemes": []})
    if p == "/admin/readiness" and m == "GET": return ok({"passed": 1, "total": 16, "release_ready": False, "checks": [
        {"id": "scheme_verification", "title": "All schemes shown to farmers are verified", "kind": "auto", "status": "failed", "tested_on": "2026-11-21", "reviewer": "(computed)", "evidence": "computed", "outstanding": ["PM_KISAN is demo_unverified"]},
        {"id": "tamil_ocr", "title": "Tamil OCR evaluated", "kind": "report", "status": "not_started", "tested_on": None, "reviewer": None, "evidence": None, "outstanding": []}]})
    if p == "/admin/readiness/tamil_ocr": return ok({"detail": "name the responsible reviewer"}, 400)
    if p.startswith("/me/documents") and "/confirm" in p: S["docs"][0]["confirmed"] = body["fields"]; return ok(S["docs"][0])
    if p.startswith("/me/documents"):
        if m == "POST":
            S["docs"] = [{"id": "d1", "doc_type": "land_record", "extracted": {"survey_no": "45/2A", "area_acres": 2.0}, "confirmed": {}, "verified": False, "quality_warnings": []}]
            return ok({"id": "d1", "duplicate": False, "ocr_available": True, "type_mismatch": False, "analysis": {}, "quality_warnings": []})
        return ok(S["docs"])
    if p.startswith("/me/claim-pack/"):
        return ok({"scheme": {k: RES[k] for k in ("scheme_id", "name", "version", "source", "last_verified", "rule_status", "benefit", "deadline")}, "status": "green", "trace": RES["trace"], "facts_confirmed_by_you": {},
                   "document_checklist": [{"doc_type": "land_record", "uploaded": True, "details_confirmed": True}], "other_documents": ["Bank passbook"], "steps": ["Open pmkisan.gov.in"], "manual_checks": ["Check eKYC"], "assurance": {"rules_matched": True, "documents_supplied": ["land_record"], "documents_checked_by_a_person": [], "officially_confirmed": False, "officially_confirmed_note": "Only the government can confirm."}, "tracking": [], "qr_svg": None, "generated_at": "2026-11-19T00:00:00Z", "disclaimer": "Preparation aid only."})
    return ok({}, 404)

errors = []
with sync_playwright() as pw:
    b = pw.chromium.launch(); ctx = b.new_context(viewport={"width": 390, "height": 844}, locale="ta-IN"); page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e))); page.on("dialog", lambda d: (S.setdefault("dialogs", []).append(d.message), d.accept())); ctx.route("**/api/**", api)
    base = f"http://127.0.0.1:{PORT}/"
    page.goto(base); expect(page.get_by_text("உங்கள் உரிமைகள், உங்கள் கைகளில்")).to_be_visible()                       # welcome (Tamil default)
    expect(page.get_by_role("group", name="Language / மொழி / भाषा").get_by_role("button")).to_have_count(3); expect(page.get_by_role("button", name="தமிழ்")).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_text("பேசுங்கள்")).to_be_visible(); expect(page.get_by_text("உறுதிசெய்யுங்கள்")).to_be_visible(); expect(page.get_by_text("விதிகள் முடிவு செய்யும்")).to_be_visible()   # speak -> confirm -> rules decide
    import re as _re
    def no_emoji_or_markup(where):
        txt = page.evaluate("document.body.innerText"); assert "<Icon" not in txt and "n=\"" not in txt, (where, "raw markup in page text")
        bad = _re.findall("[\U0001F000-\U0001FAFF\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF]", txt); assert not bad, (where, "emoji still rendered", bad)
    no_emoji_or_markup("welcome"); page.screenshot(path="/tmp/e2e/welcome_mobile.png", full_page=True)
    otp = page.get_by_role("button", name="OTP அனுப்பு"); expect(otp).to_be_disabled()                                           # needs consent + 10 digits
    page.get_by_role("checkbox").check(); page.get_by_placeholder("10 இலக்க மொபைல் எண்").fill("9876543210"); expect(otp).to_be_enabled(); otp.click()
    page.get_by_role("button", name="அனுப்பு").click()                                                                  # verify
    expect(page.get_by_text("உங்களிடம் எவ்வளவு ஏக்கர் விவசாய நிலம்")).to_be_visible()                                   # first question
    expect(page.locator("nav.tabbar button.tab")).to_have_count(5); expect(page.locator("nav.tabbar button.tab").first).to_have_attribute("aria-current", "page")   # four tabs plus More
    expect(page.get_by_text("கேள்வி 1 / சுமார் 3")).to_be_visible(); expect(page.get_by_role("button", name=re.compile("முந்தைய கேள்வி"))).to_have_count(0)   # progress; nothing to go back to yet
    page.evaluate("""window.SpeechRecognition = class { constructor() { window.__sr = this; } start() {} stop() { this.onend && this.onend(); } }; true""")        # a fake speech recogniser
    page.locator("button.mic").click(); expect(page.locator("button.mic")).to_have_class(re.compile("listening")); expect(page.get_by_text("கேட்கிறேன்… பேசுங்கள்")).to_be_visible()
    page.evaluate("""(() => { const r = [{ transcript: "இரண்டு" }]; r.isFinal = false; window.__sr.onresult({ results: [r] }); })()""")
    expect(page.get_by_text("“இரண்டு”")).to_be_visible(); page.screenshot(path="/tmp/e2e/listening_mobile.png")                                          # live transcript while listening
    page.get_by_role("button", name="நிறுத்து").last.click(); expect(page.locator("button.mic")).not_to_have_class(re.compile("listening"))              # clear Stop button
    page.locator("button.mic").click(); page.evaluate("""(() => { const r = [{ transcript: "2 ஏக்கர்" }]; r.isFinal = true; window.__sr.onresult({ results: [r] }); window.__sr.onend(); })()""")
    expect(page.get_by_text("“2 ஏக்கர்”")).to_be_visible(); assert "land_owned_acres" not in S["profile"]                                              # heard, shown, not saved until confirmed
    page.get_by_role("button", name="பதிலை மாற்று").click()
    page.locator("input").last.fill("தெரியாது"); page.get_by_role("button", name="அனுப்பு").click()                      # "I don't know" is never saved as an answer
    expect(page.get_by_text("நீங்கள் 'தெரியாது' என்றீர்கள்")).to_be_visible(); expect(page.get_by_role("button", name="சரி")).to_be_disabled()
    page.get_by_role("button", name="பதிலை மாற்று").click(); assert page.locator("input").last.input_value() == "தெரியாது"        # original text comes back for editing
    page.locator("input").last.fill("இரண்டு ஏக்கர்"); page.get_by_role("button", name="அனுப்பு").click()
    expect(page.get_by_text("நீங்கள் சொன்னது")).to_be_visible(); expect(page.get_by_text("“இரண்டு ஏக்கர்”")).to_be_visible(); expect(page.get_by_text("அதிக உறுதி")).to_be_visible()
    assert "land_owned_acres" not in S["profile"]                                                                                  # nothing saved before the farmer confirms
    page.get_by_role("button", name="சரி").click()                                                                                 # farmer confirms
    expect(page.get_by_text("உங்களுக்கு வங்கிக் கணக்கு உள்ளதா?")).to_be_visible(); assert S["profile"]["land_owned_acres"] == 2.0
    expect(page.get_by_text("கேள்வி 2 / சுமார் 3")).to_be_visible()
    page.get_by_role("button", name=re.compile("முந்தைய கேள்வி")).click(); page.wait_for_timeout(300)                                                     # Back: takes the answer back and asks it again
    assert "land_owned_acres" not in S["profile"] and S.get("undone") == "land_owned_acres"; expect(page.get_by_text("உங்களிடம் எவ்வளவு ஏக்கர் விவசாய நிலம்")).to_be_visible(); expect(page.get_by_text("கேள்வி 1 / சுமார் 3")).to_be_visible()
    page.locator("input").last.fill("இரண்டு ஏக்கர்"); page.get_by_role("button", name="அனுப்பு").click(); page.get_by_role("button", name="சரி").click()
    expect(page.get_by_text("உங்களுக்கு வங்கிக் கணக்கு உள்ளதா?")).to_be_visible(); assert S["profile"]["land_owned_acres"] == 2.0
    page.evaluate("window.SpeechRecognition = undefined; window.webkitSpeechRecognition = undefined; true")            # a browser without speech recognition
    page.locator("button.mic").click(); expect(page.get_by_text("இந்த உலாவியில் குரல் வசதி இல்லை")).to_be_visible()     # calm inline message, no pop-up
    expect(page.get_by_role("group", name="ஒரு தொடுதலில் பதில் அளிக்கலாம்")).to_be_visible()                                       # yes/no/don't know buttons on yes/no questions
    page.locator("input").last.fill("ஆம்"); page.get_by_role("button", name="அனுப்பு").click(); page.get_by_role("button", name="சரி").click()
    expect(page.get_by_text(Q_TEXT("government_employee", "ta"))).to_be_visible(); page.get_by_role("button", name="தெரியாது").click()      # one tap: "I don't know"
    page.wait_for_timeout(300); assert "government_employee" in S["profile"] and S["profile"]["government_employee"] is None, "don't-know must be stored as unknown, never yes/no"
    expect(page.get_by_text("கேள்விகள் முடிந்தன!")).to_be_visible(); page.get_by_role("button", name="முடிவுகள்").last.click()
    expect(page.get_by_text("ஏதோ தவறு நடந்தது")).to_be_visible(); page.get_by_role("button", name="மீண்டும் முயல்க").click()           # error state with retry
    expect(page.get_by_text("PM-KISAN Samman Nidhi").first).to_be_visible(); expect(page.get_by_text("மேலும் தகவல்/சரிபார்ப்பு தேவை").first).to_be_visible()   # amber chip
    expect(page.get_by_text("வரைவு")).to_be_visible()                                                                                     # one small "Draft" chip on the card
    expect(page.get_by_role("img", name="பூர்த்தியாகிறது").first).to_be_visible(); expect(page.get_by_role("img", name="உறுதிப்படுத்த வேண்டும்").first).to_be_visible()   # tick-list: met / needs confirmation
    expect(page.get_by_text("ஒரு நிபந்தனை தெரியவில்லை")).to_be_hidden(); expect(page.get_by_text("மூலம் சரிபார்க்கப்படுகிறது").first).to_be_hidden()   # detail is collapsed by default
    assert page.get_by_text("அதிகாரப்பூர்வமாக சரிபார்க்கப்படவில்லை").count() == 1, "the draft warning must appear once (banner), not on every card"
    page.get_by_text("விவரங்களைப் பார்க்க").first.click(); expect(page.get_by_text("ஒரு நிபந்தனை தெரியவில்லை")).to_be_visible()      # amber + its meaning, after opening details
    expect(page.get_by_text("அதிகாரப்பூர்வமாக சரிபார்க்கப்படவில்லை").first).to_be_visible(); expect(page.get_by_text("demo-2026.11")).to_be_hidden()   # plain-language unverified notice, no jargon
    expect(page.get_by_text("நீங்கள் தெரிவித்தது").first).to_be_visible(); expect(page.get_by_text("மூலம் சரிபார்க்கப்படுகிறது").first).to_be_visible()   # explanation + evidence status
    expect(page.get_by_text("உறுதிப்படுத்த வேண்டும்").first).to_be_visible()                                              # unknown condition is "needs confirmation"
    expect(page.get_by_role("region", name="நீங்கள் 1 திட்டங்களுக்குத் தகுதி பெறலாம்")).to_be_visible(); # headline
    expect(page.get_by_text("முதலில் இதைச் செய்யுங்கள்: PM-KISAN Samman Nidhi")).to_be_visible(); expect(page.get_by_role("button", name=re.compile("படித்துக் காட்டு"))).to_be_visible()
    page.get_by_text("இந்த விதி தவறாகத் தெரிகிறதா?").first.click(); page.get_by_label("இந்த விதி தவறாகத் தெரிகிறதா?").fill("Income tax rule looks wrong")
    page.get_by_role("button", name="அனுப்பு").click(); expect(page.get_by_text("நன்றி. சரிபார்ப்புக் குழுவுக்கு அனுப்பப்பட்டது.")).to_be_visible()
    assert S["reports"][0]["scheme_id"] == "PM_KISAN" and S["reports"][0]["text"] == "Income tax rule looks wrong"
    page.evaluate("window.__opened = []; window.open = (...a) => { window.__opened.push(a); return null; }; true")                          # help-centre finder opens a map search
    hb = page.get_by_role("button", name="வரைபடத்தில் தேடு"); expect(hb).to_be_disabled(); page.get_by_placeholder("உங்கள் மாவட்டம் அல்லது அஞ்சல் குறியீடு").fill("Tiruvarur"); hb.click()
    opened = page.evaluate("window.__opened"); assert opened and opened[0][0].startswith("https://www.google.com/maps/search/?api=1&query=Common%20Service%20Centre%20Tiruvarur") and "noopener" in opened[0][2], opened
    expect(page.get_by_text("வரைபடத் தேடல் அதிகாரப்பூர்வ பட்டியல் அல்ல")).to_be_visible()
    no_emoji_or_markup("results"); page.screenshot(path="/tmp/e2e/results_mobile.png", full_page=True)
    AUDIT = """() => [...document.querySelectorAll('input,select,textarea,button,a[href],summary')].filter(e => e.offsetParent !== null && e.type !== 'hidden' && !(e.getAttribute('aria-label') || (e.labels && e.labels.length) || e.textContent.trim() || e.getAttribute('title'))).map(e => e.outerHTML.slice(0, 90))"""
    def audit(where): bad = page.evaluate(AUDIT); assert not bad, f"controls without an accessible name on {where}: {bad}"
    audit("results")
    for w in (320, 360, 390, 768, 1024, 1440):                                                                                     # responsive widths
        page.set_viewport_size({"width": w, "height": 900}); assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), f"horizontal overflow at {w}px"
    page.set_viewport_size({"width": 320, "height": 900}); page.evaluate("document.body.style.zoom = '2'")                       # 320px at 200% text/zoom
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth * 2 + 2"), "overflow at 320px with 200% zoom"; page.evaluate("document.body.style.zoom = '1'"); page.set_viewport_size({"width": 390, "height": 844})
    page.locator("h1").first.click(); page.keyboard.press("Tab")                                                                  # start keyboard navigation from the top of the page
    for _ in range(8):                                                                                                             # keyboard: focus always lands on a real control
        assert page.evaluate("['BUTTON','A','INPUT','SELECT','SUMMARY','TEXTAREA'].includes(document.activeElement.tagName)"), "Tab focus lost"; page.keyboard.press("Tab")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "horizontal overflow on mobile"
    page.get_by_role("button", name="விண்ணப்பத் தொகுப்பு").click(); expect(page.locator(".pack")).to_be_visible(); expect(page.get_by_text("அரசு உறுதிப்படுத்தியது").first).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "overflow in claim pack"; page.get_by_role("button", name="மூடு").click()
    page.get_by_role("button", name="மேலும்", exact=True).click(); expect(page.get_by_role("menu")).to_have_count(0); expect(page.locator("#more-panel").get_by_role("button")).to_have_count(2); expect(page.get_by_role("button", name="மேலும்", exact=True)).to_have_attribute("aria-expanded", "true"); page.locator("#more-panel").get_by_role("button", name=re.compile("குடும்பம்")).click(); page.get_by_placeholder("வயது").fill("66"); page.get_by_role("checkbox").first.check(); page.get_by_role("button", name="சேர்").first.click()
    expect(page.get_by_text("spouse · 66")).to_be_visible()
    fam = [c for c in S["calls"] if c[0] == "POST" and c[1] == "/me/family"][0][2]; assert fam["age"] == 66 and fam["consent"] is True and fam["has_disability"] is None   # unknown stays null
    audit("family"); S["hold"] = "/me/documents"; page.get_by_role("button", name=re.compile("ஆவணம்")).click()
    expect(page.locator(".skel").first).to_be_visible(); api(S.pop("held")); expect(page.get_by_text("இன்னும் ஆவணங்கள் எதுவும் பதிவேற்றப்படவில்லை.")).to_be_visible()      # documents: skeleton, then an empty state
    page.locator("input[type=file]").set_input_files({"name": "land.pdf", "mimeType": "application/pdf", "buffer": b"%PDF-1.4 test"})
    expect(page.locator("b", has_text="land_record").first).to_be_visible(); expect(page.get_by_text("ஆவணம் படிக்கப்பட்டது மட்டுமே – உண்மையானது என சரிபார்க்கப்படவில்லை")).to_be_visible()
    page.get_by_role("button", name="சரிபார்த்து சேமி").click(); page.wait_for_timeout(300)
    assert S["docs"][0]["confirmed"].get("area_acres") == 2.0, "confirm payload missing area"                                # extracted value saved only after the click
    audit("documents"); page.get_by_role("button", name="மேலும்", exact=True).click(); S["hold"] = "/me/discover"; page.locator("#more-panel").get_by_role("button", name=re.compile("பலன்கள்")).click()
    expect(page.locator(".skel").first).to_be_visible(); api(S.pop("held")); expect(page.get_by_text("land_record").first).to_be_visible(); expect(page.get_by_text("அதிகாரப்பூர்வமாக சரிபார்க்கப்பட்ட பணம்: 0")).to_be_visible()
    page.get_by_role("button", name=re.compile("விண்ணப்பம்")).first.click(); expect(page.get_by_text("இன்னும் எந்த விண்ணப்பமும் கண்காணிக்கப்படவில்லை")).to_be_visible()   # nothing tracked yet: an empty state, not a blank area
    page.get_by_role("button", name=re.compile("முடிவுகள்")).first.click(); page.get_by_role("button", name="விண்ணப்பத்தை கண்காணி").first.click()                                                              # Track is a visible secondary button -> Apps tab
    S["hold"] = "/me/applications"; page.get_by_role("button", name=re.compile("விண்ணப்பம்")).first.click()
    expect(page.locator(".skel").first).to_be_visible(); api(S.pop("held")); page.get_by_role("button", name="சமர்ப்பித்தேன்").click(); audit("applications")      # applications: skeleton, then the list
    page.get_by_text("வரலாறு").first.click(); expect(page.get_by_text("விண்ணப்பம் சமர்ப்பிக்கப்பட்டது")).to_be_visible(); expect(page.get_by_text("நீங்கள் தெரிவித்தது – அரசு உறுதிப்படுத்தவில்லை").first).to_be_visible()
    expect(page.get_by_text("Every step is reported by you")).to_be_visible()                                                           # timeline never claims official status
    page.get_by_role("button", name="என் தரவை நீக்கு").click(); expect(page.get_by_role("alertdialog")).to_be_visible(); expect(page.get_by_text("இதை மீட்க முடியாது")).to_be_visible()
    page.get_by_role("button", name="வேண்டாம்").click(); assert not S.get("deleted"), "cancel must not delete"; expect(page.get_by_role("alertdialog")).to_have_count(0)   # one tap can no longer wipe data
    page.get_by_role("button", name="வெளியேறு").click(); expect(page.get_by_text("உங்கள் உரிமைகள், உங்கள் கைகளில்")).to_be_visible()   # logout returns to welcome
    S["in"] = True; page.goto(base); page.reload(); page.get_by_role("button", name="என் தரவை நீக்கு").click()                                      # delete: the CONFIRM path
    expect(page.get_by_role("alertdialog")).to_be_visible(); page.get_by_role("button", name="ஆம், அனைத்தையும் நீக்கு").click()
    expect(page.get_by_text("உங்கள் உரிமைகள், உங்கள் கைகளில்")).to_be_visible(); assert S.get("deleted") and S["in"] is False, "confirmed delete must call DELETE /me and end the session"
    page.goto(base + "#/partner"); page.reload(); expect(page.get_by_text("Help centre login")).to_be_visible()
    page.goto(base + "#/admin"); page.reload(); expect(page.get_by_text("Scheme reviewer login")).to_be_visible(); audit("admin login")
    page.get_by_placeholder("User").fill("a"); page.get_by_placeholder("Password").fill("b"); page.get_by_role("button", name="Log in").click()
    expect(page.get_by_text("Production readiness: 1 of 16 checks passed")).to_be_visible(); expect(page.get_by_text("not release ready")).to_be_visible(); expect(page.get_by_text("PM_KISAN is demo_unverified")).to_be_visible()
    expect(page.get_by_text("Impact (anonymised totals)")).to_be_visible(); expect(page.get_by_text("Rule reports (1 open)")).to_be_visible()      # impact dashboard + rule reports
    no_emoji_or_markup("admin"); page.get_by_role("button", name="Mark reviewed").click(); page.wait_for_timeout(200); assert S.get("closed")
    assert page.get_by_role("button", name="Record result").count() == 1, "auto checks must not offer a manual 'Record result'"                 # only the report-driven check can be recorded
    page.get_by_role("button", name="Record result").click(); expect(page.get_by_label("Report JSON")).to_be_visible(); page.get_by_role("button", name="Save").click(); expect(page.get_by_text("name the responsible reviewer")).to_be_visible()
    ctx2 = b.new_context(viewport={"width": 390, "height": 844}, locale="ta-IN"); p2 = ctx2.new_page(); ctx2.route("**/api/**", api); p2.goto(base)
    p2.evaluate("navigator.serviceWorker.ready.then(() => true)"); p2.reload(); p2.wait_for_timeout(800)                                         # 2nd load is controlled by the SW and fills the shell cache
    S["offline"] = True; ctx2.set_offline(True); p2.reload(); expect(p2.get_by_text("உங்கள் உரிமைகள், உங்கள் கைகளில்")).to_be_visible()      # app shell loads with no network (NOT offline data/drafting)
    b.close()
assert not S.get("dialogs"), S.get("dialogs")     # no browser pop-ups anywhere in the journey
assert not errors, errors
print("E2E PASSED (mocked API). Screenshot: /tmp/e2e/results_mobile.png")
