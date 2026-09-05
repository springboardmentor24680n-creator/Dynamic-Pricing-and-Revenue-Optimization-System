import sqlite3
from pathlib import Path

paths = [
    Path("../pricepilot.db").resolve(),
    Path("pricepilot.db").resolve(),
]

for path in paths:
    print("PATH", path)
    if path.exists():
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        try:
            cur.execute("SELECT count(*) FROM products")
            print("COUNT", cur.fetchone()[0])
            cur.execute("SELECT id,name FROM products ORDER BY id LIMIT 10")
            print("SAMPLE", cur.fetchall())
        except Exception as e:
            print("ERROR", e)
        conn.close()
    else:
        print("MISSING")
