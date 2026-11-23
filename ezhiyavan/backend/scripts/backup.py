"""Encrypted database backups.   BACKUP_KEY=<Fernet key> python scripts/backup.py backup|restore <file> [--db sqlite:///x.db] [--keep 14]
SQLite: online-consistent copy via the sqlite3 backup API, then Fernet-encrypted (tested).
PostgreSQL: pipes `pg_dump` through the same encryption (NOT tested here). Store backups off-host and test restores regularly."""
import os, sys, sqlite3, subprocess, tempfile, datetime as dt, glob
from cryptography.fernet import Fernet

def _f(): return Fernet(os.environ["BACKUP_KEY"].encode())

def backup_sqlite(db_path, out_dir, keep=14):
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tp = os.path.join(tmp, "snap.db"); src = sqlite3.connect(db_path); dst = sqlite3.connect(tp); src.backup(dst); dst.close(); src.close()
        blob = _f().encrypt(open(tp, "rb").read())
    out = os.path.join(out_dir, "ezhiyavan-" + dt.datetime.utcnow().strftime("%Y%m%dT%H%M%S") + ".db.enc")
    with open(out, "wb") as fh: fh.write(blob)
    for old in sorted(glob.glob(os.path.join(out_dir, "ezhiyavan-*.db.enc")))[:-keep]: os.remove(old)
    return out

def restore_sqlite(enc_file, db_path):
    open(db_path, "wb").write(_f().decrypt(open(enc_file, "rb").read())); return db_path

def backup_postgres(url, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    dump = subprocess.run(["pg_dump", "--format=custom", url], check=True, capture_output=True).stdout
    out = os.path.join(out_dir, "ezhiyavan-" + dt.datetime.utcnow().strftime("%Y%m%dT%H%M%S") + ".pgdump.enc")
    open(out, "wb").write(_f().encrypt(dump)); return out

if __name__ == "__main__":
    cmd, arg = sys.argv[1], sys.argv[2]; db = os.getenv("DATABASE_URL", "sqlite:///./ezhiyavan.db")
    if cmd == "backup": print(backup_sqlite(db.replace("sqlite:///", ""), arg) if db.startswith("sqlite") else backup_postgres(db, arg))
    elif cmd == "restore": print(restore_sqlite(arg, db.replace("sqlite:///", "")))
