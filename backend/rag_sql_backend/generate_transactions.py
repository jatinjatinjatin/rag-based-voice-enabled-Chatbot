import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "app.db"

ROWS = 100_000   # change to 1_000_000 for 1M rows
BATCH_SIZE = 5000

def main():
    print("⚙️ Connecting to database...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("📦 Creating table if not exists...")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        status TEXT,
        city TEXT,
        created_at TEXT
    )
    """)

    cities = ["Delhi", "Mumbai", "Bangalore", "London", "New York", "Berlin"]
    statuses = ["success", "failed", "pending"]

    start = datetime(2023, 1, 1)
    batch = []

    print(f"🚀 Generating {ROWS:,} rows...")

    for i in range(ROWS):
        dt = start + timedelta(minutes=random.randint(0, 525600))
        batch.append((
            random.randint(1, 5000),
            round(random.uniform(10, 5000), 2),
            random.choice(statuses),
            random.choice(cities),
            dt.isoformat()
        ))

        if len(batch) >= BATCH_SIZE:
            cur.executemany("""
                INSERT INTO transactions (user_id, amount, status, city, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, batch)
            batch.clear()

        if i % 50000 == 0 and i > 0:
            print(f"  → {i:,} rows generated...")

    if batch:
        cur.executemany("""
            INSERT INTO transactions (user_id, amount, status, city, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, batch)

    conn.commit()
    conn.close()

    print(f"✅ Inserted {ROWS:,} rows into transactions table")
    print("🎉 Done!")

if __name__ == "__main__":
    main()
