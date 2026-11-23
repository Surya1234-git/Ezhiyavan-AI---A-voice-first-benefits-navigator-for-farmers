"""Document intelligence: OCR (optional backends) -> classify -> extract fields -> flag missing. Output is a PROPOSAL; the farmer confirms.
Reading a document is NOT authenticity verification."""
import os, re, datetime as dt

MAX_PAGES = 5

def preprocess(img):
    """Orientation (Tesseract OSD), small-angle deskew (OpenCV, optional), contrast, denoise, upscale. Returns the original image on any failure."""
    try:
        import pytesseract
        from PIL import Image, ImageOps, ImageFilter
        g = ImageOps.autocontrast(ImageOps.grayscale(img))
        try:                                                    # 90/180/270 rotation
            osd = pytesseract.image_to_osd(g)
            rot = int(re.search(r"Rotate:\s+(\d+)", osd).group(1)); conf = float(re.search(r"Orientation confidence:\s+([\d.]+)", osd).group(1))
            if rot in (90, 180, 270) and conf >= 1.0: g = g.rotate(-rot, expand=True, fillcolor=255)
        except Exception: pass
        try:                                                    # skew of a few degrees
            import cv2, numpy as np
            a = np.array(g); ys, xs = np.where(a < 128)
            if len(xs) > 200:
                ang = cv2.minAreaRect(np.column_stack((xs, ys)).astype("float32"))[-1]
                ang = ang - 90 if ang > 45 else ang
                if 0.5 < abs(ang) <= 15:
                    h, w = a.shape; M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
                    g = Image.fromarray(cv2.warpAffine(a, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=255))
        except Exception: pass
        g = g.filter(ImageFilter.MedianFilter(3))
        if min(g.size) < 1000: g = g.resize((g.width * 2, g.height * 2), Image.LANCZOS)
        return g
    except Exception:
        return img
_AVAILABLE = None
def available_languages():
    """Tesseract language data actually installed. (Tesseract does NOT fail when a requested language such as 'tam' is missing - it silently
    runs with whatever loaded - so we must check ourselves, or reports would claim Tamil OCR ran when it did not.)"""
    global _AVAILABLE
    if _AVAILABLE is None:
        try:
            import pytesseract; _AVAILABLE = set(pytesseract.get_languages(config=""))
        except Exception: _AVAILABLE = set()
    return _AVAILABLE

def usable_lang(requested):
    comps = [c for c in requested.split("+") if c]; ok = [c for c in comps if c in available_languages()]
    return "+".join(ok) if ok else ("eng" if "eng" in available_languages() else requested)

def _ocr_once(img, lang):
    """-> (text, mean_word_confidence, score). score = sum of confidences of reasonably confident words (rewards both quality and amount of text)."""
    import pytesseract
    from pytesseract import Output
    for lg in dict.fromkeys([usable_lang(lang), "eng"]):     # only language data that is really installed; the caller records what was used
        try:
            data = pytesseract.image_to_data(img, lang=lg, output_type=Output.DICT)
            confs = [float(c) for c, w in zip(data["conf"], data["text"]) if str(c) not in ("-1", "") and w.strip()]
            return pytesseract.image_to_string(img, lang=lg), (sum(confs) / len(confs) if confs else 0.0), sum(c for c in confs if c > 50), lg
        except pytesseract.TesseractError: continue
    return "", 0.0, 0.0, None

def _ocr_image(img, lang):
    """Returns (text, mean_word_confidence, language_data_actually_used). Preprocesses; if the result looks poor (a sideways/upside-down page often does) tries the other
    three orientations and keeps the best-scoring reading. OSD alone is not trusted: it is unreliable on short text."""
    img = preprocess(img); best = _ocr_once(img, lang)
    if best[1] < 70 or len(best[0].strip()) < 30:
        for deg in (90, 180, 270):
            r = _ocr_once(img.rotate(deg, expand=True, fillcolor=255 if img.mode == "L" else "white"), lang)
            if r[2] > best[2]: best = r
    return best[0], best[1], best[3]

def read_document(path, lang=None):
    """-> {text, method, mean_conf, low_res, pages}. Methods: pdf_text | pdf_scanned_ocr | image_ocr. text=None if nothing could be read.
    OCR_LANGS env (default 'eng'; use 'tam+eng' once Tesseract Tamil data is installed)."""
    import re as _re
    lang = lang or os.getenv("OCR_LANGS", "eng")
    if not _re.fullmatch(r"[a-z_]{3,12}(\+[a-z_]{3,12})*", lang): lang = "eng"
    info = {"text": None, "method": None, "mean_conf": None, "low_res": False, "pages": 0, "lang_requested": lang, "lang_used": None}
    try:
        if os.path.splitext(path)[1].lower() == ".pdf":
            from pypdf import PdfReader
            r = PdfReader(path); info["pages"] = len(r.pages)
            t = "\n".join((pg.extract_text() or "") for pg in r.pages)
            if t.strip(): info.update(text=t, method="pdf_text"); return info
            import pypdfium2 as pdfium                       # scanned PDF: render pages, then OCR
            pdf = pdfium.PdfDocument(path); texts, confs = [], []
            for i in range(min(len(pdf), MAX_PAGES)):
                tx, cf, lg = _ocr_image(pdf[i].render(scale=300 / 72).to_pil(), lang); texts.append(tx); confs.append(cf); info["lang_used"] = lg
            info.update(text="\n".join(texts), method="pdf_scanned_ocr", mean_conf=sum(confs) / max(len(confs), 1),
                        pages_detail=[{"page": i + 1, "mean_conf": round(c, 1), "chars": len(t.strip())} for i, (t, c) in enumerate(zip(texts, confs))])
        else:
            from PIL import Image
            img = Image.open(path); info["pages"] = 1; info["low_res"] = min(img.size) < 700
            tx, cf, lg = _ocr_image(img, lang); info.update(text=tx, method="image_ocr", mean_conf=cf, lang_used=lg)
        if not (info["text"] or "").strip(): info["text"] = None
    except Exception:
        info["text"] = None
    return info

def ocr_text(path, lang=None): return read_document(path, lang)["text"]

def quality_warnings(info):
    w = []
    if info.get("low_res"): w.append("low_resolution")
    mc = info.get("mean_conf")
    if info.get("method") in ("image_ocr", "pdf_scanned_ocr") and mc is not None and mc < 60: w.append("low_ocr_confidence")
    if info.get("text") is not None and len(info["text"].strip()) < 20: w.append("very_little_text")
    return w

KEYWORDS = {
    "land_record": ["patta", "chitta", "பட்டா", "சிட்டா", "survey", "சர்வே", "adangal", "அடங்கல்", "khasra", "खसरा", "khatauni", "खतौनी"],
    "income_certificate": ["income certificate", "annual income", "வருமானச் சான்று", "வருமான சான்றிதழ்", "ஆண்டு வருமானம்", "आय प्रमाण"],
    "community_certificate": ["community certificate", "சாதிச் சான்று", "சமூகச் சான்று", "जाति प्रमाण"],
    "bank_passbook": ["passbook", "ifsc", "ifs code", "branch", "கணக்கு எண்", "खाता"],
}
REQUIRED = {"land_record": ["survey_no", "area_acres"], "income_certificate": ["income_inr", "issue_date"], "bank_passbook": ["ifsc"], "community_certificate": []}
ALLOWED_FIELDS = {"survey_no", "area_acres", "patta_no", "issue_date", "valid_until", "income_inr", "ifsc"}

AADHAAR_RE = re.compile(r"(?<!\d)([2-9]\d{3})[\s-]?(\d{4})[\s-]?(\d{4})(?!\d)")        # 12 digits, first digit 2-9 (over-masking is deliberate)
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
ACCT_RE = re.compile(r"((?:a/c|acct|account|खाता|கணக்கு)[^\d]{0,25})(\d[\d\s-]{7,20}\d)", re.I)
def redact(text):
    """Masks Aadhaar, PAN and bank account numbers. Returns (masked_text, sorted list of detected kinds). Extraction runs on the masked text only."""
    found = set()
    def a(m): found.add("aadhaar"); return "XXXX-XXXX-" + m.group(3)
    def acct(m): found.add("bank_account"); return m.group(1) + "[MASKED]"
    text = ACCT_RE.sub(acct, text)
    text = AADHAAR_RE.sub(a, text)
    if PAN_RE.search(text): found.add("pan"); text = PAN_RE.sub("[PAN-MASKED]", text)
    return text, sorted(found)

def classify(text):
    """Needs >= 2 DISTINCT keywords of one type (one stray word such as 'patta' is not enough). Returns (type, confidence, candidates)."""
    t = text.lower(); scores = {k: sum(w.lower() in t for w in ws) for k, ws in KEYWORDS.items()}
    cands = [k for k, v in sorted(scores.items(), key=lambda kv: -kv[1]) if v > 0]
    if not cands or scores[cands[0]] < 2: return "unknown", "none", cands
    if len(cands) > 1 and scores[cands[1]] == scores[cands[0]]: return "unknown", "none", cands          # tie: ask the farmer
    return cands[0], ("high" if scores[cands[0]] >= 3 else "medium"), cands

def _date(s):
    m = re.match(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})$", s.strip())
    if not m: return None
    d, mo, y = int(m[1]), int(m[2]), int(m[3]); y += 2000 if y < 100 else 0
    try: return dt.date(y, mo, d).isoformat()
    except ValueError: return None

def _area_acres(text):
    m = re.search(r"(\d+(?:\.\d+)?)\s*(acres?|ac\b|ஏக்கர்|एकड़|hectares?|ha\b|ஹெக்டேர்|हेक्टेयर|cents?|சென்ட்)", text, re.I)
    if not m: return None
    v, u = float(m[1]), m[2].lower()
    if u.startswith(("hect", "ha", "ஹெக்", "हेक्")): v *= 2.47105
    elif u.startswith(("cent", "சென்")): v /= 100
    return round(v, 3)

def extract_fields(doc_type, text):
    f = {}
    if doc_type == "land_record":
        m = re.search(r"(?:survey|s\.?\s*no\.?|சர்வே|सर्वे)[^\d]{0,20}(\d+(?:\s*/\s*\d+[A-Za-z]?)?)", text, re.I)
        if m: f["survey_no"] = m[1].replace(" ", "")
        m = re.search(r"(?:patta|பட்டா)[^\d]{0,20}(\d+)", text, re.I)
        if m: f["patta_no"] = m[1]
        a = _area_acres(text)
        if a is not None: f["area_acres"] = a
    elif doc_type == "income_certificate":
        m = re.search(r"(?:annual income|ஆண்டு வருமானம்)[^\d]{0,25}([\d,]+)", text, re.I)
        if m:
            try: f["income_inr"] = int(m[1].replace(",", ""))
            except ValueError: pass
    elif doc_type == "bank_passbook":
        m = re.search(r"\b([A-Z]{4}0[A-Z0-9]{6})\b", text)    # IFSC only; account numbers are deliberately NOT extracted
        if m: f["ifsc"] = m[1]
    m = re.search(r"(?:date of issue|issued on|dated|வழங்கப்பட்ட நாள்)[^\d]{0,10}(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})", text, re.I)
    if m and _date(m[1]): f["issue_date"] = _date(m[1])
    m = re.search(r"(?:valid (?:up ?to|till|until)|expiry|expires on)[^\d]{0,10}(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})", text, re.I)
    if m and _date(m[1]): f["valid_until"] = _date(m[1])
    return f

def _has_bad_date(text):
    return any(_date(m) is None for m in re.findall(r"(?:date of issue|issued on|dated|valid (?:up ?to|till|until)|expiry|expires on)[^\d]{0,10}(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})", text, re.I))

def analyze(text, mean_conf=None, today=None):
    """Proposal only. Sensitive numbers are masked first. field_confidence is 'low' when OCR confidence is poor or the value looks odd/ambiguous."""
    today = today or dt.date.today()
    text, sensitive = redact(text)
    dtp, conf, cands = classify(text); fields = extract_fields(dtp, text) if dtp != "unknown" else {}
    warnings = []; fc = {k: ("low" if (mean_conf is not None and mean_conf < 75) else "high") for k in fields}
    if dtp == "land_record":
        areas = re.findall(r"\d+(?:\.\d+)?\s*(?:acres?|ac\b|ஏக்கர்|एकड़|hectares?|ha\b|ஹெக்டேர்|हेक्टेयर|cents?|சென்ட்)", text, re.I)
        if len(areas) > 1: fc["area_acres"] = "low"; warnings.append("several_area_values")
        if "area_acres" in fields and not (0 < fields["area_acres"] <= 100): fc["area_acres"] = "low"; warnings.append("unusual_area")
        if "survey_no" not in fields: warnings.append("missing_survey_no")
    if _has_bad_date(text): warnings.append("invalid_date_text")
    if fields.get("valid_until") and dt.date.fromisoformat(fields["valid_until"]) < today: warnings.append("expired")
    if mean_conf is not None and mean_conf < 75: warnings.append("low_ocr_confidence")
    return {"detected_type": dtp, "confidence": conf, "candidates": cands, "fields": fields, "field_confidence": fc, "warnings": warnings,
            "sensitive_detected": sensitive, "missing": [k for k in REQUIRED.get(dtp, []) if k not in fields],
            "note": "Read from the document text only. Authenticity is NOT verified."}

def doc_issues(docs, profile):
    """Inconsistencies between the farmer's CONFIRMED document values and each other / the profile."""
    out = []; areas = [(d["id"], d["confirmed"]["area_acres"]) for d in docs if d["doc_type"] == "land_record" and "area_acres" in (d.get("confirmed") or {})]
    for i in range(len(areas)):
        for j in range(i + 1, len(areas)):
            a, b = areas[i][1], areas[j][1]
            if abs(a - b) > 0.05 * max(a, b, 0.01): out.append({"kind": "area_mismatch_between_documents", "values": [a, b]})
    pa = profile.get("land_owned_acres")
    for _, a in areas:
        if pa is not None and abs(a - pa) > 0.05 * max(a, pa, 0.01): out.append({"kind": "area_differs_from_your_answer", "document": a, "answer": pa})
    return out

def assurance(result_status, doc_types_supplied, reviewed_types):
    """The four different things that are often confused. The last one is ALWAYS false: we have no government integration."""
    return {"rules_matched": result_status == "green", "documents_supplied": sorted(set(doc_types_supplied)), "documents_checked_by_a_person": sorted(set(reviewed_types)),
            "officially_confirmed": False, "officially_confirmed_note": "Only the responsible government authority can confirm eligibility."}

def build_reminders(results, docs, today=None, window=30):
    """results: household eval results; docs: [{doc_type, confirmed:{...}}]. Pure function."""
    today = today or dt.date.today(); out = []; have = {d["doc_type"] for d in docs}
    for r in results:
        if r["status"] == "red": continue
        for t in r.get("required_doc_types", []):
            if t not in have: out.append({"kind": "missing_document", "scheme_id": r["scheme_id"], "doc_type": t})
        if r.get("deadline"):
            left = (dt.date.fromisoformat(r["deadline"]) - today).days
            if left <= window: out.append({"kind": "deadline", "scheme_id": r["scheme_id"], "date": r["deadline"], "days_left": left})
    for d in docs:
        vu = (d.get("confirmed") or {}).get("valid_until")
        if vu:
            left = (dt.date.fromisoformat(vu) - today).days
            if left <= window: out.append({"kind": "document_expiring", "doc_type": d["doc_type"], "date": vu, "days_left": left})
    return out
