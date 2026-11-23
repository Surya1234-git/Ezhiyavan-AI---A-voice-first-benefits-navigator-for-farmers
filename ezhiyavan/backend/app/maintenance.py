"""Retention enforcement. Run daily (cron/systemd timer):  python -m app.maintenance
DOC_RETENTION_DAYS (default 365): uploaded documents older than this are deleted (rows + files).
INACTIVE_RETENTION_DAYS (default 730): farmers with no login for this long are erased entirely.
Expired OTPs and revoked-token records are always cleaned."""
import os, time, datetime as dt
from . import main as m

def purge(now=None, doc_days=None, inactive_days=None):
    now = now or dt.datetime.utcnow()
    doc_days = doc_days if doc_days is not None else int(os.getenv("DOC_RETENTION_DAYS", "365"))
    inactive_days = inactive_days if inactive_days is not None else int(os.getenv("INACTIVE_RETENTION_DAYS", "730"))
    n = {"otps": 0, "revoked": 0, "documents": 0, "farmers": 0}
    with m.Session() as db:
        n["otps"] = db.query(m.Otp).filter(m.Otp.expires < now).delete()
        n["revoked"] = db.query(m.Revoked).filter(m.Revoked.exp < int(now.timestamp())).delete()
        for d in db.query(m.Doc).filter(m.Doc.created_at < now - dt.timedelta(days=doc_days)).all():
            try: os.remove(os.path.join(m.UPLOAD_DIR(), d.farmer_id, d.filename))
            except FileNotFoundError: pass
            db.delete(d); n["documents"] += 1
        db.commit()
        for f in db.query(m.Farmer).filter(m.Farmer.last_active < now - dt.timedelta(days=inactive_days)).all():
            m.erase_farmer(db, f.id); n["farmers"] += 1
    return n

if __name__ == "__main__": print(purge())
