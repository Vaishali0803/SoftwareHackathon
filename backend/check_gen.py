import sys; sys.path.insert(0, ".")
from app.database import SessionLocal, create_tables, GenerationRecord
create_tables()
db = SessionLocal()
recs = db.query(GenerationRecord).filter(GenerationRecord.status=="done").order_by(GenerationRecord.created_at.desc()).limit(3).all()
for r in recs:
    val_path = r.source_for_validation_path
    print(r.id[:16], "|", r.model_used, "| source_for_val:", val_path)
db.close()
