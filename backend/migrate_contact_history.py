
import sqlite3
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).resolve().parent
DB_FILE = ROOT / "data" / "urct.db"

if not DB_FILE.exists():
    raise SystemExit("Database file not found.")

backup_dir = ROOT.parent / "backups" / "database"
backup_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = backup_dir / f"urct_before_contact_{timestamp}.db"

with sqlite3.connect(DB_FILE) as source:
    with sqlite3.connect(backup_file) as backup:
        source.backup(backup)

print("Backup created:", backup_file)

with sqlite3.connect(DB_FILE) as db:
    db.execute("PRAGMA foreign_keys = ON")

    tables = {
        row[0] for row in db.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table'"
        )
    }

    if not {"contacts", "conversations"}.issubset(tables):
        raise SystemExit(
            "Required tables missing. No migration performed."
        )

    columns = {
        row[1] for row in db.execute(
            "PRAGMA table_info(conversations)"
        )
    }

    try:
        db.execute("BEGIN IMMEDIATE")

        if "contact_id" not in columns:
            db.execute("""
                ALTER TABLE conversations
                ADD COLUMN contact_id VARCHAR(36)
                REFERENCES contacts(id)
                ON DELETE SET NULL
            """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS
            ix_conversations_contact_id
            ON conversations(contact_id)
        """)

        problems = db.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if problems:
            raise RuntimeError(
                f"Foreign key violations: {problems}"
            )

        db.commit()

    except Exception:
        db.rollback()
        raise

print("Migration completed successfully.")

with sqlite3.connect(DB_FILE) as db:
    columns = [
        row[1] for row in db.execute(
            "PRAGMA table_info(conversations)"
        )
    ]

print("Conversation columns:", columns)
