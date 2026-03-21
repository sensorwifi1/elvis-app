from pathlib import Path
import sqlite3
import qrcode

BASE_URL = "http://bar.growiq.pl"
APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "app.db"
OUT_DIR = APP_DIR / "qr_codes"
OUT_DIR.mkdir(exist_ok=True)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT table_number, qr_token FROM table_qr ORDER BY table_number").fetchall()
conn.close()

for row in rows:
    url = f"{BASE_URL}/q/{row['qr_token']}"
    path = OUT_DIR / f"table_{row['table_number']}.png"
    qrcode.make(url).save(path)
    print(f"Saved {path} -> {url}")
