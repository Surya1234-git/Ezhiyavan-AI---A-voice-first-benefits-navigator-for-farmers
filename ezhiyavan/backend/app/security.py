"""Stdlib-only auth helpers: HMAC-signed tokens, salted phone hashing, OTP hashing."""
import base64, hashlib, hmac, json, os, secrets, time
SECRET = os.getenv("SECRET_KEY", "")
def _key():
    if not SECRET or SECRET == "change-me": raise RuntimeError("Set SECRET_KEY to a long random value")
    return SECRET.encode()
def _b(x): return base64.urlsafe_b64encode(x).rstrip(b"=").decode()
def _ub(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
def make_token(sub, role="farmer", ttl=3600 * 12):
    body = _b(json.dumps({"sub": sub, "role": role, "jti": secrets.token_hex(8), "exp": int(time.time()) + ttl}).encode())
    return body + "." + _b(hmac.new(_key(), body.encode(), hashlib.sha256).digest())
def verify_token(tok):
    try:
        body, sig = tok.split(".")
        if not hmac.compare_digest(sig, _b(hmac.new(_key(), body.encode(), hashlib.sha256).digest())): return None
        c = json.loads(_ub(body))
        return c if c["exp"] > time.time() else None
    except Exception: return None
def hash_phone(phone): return hmac.new(_key(), ("phone:" + phone).encode(), hashlib.sha256).hexdigest()
def hash_otp(phone, code): return hmac.new(_key(), f"otp:{phone}:{code}".encode(), hashlib.sha256).hexdigest()
def new_otp(): return f"{secrets.randbelow(10**6):06d}"
def check_password(pw, stored):  # stored = "salt$hexsha256(pbkdf2)"
    try:
        salt, h = stored.split("$")
        d = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 200_000).hex()
        return hmac.compare_digest(d, h)
    except Exception: return False
