"""
migrate.py
──────────
One-time safe migration script.
Adds new columns to existing tables without destroying data.
Run ONCE after pulling the enhanced version:

    python migrate.py
"""

import sqlite3
import os

# Path to the SQLite database (matches app.py config)
DB_PATH = os.path.join("instance", "database_new3.db")

def run():
    if not os.path.exists(DB_PATH):
        print(f"[migrate] Database not found at {DB_PATH}")
        print("[migrate] It will be created fresh when you start app.py — no migration needed.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # ── 1. Add AI-verification columns to challenge_submissions ──
    new_columns = [
        ("ai_status",      "TEXT"),
        ("ai_confidence",  "REAL"),
        ("ai_explanation", "TEXT"),
    ]
    for col, coltype in new_columns:
        try:
            cur.execute(f"ALTER TABLE challenge_submissions ADD COLUMN {col} {coltype}")
            print(f"[migrate] ✅ Added column: challenge_submissions.{col}")
        except sqlite3.OperationalError:
            print(f"[migrate] ⏭  Column already exists: challenge_submissions.{col}")

    conn.commit()
    conn.close()

    print("\n[migrate] ✅ Migration complete.")
    print("[migrate] The 'dynamic_quiz_attempts' table will be auto-created by db.create_all() when app.py starts.")

if __name__ == "__main__":
    run()
