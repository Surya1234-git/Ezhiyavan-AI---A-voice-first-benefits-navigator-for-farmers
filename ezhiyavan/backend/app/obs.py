"""Observability that never leaks personal data: log scrubbing, JSON logs, in-process counters, optional alert webhook."""
import json, logging, os, re, threading, urllib.request
from . import docs

_PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{7})(\d{2})(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_OTP = re.compile(r"((?:otp|code|கடவுச்சொல்)\D{0,12})(\d{4,8})", re.I)
def scrub(text):
    """Masks Aadhaar, PAN, bank account numbers, phone numbers, e-mail addresses and OTP-like codes."""
    t, _ = docs.redact(str(text)); t = _EMAIL.sub("[EMAIL]", t); t = _OTP.sub(lambda m: m.group(1) + "[OTP]", t)
    return _PHONE.sub(lambda m: "[PHONE]" + m.group(2), t)

class JsonFormatter(logging.Formatter):
    def format(self, r):
        msg = r.getMessage()
        if r.exc_info: msg += "\n" + self.formatException(r.exc_info)
        return json.dumps({"t": self.formatTime(r, "%Y-%m-%dT%H:%M:%S"), "level": r.levelname, "logger": r.name, "msg": scrub(msg)}, ensure_ascii=False)

def setup_logging():
    h = logging.StreamHandler(); h.setFormatter(JsonFormatter()); root = logging.getLogger(); root.handlers = [h]; root.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    return logging.getLogger("ezhiyavan")

_lock = threading.Lock(); _counts = {}
def inc(name, n=1):
    with _lock: _counts[name] = _counts.get(name, 0) + n
def snapshot():
    with _lock: return dict(_counts)
def reset():
    with _lock: _counts.clear()

CRITICAL = {"unhandled_exception": 1, "ratelimit_backend_error": 1, "otp_send_failed": 3, "db_error": 1}      # alert when a counter first reaches its threshold
def alert(name, detail=""):
    """POSTs a scrubbed message to ALERT_WEBHOOK_URL (e.g. a chat/pager webhook). Never raises. NOT tested against a live endpoint."""
    url = os.getenv("ALERT_WEBHOOK_URL")
    if not url: return False
    try:
        req = urllib.request.Request(url, json.dumps({"text": scrub(f"[ezhiyavan] {name}: {detail}")[:500]}).encode(), {"content-type": "application/json"}); urllib.request.urlopen(req, timeout=3); return True
    except Exception: return False
def inc_critical(name, detail=""):
    inc(name)
    if name in CRITICAL and snapshot()[name] == CRITICAL[name]: alert(name, detail)
