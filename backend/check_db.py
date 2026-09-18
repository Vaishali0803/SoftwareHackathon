import sys; sys.path.insert(0, ".")
from app.database import SessionLocal, create_tables, GenerationRecord
create_tables()
db = SessionLocal()
recs = db.query(GenerationRecord).order_by(GenerationRecord.created_at.desc()).limit(5).all()
for r in recs:
    print(r.id[:16], "|", r.status, "|", r.progress, "|", r.progress_message, "|", repr(r.error_message))
db.close()
