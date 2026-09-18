"""Add source_for_validation_path column to generations table."""
import sys; sys.path.insert(0, ".")
import sqlalchemy as sa
from app.database import engine

with engine.connect() as conn:
    try:
        conn.execute(sa.text(
            "ALTER TABLE generations ADD COLUMN source_for_validation_path TEXT"
        ))
        conn.commit()
        print("Migration complete: source_for_validation_path column added.")
    except Exception as e:
        msg = str(e).lower()
        if "duplicate" in msg or "already exists" in msg:
            print("Column already exists — no migration needed.")
        else:
            print(f"Migration error: {e}")
            sys.exit(1)
