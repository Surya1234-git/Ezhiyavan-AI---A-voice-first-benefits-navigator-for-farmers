import os, re, uuid, json, shutil, socket, struct, time, hashlib, tempfile, base64, urllib.parse, urllib.request, datetime as dt
from collections import defaultdict, deque
from fastapi import FastAPI, HTTPException, Depends, Header, Request, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, Integer, JSON, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from . import engine as eng, security as sec, docs as dcs, readiness as rdy, obs, ratelimit, timeline as tl, insights, netutil
from .validation import validate_value
from starlette.concurrency import run_in_threadpool
import logging
from .extract import extract_smart, extract_many, kind as field_kind
from .questions import question

DB = os.getenv("DATABASE_URL", "sqlite:///./ezhiyavan.db")
engine_db = create_engine(DB, connect_args={"check_same_thread": False} if DB.startswith("sqlite") else {})
Session = sessionmaker(bind=engine_db)
Base = declarative_base()
DEV = os.getenv("ENV", "prod") == "dev"
COOKIE = "ez_session"
now = lambda: dt.datetime.utcnow()
MAX_UPLOAD = 5 * 1024 * 1024
MAGIC = {".pdf": b"%PDF", ".png": b"\x89PNG", ".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff"}
UPLOAD_DIR = lambda: os.getenv("UPLOAD_DIR", "uploads")

class Farmer(Base):
    __tablename__ = "farmers"
    id = Column(String, primary_key=True); phone_hash = Column(String, unique=True, index=True)
    name = Column(String); language = Column(String, default="ta"); consent_version = Column(String)
    profile = Column(JSON, default=dict); created_at = Column(DateTime, default=now); last_active = Column(DateTime, default=now)
class Otp(Base):
    __tablename__ = "otps"
    id = Column(String, primary_key=True); phone_hash = Column(String, index=True); code_hash = Column(String)
    expires = Column(DateTime); attempts = Column(Integer, default=0); created_at = Column(DateTime, default=now)
class FamilyMember(Base):
    __tablename__ = "family_members"
    id = Column(String, primary_key=True); farmer_id = Column(String, index=True)
    relationship = Column(String); age = Column(Integer); occupation = Column(String); consent = Column(Boolean, default=False)
    has_disability = Column(Boolean); is_widowed = Column(Boolean); is_student = Column(Boolean)   # NULL = unknown
class Application(Base):
    __tablename__ = "applications"
    id = Column(String, primary_key=True); farmer_id = Column(String, index=True); scheme_id = Column(String)
    status = Column(String, default="prepared"); reference_number = Column(String); updated_at = Column(DateTime, default=now)
class Doc(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True); farmer_id = Column(String, index=True); doc_type = Column(String)
    filename = Column(String); verified = Column(Boolean, default=False)
    reviewed_by = Column(String); reviewed_at = Column(DateTime); review_outcome = Column(String)   # human check by a help centre (NOT official verification)
    sha256 = Column(String, index=True); quality = Column(JSON, default=list); created_at = Column(DateTime, default=now)
    extracted = Column(JSON, default=dict); confirmed = Column(JSON, default=dict)   # extracted = OCR proposal; confirmed = farmer-approved
class AppEvent(Base):
    __tablename__ = "application_events"
    id = Column(String, primary_key=True); application_id = Column(String, index=True); farmer_id = Column(String, index=True)
    status = Column(String); reference_number = Column(String); at = Column(DateTime, default=now)
class Revoked(Base):
    __tablename__ = "revoked_tokens"
    jti = Column(String, primary_key=True); exp = Column(Integer)
class Consent(Base):
    __tablename__ = "partner_consents"
    id = Column(String, primary_key=True); farmer_id = Column(String, index=True); partner_id = Column(String, index=True)
    granted_at = Column(DateTime, default=now); revoked_at = Column(DateTime)
class Note(Base):
    __tablename__ = "case_notes"
    id = Column(String, primary_key=True); farmer_id = Column(String, index=True); partner_id = Column(String)
    text = Column(String); at = Column(DateTime, default=now)
class Audit(Base):
    __tablename__ = "audit_log"
    id = Column(String, primary_key=True); actor = Column(String); action = Column(String); scheme_id = Column(String)
    farmer_id = Column(String, index=True); detail = Column(JSON); at = Column(DateTime, default=now)
class RuleReport(Base):     # a farmer or help centre says a scheme rule looks wrong -> reviewers see it in the admin screen
    __tablename__ = "rule_reports"
    id = Column(String, primary_key=True); farmer_id = Column(String, index=True); scheme_id = Column(String); rule_id = Column(String)
    text = Column(String); status = Column(String, default="open"); created_at = Column(DateTime, default=now)
Base.metadata.create_all(engine_db)   # NOTE: use Alembic migrations for real deployments (not yet set up)
if DB.startswith("sqlite"):   # append-only audit log enforced in the database (a DB admin could still drop these; use a separate DB role / WORM storage in production)
    with engine_db.begin() as cx:
        for ev in ("UPDATE", "DELETE"):
            cx.exec_driver_sql(f"CREATE TRIGGER IF NOT EXISTS audit_no_{ev.lower()} BEFORE {ev} ON audit_log BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;")

app = FastAPI(title="Ezhiyavan AI")
origins = [o for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE"],
                   allow_headers=["Authorization", "Content-Type", "X-Requested-With"])

# ---------- observability + shared rate limiting (REDIS_URL -> shared across workers; otherwise per process) ----------
log = obs.setup_logging(); limiter = ratelimit.make_limiter()
@app.middleware("http")
async def guard(request: Request, call_next):
    ip = netutil.client_ip(request.headers.get("x-forwarded-for", ""), request.client.host if request.client else "?",
                           os.getenv("TRUST_PROXY") == "1", int(os.getenv("TRUST_PROXY_HOPS", "1")))
    auth = request.url.path.startswith(("/api/auth", "/api/admin/login", "/api/partner/login"))
    limit = int(os.getenv("RATE_AUTH", "30")) if auth else int(os.getenv("RATE_API", "300"))
    ok, _ = limiter.hit(f"{ip}:{'auth' if auth else 'api'}", limit, 60)
    if not ok: obs.inc("rate_limited"); return JSONResponse({"detail": "too many requests"}, status_code=429)
    resp = await call_next(request); obs.inc("requests_total"); obs.inc(f"status_{resp.status_code // 100}xx")
    if resp.status_code in (401, 403): obs.inc("auth_denied")
    return resp

@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("unhandled error on %s", request.url.path); obs.inc_critical("unhandled_exception", request.url.path)
    return JSONResponse({"detail": "internal error"}, status_code=500)

@app.get("/healthz")
def healthz():
    try:
        with Session() as db: db.execute(__import__("sqlalchemy").text("select 1"))
    except Exception: obs.inc_critical("db_error"); return JSONResponse({"ok": False}, status_code=503)
    return {"ok": True}

def claims(request: Request, authorization: str = Header(default="")):
    tok, from_cookie = authorization.removeprefix("Bearer ").strip() if authorization else "", False
    if not tok: tok, from_cookie = request.cookies.get(COOKIE, ""), True
    c = sec.verify_token(tok) if tok else None
    if not c: raise HTTPException(401, "login required")
    if from_cookie and request.method not in ("GET", "HEAD", "OPTIONS") and request.headers.get("x-requested-with") != "ezhiyavan":
        raise HTTPException(403, "missing CSRF header")        # cookie auth + SameSite=Strict + custom header
    with Session() as db:
        if db.get(Revoked, c.get("jti")): raise HTTPException(401, "logged out")
    return c
def farmer_id(c=Depends(claims)):
    if c["role"] != "farmer": raise HTTPException(403)
    return c["sub"]
def admin(c=Depends(claims)):
    if c["role"] != "admin": raise HTTPException(403)
    return c["sub"]
def partner(c=Depends(claims)):
    if c["role"] != "partner": raise HTTPException(403)
    return c["sub"]
@app.get("/api/admin/metrics")
def metrics(who=Depends(admin)): return {"counters": obs.snapshot(), "ocr_languages_available": sorted(dcs.available_languages())}
def audit(db, actor, action, scheme_id=None, detail=None, farmer_id=None):
    db.add(Audit(id=str(uuid.uuid4()), actor=actor, action=action, scheme_id=scheme_id, farmer_id=farmer_id, detail=detail or {}))

# ---------- auth ----------
class OtpReq(BaseModel): phone: str = Field(pattern=r"^[6-9]\d{9}$")
class OtpVerify(OtpReq): code: str = Field(pattern=r"^\d{6}$"); consent: bool; language: str = "ta"
def send_sms(phone, code):
    """Twilio adapter (set TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM). Untested against the live API. NOTE: sending SMS inside India normally needs
    DLT registration of sender/template with an Indian operator/gateway - replace this function with your DLT-compliant gateway if needed."""
    sid, tok, frm = os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"), os.getenv("TWILIO_FROM")
    if not (sid and tok and frm): raise RuntimeError("SMS provider not configured")
    data = urllib.parse.urlencode({"To": "+91" + phone, "From": frm, "Body": f"Ezhiyavan AI code {code}. Valid 5 minutes. Do not share it."}).encode()
    req = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", data,
                                 {"Authorization": "Basic " + base64.b64encode(f"{sid}:{tok}".encode()).decode()})
    with urllib.request.urlopen(req, timeout=10) as r:
        if r.status >= 300: raise RuntimeError("SMS send failed")

@app.post("/api/auth/request-otp")
def request_otp(b: OtpReq):
    ph = sec.hash_phone(b.phone)
    with Session() as db:
        if db.query(Otp).filter(Otp.phone_hash == ph, Otp.created_at > now() - dt.timedelta(minutes=10)).count() >= 3:
            raise HTTPException(429, "too many requests, try later")
        code = sec.new_otp()
        db.add(Otp(id=str(uuid.uuid4()), phone_hash=ph, code_hash=sec.hash_otp(b.phone, code), expires=now() + dt.timedelta(minutes=5))); db.commit()
    if DEV: return {"sent": True, "dev_code": code}
    try: send_sms(b.phone, code)
    except Exception: obs.inc_critical("otp_send_failed"); raise HTTPException(503, "SMS provider not configured")
    return {"sent": True}

@app.post("/api/auth/verify-otp")
def verify_otp(b: OtpVerify, response: Response):
    if not b.consent: raise HTTPException(400, "consent required")
    ph = sec.hash_phone(b.phone)
    with Session() as db:
        o = db.query(Otp).filter(Otp.phone_hash == ph, Otp.expires > now()).order_by(Otp.created_at.desc()).first()
        if not o or o.attempts >= 5: raise HTTPException(401, "invalid or expired code")
        o.attempts += 1
        if o.code_hash != sec.hash_otp(b.phone, b.code): db.commit(); obs.inc("otp_verify_failed"); raise HTTPException(401, "invalid or expired code")
        db.delete(o)
        f = db.query(Farmer).filter_by(phone_hash=ph).first()
        if f: f.last_active = now()
        if not f:
            f = Farmer(id=str(uuid.uuid4()), phone_hash=ph, language=b.language if b.language in ("ta", "en", "hi") else "ta", consent_version="v1", profile={}); db.add(f)
        db.commit(); tok = sec.make_token(f.id, "farmer")
    response.set_cookie(COOKIE, tok, httponly=True, samesite="strict", secure=not DEV, max_age=12 * 3600, path="/api")
    return {"ok": True, **({"token": tok} if DEV else {})}     # token in body only in dev; production uses the HttpOnly cookie

@app.post("/api/auth/logout")
def logout(response: Response, c=Depends(claims)):
    with Session() as db:
        db.merge(Revoked(jti=c["jti"], exp=c["exp"])); db.query(Revoked).filter(Revoked.exp < int(time.time())).delete(); db.commit()
    response.delete_cookie(COOKIE, path="/api"); return {"ok": True}
@app.get("/api/me/session")
def session_ok(fid=Depends(farmer_id)): return {"ok": True}

# ---------- discovery ----------
def members_of(db, fid):
    return [{"id": m.id, "relationship": m.relationship, "age": m.age, "occupation": m.occupation, "consent": bool(m.consent),
             "has_disability": m.has_disability, "is_widowed": m.is_widowed, "is_student": m.is_student}
            for m in db.query(FamilyMember).filter_by(farmer_id=fid)]
def discovery(db, fid):
    f = db.get(Farmer, fid); schemes = eng.load_schemes(); order = {"green": 0, "amber": 1, "red": 2}
    hh = sorted((eng.evaluate(s, f.profile) for s in schemes if s.get("applies_to") != "member"), key=lambda r: order[r["status"]])
    mem = eng.evaluate_members(schemes, f.profile, members_of(db, fid))
    return {"profile": f.profile, "results": hh, "members": mem, "estimate": eng.estimate(hh, mem), "summary": insights.summarize(hh, schemes),
            "disclaimer": "Potential eligibility only. Official verification decides."}
def set_field(db, fid, field, value, actor=None):
    if field not in eng.needed_fields(eng.load_schemes()): raise HTTPException(400, "unknown field")
    try: value = validate_value(field, value)
    except ValueError as e: raise HTTPException(400, str(e))
    f = db.get(Farmer, fid); p = dict(f.profile); p[field] = value; f.profile = p
    if actor: audit(db, actor, "set_profile_field", farmer_id=fid, detail={"field": field})
    db.commit(); return p

class Answer(BaseModel): field: str; text: str = Field(max_length=500)
class Confirm(BaseModel): field: str; value: object; overwrite: bool = False
class AppIn(BaseModel): scheme_id: str
class AppPatch(BaseModel): status: str; reference_number: str = Field(default="", max_length=60)
class Member(BaseModel):
    relationship: str = Field(max_length=30); age: int = Field(ge=0, le=120); occupation: str = Field(default="", max_length=60); consent: bool = False
    has_disability: bool | None = None; is_widowed: bool | None = None; is_student: bool | None = None

@app.get("/api/me/next-question")
def next_q(lang: str = "", fid=Depends(farmer_id)):
    with Session() as db:
        f = db.get(Farmer, fid)
        schemes = eng.load_schemes(); skip = eng.redundant_fields(schemes, f.profile)
        todo = [x for x in eng.needed_fields(schemes) if x not in f.profile and x not in skip]
        if todo: return {"field": todo[0], "kind": field_kind(todo[0]), "question": question(todo[0], lang or f.language), "answered": len(f.profile), "remaining": len(todo)}     # remaining is an estimate: one answer can make others unnecessary
        return {"done": True, "answered": len(f.profile), "remaining": 0}

@app.delete("/api/me/answers/{field}")
def undo_answer(field: str, fid=Depends(farmer_id)):      # "Back": the farmer takes back one answer, which is then asked again
    if field not in eng.needed_fields(eng.load_schemes()): raise HTTPException(400, "unknown field")
    with Session() as db:
        f = db.get(Farmer, fid); p = dict(f.profile)
        if field in p:
            del p[field]; f.profile = p; audit(db, "farmer", "undo_answer", farmer_id=fid, detail={"field": field}); db.commit()
        return {"ok": True}

@app.post("/api/me/extract")
def extract_answer(a: Answer, fid=Depends(farmer_id)):
    if a.field not in eng.needed_fields(eng.load_schemes()): raise HTTPException(400, "unknown field")
    with Session() as db: lang = db.get(Farmer, fid).language
    return {"field": a.field, **extract_smart(a.field, a.text, lang)}

@app.post("/api/me/confirm")
def confirm(c: Confirm, fid=Depends(farmer_id)):
    with Session() as db:
        prev = db.get(Farmer, fid).profile.get(c.field)
        if prev is not None and prev != c.value and not c.overwrite:      # contradiction with an earlier answer
            raise HTTPException(409, json.dumps({"previous": prev, "new": c.value}))
        return {"profile": set_field(db, fid, c.field, c.value)}

class Chat(BaseModel): text: str = Field(min_length=1, max_length=800)
@app.post("/api/me/chat")
def chat(b: Chat, fid=Depends(farmer_id)):
    """Free-text message -> several proposed facts. Nothing is saved here; the farmer confirms each proposal via /api/me/confirm."""
    with Session() as db: f = db.get(Farmer, fid); lang, known = f.language, dict(f.profile)
    return {"proposals": extract_many(b.text, lang, eng.needed_fields(eng.load_schemes()), known)}

@app.get("/api/me/discover")
def discover(fid=Depends(farmer_id)):
    with Session() as db: return discovery(db, fid)

@app.post("/api/me/family")
def add_member(m: Member, fid=Depends(farmer_id)):
    with Session() as db: db.add(FamilyMember(id=str(uuid.uuid4()), farmer_id=fid, **m.model_dump())); db.commit(); return {"ok": True}
@app.get("/api/me/family")
def list_family(fid=Depends(farmer_id)):
    with Session() as db: return members_of(db, fid)
@app.delete("/api/me/family/{mid}")
def del_member(mid: str, fid=Depends(farmer_id)):
    with Session() as db: db.query(FamilyMember).filter_by(id=mid, farmer_id=fid).delete(); db.commit(); return {"ok": True}

# ---------- applications ----------
@app.post("/api/me/applications")
def add_app(b: AppIn, fid=Depends(farmer_id)):
    if b.scheme_id not in {s["scheme_id"] for s in eng.load_schemes()}: raise HTTPException(400, "unknown scheme")
    with Session() as db:
        a = Application(id=str(uuid.uuid4()), farmer_id=fid, scheme_id=b.scheme_id); db.add(a)
        db.add(AppEvent(id=str(uuid.uuid4()), application_id=a.id, farmer_id=fid, status="prepared", reference_number="")); db.commit(); return {"id": a.id}
@app.get("/api/me/applications")
def list_apps(fid=Depends(farmer_id)):
    with Session() as db:
        return [{"id": a.id, "scheme_id": a.scheme_id, "status": a.status, "reference_number": a.reference_number, "source": "self-reported"}
                for a in db.query(Application).filter_by(farmer_id=fid)]
@app.patch("/api/me/applications/{aid}")
def patch_app(aid: str, b: AppPatch, fid=Depends(farmer_id)):
    if b.status not in {"prepared", "submitted", "under_review", "approved", "received", "rejected"}: raise HTTPException(400, "bad status")
    with Session() as db:
        a = db.get(Application, aid)
        if not a or a.farmer_id != fid: raise HTTPException(404)
        a.status, a.reference_number, a.updated_at = b.status, b.reference_number, now()
        db.add(AppEvent(id=str(uuid.uuid4()), application_id=aid, farmer_id=fid, status=b.status, reference_number=b.reference_number)); db.commit(); return {"ok": True}
@app.get("/api/me/applications/{aid}/history")
def app_history(aid: str, fid=Depends(farmer_id)):
    with Session() as db:
        a = db.get(Application, aid)
        if not a or a.farmer_id != fid: raise HTTPException(404)
        return [{"status": e.status, "reference_number": e.reference_number, "at": e.at.isoformat(), "source": "self-reported"}
                for e in db.query(AppEvent).filter_by(application_id=aid).order_by(AppEvent.at)]

@app.get("/api/me/applications/{aid}/timeline")
def app_timeline(aid: str, fid=Depends(farmer_id)):
    with Session() as db:
        a = db.get(Application, aid)
        if not a or a.farmer_id != fid: raise HTTPException(404)
        return tl.build([{"status": e.status, "reference_number": e.reference_number, "at": e.at.isoformat()} for e in db.query(AppEvent).filter_by(application_id=aid).order_by(AppEvent.at)])

# ---------- documents ----------
def clamav_scan(data: bytes):
    """Optional: set CLAMD_HOST (and CLAMD_PORT, default 3310). Returns True if clean. Fails CLOSED if configured but unreachable."""
    host = os.getenv("CLAMD_HOST")
    if not host: return True
    try:
        with socket.create_connection((host, int(os.getenv("CLAMD_PORT", "3310"))), timeout=10) as s:
            s.sendall(b"zINSTREAM\0")
            for i in range(0, len(data), 8192):
                chunk = data[i:i + 8192]; s.sendall(struct.pack("!I", len(chunk)) + chunk)
            s.sendall(struct.pack("!I", 0)); return b"OK" in s.recv(1024)
    except Exception: return False

def _fernet():
    k = os.getenv("FILE_ENC_KEY")
    if not k: return None
    from cryptography.fernet import Fernet, MultiFernet
    return MultiFernet([Fernet(x.strip().encode()) for x in k.split(",") if x.strip()])   # comma list, newest first (see scripts/rotate_key.py)

@app.post("/api/me/documents")
async def upload_doc(doc_type: str, file: UploadFile = File(...), fid=Depends(farmer_id)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in MAGIC or not re.fullmatch(r"[a-z_]{1,30}", doc_type): obs.inc("upload_rejected"); raise HTTPException(400, "unsupported file or type")
    fer = _fernet()
    if fer is None and not DEV: raise HTTPException(503, "document encryption not configured (set FILE_ENC_KEY)")   # fail closed in production
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD: obs.inc("upload_rejected"); raise HTTPException(413, "file too large (max 5 MB)")
    if not data.startswith(MAGIC[ext]): obs.inc("upload_rejected"); raise HTTPException(400, "file content does not match its type")
    if not clamav_scan(data): obs.inc("upload_rejected"); raise HTTPException(422, "file rejected by malware scan")
    digest = hashlib.sha256(data).hexdigest()
    with Session() as db:
        dup = db.query(Doc).filter_by(farmer_id=fid, sha256=digest).first()
        if dup: return {"id": dup.id, "duplicate": True, "ocr_available": bool(dup.extracted), "analysis": None, "type_mismatch": False, "verified": False,
                        "quality_warnings": dup.quality or [], "note": "This file was already uploaded."}
    with tempfile.TemporaryDirectory() as tmp:                      # plaintext exists only here, briefly, for OCR
        tp = os.path.join(tmp, "in" + ext); open(tp, "wb").write(data); info = await run_in_threadpool(dcs.read_document, tp)
    analysis = dcs.analyze(info["text"], info["mean_conf"]) if info["text"] else None; warns = dcs.quality_warnings(info)
    if info["text"] is None: obs.inc("ocr_unreadable")
    d = os.path.join(UPLOAD_DIR(), fid); os.makedirs(d, mode=0o700, exist_ok=True)
    name = uuid.uuid4().hex + ext + (".enc" if fer else ""); open(os.path.join(d, name), "wb").write(fer.encrypt(data) if fer else data)
    did = str(uuid.uuid4())
    with Session() as db:
        db.add(Doc(id=did, farmer_id=fid, doc_type=doc_type, filename=name, sha256=digest, quality=warns, extracted=(analysis or {}).get("fields", {}))); db.commit()
    return {"id": did, "duplicate": False, "ocr_available": info["text"] is not None, "ocr_method": info["method"], "analysis": analysis, "quality_warnings": warns,
            "type_mismatch": bool(analysis and analysis["detected_type"] not in ("unknown", doc_type)), "verified": False,
            "note": "Read from the document only. Authenticity is not verified. Please check the values."}
def doc_view(d): return {"id": d.id, "doc_type": d.doc_type, "extracted": d.extracted or {}, "confirmed": d.confirmed or {}, "verified": bool(d.verified), "quality_warnings": d.quality or [],
            "checked_by_a_person": bool(d.reviewed_by), "review_outcome": d.review_outcome, "reviewed_at": d.reviewed_at.isoformat() if d.reviewed_at else None}
@app.get("/api/me/documents")
def list_docs(fid=Depends(farmer_id)):
    with Session() as db: return [doc_view(d) for d in db.query(Doc).filter_by(farmer_id=fid)]
@app.get("/api/me/documents/issues")
def my_doc_issues(fid=Depends(farmer_id)):
    with Session() as db: return dcs.doc_issues([doc_view(d) for d in db.query(Doc).filter_by(farmer_id=fid)], db.get(Farmer, fid).profile)
@app.get("/api/me/family/issues")
def my_family_issues(fid=Depends(farmer_id)):
    with Session() as db: return eng.family_issues(members_of(db, fid))
class DocConfirm(BaseModel): fields: dict
@app.post("/api/me/documents/{did}/confirm")
def confirm_doc(did: str, b: DocConfirm, fid=Depends(farmer_id)):
    clean = {}
    for k, v in b.fields.items():
        if k not in dcs.ALLOWED_FIELDS: raise HTTPException(400, f"field not allowed: {k}")
        if k in ("issue_date", "valid_until"):
            try: dt.date.fromisoformat(str(v))
            except ValueError: raise HTTPException(400, f"{k} must be YYYY-MM-DD")
        elif k in ("area_acres", "income_inr"):
            if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0: raise HTTPException(400, f"{k} must be a positive number")
        elif not isinstance(v, str) or len(v) > 30: raise HTTPException(400, f"{k} must be short text")
        clean[k] = v
    with Session() as db:
        d = db.get(Doc, did)
        if not d or d.farmer_id != fid: raise HTTPException(404)
        d.confirmed = clean; db.commit(); return doc_view(d)

@app.get("/api/me/reminders")
def reminders(fid=Depends(farmer_id)):
    with Session() as db:
        res = discovery(db, fid)["results"]; docs = [doc_view(d) for d in db.query(Doc).filter_by(farmer_id=fid)]
    return dcs.build_reminders(res, docs)

def erase_farmer(db, fid):
    """Removes ALL of a farmer's data (rows + files). Audit-log rows are kept (append-only) but hold only pseudonymous ids."""
    for m in (Application, AppEvent, Doc, FamilyMember, Consent, Note, RuleReport): db.query(m).filter_by(farmer_id=fid).delete()
    db.query(Farmer).filter_by(id=fid).delete(); db.commit()
    shutil.rmtree(os.path.join(UPLOAD_DIR(), fid), ignore_errors=True)

@app.delete("/api/me")
def delete_me(fid=Depends(farmer_id)):
    with Session() as db: erase_farmer(db, fid)
    return {"deleted": True}

def _qr_svg(url):
    """QR code to the official portal. Needs the optional 'segno' package; returns None without it."""
    try:
        import segno, io
        b = io.BytesIO(); segno.make(url, error="m").save(b, kind="svg", xmldecl=False, scale=4); return b.getvalue().decode()
    except Exception: return None

@app.get("/api/me/claim-pack/{scheme_id}")
def claim_pack(scheme_id: str, fid=Depends(farmer_id)):
    """Printable preparation summary for one household scheme. Contains no phone number, Aadhaar, PAN or bank numbers."""
    with Session() as db:
        f = db.get(Farmer, fid); docs = [doc_view(d) for d in db.query(Doc).filter_by(farmer_id=fid)]; have = {d["doc_type"]: bool(d["confirmed"]) for d in docs}
        sc = next((x for x in eng.load_schemes() if x["scheme_id"] == scheme_id and x.get("applies_to") != "member"), None)
        if not sc: raise HTTPException(404)
        r = eng.evaluate(sc, f.profile); fields = sorted({x["field"] for x in r["trace"] if x["field"] not in ("-",)})
        facts = {k: f.profile[k] for k in ",".join(fields).split(",") if k in f.profile}
        return {"scheme": {k: r[k] for k in ("scheme_id", "name", "version", "source", "last_verified", "rule_status", "benefit", "deadline")},
                "status": r["status"], "trace": r["trace"], "facts_confirmed_by_you": facts,
                "document_checklist": [{"doc_type": t, "uploaded": t in have, "details_confirmed": have.get(t, False), "checked_by_a_person": any(x["doc_type"] == t and x["checked_by_a_person"] for x in docs)} for t in r["required_doc_types"]],
                "assurance": dcs.assurance(r["status"], list(have), [x["doc_type"] for x in docs if x["checked_by_a_person"]]),
                "timeline": (lambda a: tl.build([{"status": e.status, "reference_number": e.reference_number, "at": e.at.isoformat()} for e in db.query(AppEvent).filter_by(application_id=a.id).order_by(AppEvent.at)]) if a else None)(
                    db.query(Application).filter_by(farmer_id=fid, scheme_id=scheme_id).order_by(Application.updated_at.desc()).first()),
                "tracking": [{"status": a.status, "reference_number": a.reference_number, "updated": a.updated_at.isoformat()[:10], "source": "self-reported"} for a in db.query(Application).filter_by(farmer_id=fid, scheme_id=scheme_id)],
                "qr_svg": _qr_svg(r["source"]),
                "other_documents": r["documents"], "steps": r["application_steps"], "manual_checks": r["manual_checks"],
                "generated_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "disclaimer": "Preparation aid only. Potential eligibility is not approval. Apply only through the official source above; never share OTPs or PINs."}

# ---------- partner (CSC / NGO) consent + dashboard ----------
def users(env): return json.loads(os.getenv(env, "{}"))
class ConsentIn(BaseModel): partner_id: str
@app.post("/api/me/consents")
def grant(b: ConsentIn, fid=Depends(farmer_id)):
    if b.partner_id not in users("PARTNER_USERS"): raise HTTPException(404, "unknown partner")
    with Session() as db:
        if not db.query(Consent).filter_by(farmer_id=fid, partner_id=b.partner_id, revoked_at=None).first():
            db.add(Consent(id=str(uuid.uuid4()), farmer_id=fid, partner_id=b.partner_id)); audit(db, fid, "consent_granted", farmer_id=fid, detail={"partner": b.partner_id}); db.commit()
    return {"ok": True}
@app.get("/api/me/consents")
def list_consents(fid=Depends(farmer_id)):
    with Session() as db: return [{"partner_id": c.partner_id, "granted_at": c.granted_at.isoformat()} for c in db.query(Consent).filter_by(farmer_id=fid, revoked_at=None)]
@app.delete("/api/me/consents/{pid}")
def revoke(pid: str, fid=Depends(farmer_id)):
    with Session() as db:
        for c in db.query(Consent).filter_by(farmer_id=fid, partner_id=pid, revoked_at=None): c.revoked_at = now()
        audit(db, fid, "consent_revoked", farmer_id=fid, detail={"partner": pid}); db.commit()
    return {"ok": True}
@app.get("/api/me/access-log")
def access_log(fid=Depends(farmer_id)):
    with Session() as db: return [{"actor": a.actor, "action": a.action, "at": a.at.isoformat()} for a in db.query(Audit).filter_by(farmer_id=fid).order_by(Audit.at.desc()).limit(100)]
@app.get("/api/me/notes")
def my_notes(fid=Depends(farmer_id)):
    with Session() as db: return [{"partner_id": n.partner_id, "text": n.text, "at": n.at.isoformat()} for n in db.query(Note).filter_by(farmer_id=fid)]

class Login(BaseModel): user: str; password: str
def _login(env, b, role, ttl):
    u = users(env)
    if b.user not in u or not sec.check_password(b.password, u[b.user]): raise HTTPException(401, "invalid credentials")
    return {"token": sec.make_token(b.user, role, ttl=ttl)}
@app.post("/api/admin/login")
def admin_login(b: Login): return _login("ADMIN_USERS", b, "admin", 1800)
@app.post("/api/partner/login")
def partner_login(b: Login): return _login("PARTNER_USERS", b, "partner", 3600)

def consented(db, pid, fid):
    if not db.query(Consent).filter_by(farmer_id=fid, partner_id=pid, revoked_at=None).first(): raise HTTPException(404)   # same 404: no probing
@app.get("/api/partner/cases")
def cases(pid=Depends(partner)):
    with Session() as db:
        out = []
        for c in db.query(Consent).filter_by(partner_id=pid, revoked_at=None):
            f = db.get(Farmer, c.farmer_id)
            if f: out.append({"farmer_ref": f.id, "language": f.language, "answers": len(f.profile), "applications": db.query(Application).filter_by(farmer_id=f.id).count(), "granted_at": c.granted_at.isoformat()})
        return out
@app.get("/api/partner/cases/{fid}")
def case(fid: str, pid=Depends(partner)):
    with Session() as db:
        consented(db, pid, fid); audit(db, pid, "view_case", farmer_id=fid); db.commit()
        docs = [doc_view(d) for d in db.query(Doc).filter_by(farmer_id=fid)]; disc = discovery(db, fid)
        apps = [{"scheme_id": a.scheme_id, "status": a.status, "reference_number": a.reference_number} for a in db.query(Application).filter_by(farmer_id=fid)]
        f = db.get(Farmer, fid)
        un = [{"field": x, "kind": field_kind(x), "question": question(x, "en")} for x in eng.needed_fields(eng.load_schemes()) if x not in f.profile and x not in eng.redundant_fields(eng.load_schemes(), f.profile)]
        cons = db.query(Consent).filter_by(farmer_id=fid, partner_id=pid, revoked_at=None).first()
        return {**disc, "documents": docs, "applications": apps, "unanswered": un, "consent": {"granted_at": cons.granted_at.isoformat()}, "doc_issues": dcs.doc_issues(docs, disc["profile"]),
                "family_issues": eng.family_issues(members_of(db, fid)), "reminders": dcs.build_reminders(disc["results"], docs)}
class PField(BaseModel): field: str; value: object; farmer_present: bool = False
@app.post("/api/partner/cases/{fid}/profile")
def partner_set(fid: str, b: PField, pid=Depends(partner)):
    if not b.farmer_present: raise HTTPException(400, "confirm that the farmer is present and agrees before entering their information")
    with Session() as db: consented(db, pid, fid); return {"profile": set_field(db, fid, b.field, b.value, actor=pid)}
class Review(BaseModel): outcome: str = Field(pattern="^(looks_consistent|needs_attention)$"); farmer_present: bool = False
@app.post("/api/partner/cases/{fid}/documents/{did}/review")
def review_doc(fid: str, did: str, b: Review, pid=Depends(partner)):
    """A person at the help centre looked at the document. This is NOT official verification and does not authenticate the document."""
    if not b.farmer_present: raise HTTPException(400, "confirm the farmer is present")
    with Session() as db:
        consented(db, pid, fid); d = db.get(Doc, did)
        if not d or d.farmer_id != fid: raise HTTPException(404)
        d.reviewed_by, d.reviewed_at, d.review_outcome = pid, now(), b.outcome; audit(db, pid, "review_document", farmer_id=fid, detail={"doc_type": d.doc_type, "outcome": b.outcome}); db.commit(); return {"ok": True}
class NoteIn(BaseModel): text: str = Field(min_length=1, max_length=500)
@app.post("/api/partner/cases/{fid}/notes")
def add_note(fid: str, b: NoteIn, pid=Depends(partner)):
    with Session() as db:
        consented(db, pid, fid); db.add(Note(id=str(uuid.uuid4()), farmer_id=fid, partner_id=pid, text=b.text)); audit(db, pid, "add_note", farmer_id=fid); db.commit(); return {"ok": True}

# ---------- schemes / admin ----------
@app.get("/api/schemes")
def schemes(): return [{k: s[k] for k in ("scheme_id", "name", "version", "status", "source", "last_verified")} for s in eng.load_schemes()]
def _path(sid):
    if not re.fullmatch(r"[A-Za-z0-9_]{1,40}", sid): raise HTTPException(400, "bad scheme_id")
    return os.path.join(eng.SCHEME_DIR, sid.lower() + ".json")
@app.get("/api/admin/schemes")
def list_all_schemes(who=Depends(admin)):
    out = []
    for p in sorted(os.listdir(eng.SCHEME_DIR)):
        if p.endswith(".json"):
            s = json.load(open(os.path.join(eng.SCHEME_DIR, p), encoding="utf-8"))
            out.append({k: s.get(k) for k in ("scheme_id", "name", "version", "status", "source", "last_verified", "submitted_by", "approved_by", "approvals", "review_notes", "conditions_complete", "expires")}
                       | {"rule_count": len(s.get("rules", [])), "evidence_blockers": len(eng.approval_blockers(s))})
    return out
@app.get("/api/admin/schemes/{sid}")
def get_scheme(sid: str, who=Depends(admin)):
    p = _path(sid)
    if not os.path.exists(p): raise HTTPException(404)
    return json.load(open(p, encoding="utf-8"))

@app.post("/api/admin/schemes")
def submit_scheme(s: dict, who=Depends(admin)):
    errs = eng.validate_scheme(s)
    if errs: raise HTTPException(400, errs)
    p = _path(s["scheme_id"])
    if os.path.exists(p):
        h = os.path.join(eng.SCHEME_DIR, "history"); os.makedirs(h, exist_ok=True)
        old = json.load(open(p, encoding="utf-8")); shutil.copy(p, os.path.join(h, f"{s['scheme_id'].lower()}_{old['version']}.json"))
    s.update(status="pending_review", submitted_by=who, last_verified=None, approvals=[], approved_by=None)
    json.dump(s, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    with Session() as db: audit(db, who, "submit", s["scheme_id"], {"version": s["version"]}); db.commit()
    return {"saved": True, "status": "pending_review"}
def _history(sid):
    """Most recent previously VERIFIED version of a scheme (for diffs and the high-impact decision)."""
    h = os.path.join(eng.SCHEME_DIR, "history"); best = None
    if os.path.isdir(h):
        for f in os.listdir(h):
            if f.startswith(sid.lower() + "_") and f.endswith(".json"):
                d = json.load(open(os.path.join(h, f), encoding="utf-8"))
                if d.get("status") == "verified" and (best is None or (d.get("last_verified") or "") > (best.get("last_verified") or "")): best = d
    return best

@app.post("/api/admin/schemes/{sid}/approve")
def approve_scheme(sid: str, who=Depends(admin)):
    p = _path(sid)
    if not os.path.exists(p): raise HTTPException(404)
    s = json.load(open(p, encoding="utf-8"))
    try: res = eng.apply_approval(s, who, _history(sid))
    except eng.ApprovalError as e: raise HTTPException(400 if e.blockers else 403, {"error": str(e), "blockers": e.blockers})
    json.dump(s, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    with Session() as db: audit(db, who, "approve", sid, {"version": s["version"], **res}); db.commit()
    return res
@app.get("/api/admin/schemes/{sid}/diff")
def scheme_diff(sid: str, who=Depends(admin)):
    p = _path(sid)
    if not os.path.exists(p): raise HTTPException(404)
    new = json.load(open(p, encoding="utf-8")); old = _history(sid)
    return {"against_version": old.get("version") if old else None, "high_impact": eng.high_impact(old, new), "blockers": eng.approval_blockers(new),
            "diff": eng.diff_schemes(old, new) if old else None}
class ReadinessIn(BaseModel):
    status: str | None = None; evidence: str = ""; reviewer: str = ""; tested_on: str = ""; report: dict | None = None; outstanding: list[str] = []
@app.get("/api/admin/readiness")
def readiness_board(who=Depends(admin)): return rdy.board()
@app.post("/api/admin/readiness/{check_id}")
def readiness_record(check_id: str, b: ReadinessIn, who=Depends(admin)):
    try: e = rdy.record(check_id, who, b.status, b.evidence, b.reviewer, b.tested_on, b.report, b.outstanding)
    except rdy.ReadinessError as err: raise HTTPException(400, str(err))
    with Session() as db: audit(db, who, "readiness_record", check_id, {"status": e["status"], "reviewer": e["reviewer"], "tested_on": e["tested_on"]}); db.commit()
    return e
@app.get("/api/admin/trust")
def trust(who=Depends(admin)): return eng.trust_report(eng.load_all())

@app.get("/api/admin/audit")
def get_audit(who=Depends(admin)):
    with Session() as db: return [{"actor": a.actor, "action": a.action, "scheme_id": a.scheme_id, "farmer_id": a.farmer_id, "detail": a.detail, "at": a.at.isoformat()}
                                  for a in db.query(Audit).order_by(Audit.at.desc()).limit(200)]

# ---------- "this rule looks wrong" reports + impact dashboard ----------
class ReportIn(BaseModel): scheme_id: str; rule_id: str = Field(default="", max_length=40); text: str = Field(min_length=5, max_length=500)
@app.post("/api/me/report-rule")
def report_rule(b: ReportIn, fid=Depends(farmer_id)):
    if b.scheme_id not in {x["scheme_id"] for x in eng.load_all()}: raise HTTPException(400, "unknown scheme")
    with Session() as db:
        if db.query(RuleReport).filter_by(farmer_id=fid, status="open").count() >= 10: raise HTTPException(429, "too many open reports")
        r = RuleReport(id=str(uuid.uuid4()), farmer_id=fid, scheme_id=b.scheme_id, rule_id=b.rule_id.strip(), text=b.text.strip())
        db.add(r); audit(db, "farmer", "report_rule", scheme_id=b.scheme_id, farmer_id=fid, detail={"rule_id": r.rule_id}); db.commit()
        return {"ok": True, "id": r.id}

@app.get("/api/admin/reports")
def list_reports(who=Depends(admin)):
    with Session() as db:
        return [{"id": r.id, "scheme_id": r.scheme_id, "rule_id": r.rule_id, "text": r.text, "status": r.status, "at": r.created_at.isoformat()}
                for r in db.query(RuleReport).order_by(RuleReport.created_at.desc()).limit(200)]      # no farmer id: reviewers judge the rule, not the person

@app.post("/api/admin/reports/{rid}/close")
def close_report(rid: str, who=Depends(admin)):
    with Session() as db:
        r = db.get(RuleReport, rid)
        if not r: raise HTTPException(404)
        r.status = "closed"; audit(db, who, "close_rule_report", scheme_id=r.scheme_id, detail={"report": rid}); db.commit(); return {"ok": True}

@app.get("/api/admin/impact")
def impact_report(who=Depends(admin)):
    with Session() as db:
        types = {}
        for d in db.query(Doc).all():
            if d.confirmed: types.setdefault(d.farmer_id, set()).add(d.doc_type)      # supplied = the farmer confirmed its values
        rows = [{"profile": f.profile, "doc_types": types.get(f.id, ()), "active_days": (now() - f.last_active).days if f.last_active else None}
                for f in db.query(Farmer).limit(5000)]
        apps_by_status = {}
        for (st,) in db.query(Application.status).all(): apps_by_status[st] = apps_by_status.get(st, 0) + 1
    return {**insights.impact(rows, eng.load_schemes()), "applications_by_self_reported_status": apps_by_status}
