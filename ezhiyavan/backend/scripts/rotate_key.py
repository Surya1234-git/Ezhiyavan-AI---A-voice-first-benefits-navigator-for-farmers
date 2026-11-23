"""Re-encrypt every stored document with a new key.   FILE_ENC_KEY="<new>,<old>" python scripts/rotate_key.py <upload_dir>
FILE_ENC_KEY is a comma-separated list, NEWEST FIRST (the app encrypts with the first key and can decrypt with all).
Procedure: 1) deploy with "<new>,<old>"  2) run this script  3) deploy with only "<new>". Back up before running; unreadable files are counted, not changed."""
import os, sys
from cryptography.fernet import Fernet, MultiFernet

def rotate_dir(root, keys_csv):
    mf = MultiFernet([Fernet(k.strip().encode()) for k in keys_csv.split(",") if k.strip()]); done = bad = 0
    for dp, _, fs in os.walk(root):
        for f in fs:
            if not f.endswith(".enc"): continue
            p = os.path.join(dp, f)
            try:
                with open(p, "rb") as fh: new = mf.rotate(fh.read())
            except Exception: bad += 1; continue
            with open(p + ".tmp", "wb") as fh: fh.write(new)
            os.replace(p + ".tmp", p); done += 1
    return {"rotated": done, "failed": bad}

if __name__ == "__main__": print(rotate_dir(sys.argv[1], os.environ["FILE_ENC_KEY"]))
