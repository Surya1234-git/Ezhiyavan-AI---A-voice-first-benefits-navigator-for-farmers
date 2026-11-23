"""Create a ready-made DEMO farmer so a judge sees results in seconds.   Usage:  python backend/scripts/seed_demo.py   (backend running with ENV=dev)
Logs in with the dev OTP, then answers every question: 2 acres, has a bank account, no exclusions. Then open the app, log in with the same phone number.
STATUS: written against the API but NOT run in the build environment (no FastAPI there) - run it once before you rely on it."""
import json, os, sys, urllib.request, urllib.error

BASE = os.getenv("BASE_URL", "http://localhost:8000"); PHONE = os.getenv("DEMO_PHONE", "9876543210")

def call(path, body=None, token=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(), method="POST" if body is not None else "GET",
                                 headers={"Content-Type": "application/json", "X-Requested-With": "ezhiyavan", **({"Authorization": "Bearer " + token} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=15) as r: return json.load(r)
    except urllib.error.HTTPError as e: sys.exit(f"{path} failed: {e.code} {e.read().decode()[:200]}")
    except urllib.error.URLError as e: sys.exit(f"cannot reach {BASE} ({e.reason}). Is the backend running?")

otp = call("/api/auth/request-otp", {"phone": PHONE})
if "dev_code" not in otp: sys.exit("No dev_code returned: start the backend with ENV=dev (demo mode only).")
tok = call("/api/auth/verify-otp", {"phone": PHONE, "code": otp["dev_code"], "consent": True, "language": "ta"}).get("token")
if not tok: sys.exit("No token returned: the backend must run with ENV=dev for seeding.")
while True:
    q = call("/api/me/next-question", token=tok)
    if q.get("done"): break
    kind = q.get("kind"); f = q["field"]
    value = (f == "has_bank_account") if kind == "bool" else (2.0 if kind == "number" else "Tamil Nadu")
    call("/api/me/confirm", {"field": f, "value": value}, tok); print("answered", f, "=", value)
print(f"Demo farmer ready. Open the app and log in with {PHONE} (the OTP appears on screen in demo mode).")
