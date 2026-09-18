from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class DatasetRecord(Base):
    __tablename__ = "datasets"
    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    num_rows = Column(Integer)
    num_columns = Column(Integer)
    column_names = Column(Text)  # JSON
    column_types = Column(Text)  # JSON
    missing_counts = Column(Text)  # JSON
    unique_counts = Column(Text)  # JSON
    sensitive_columns = Column(Text)  # JSON
    approved_columns = Column(Text)  # JSON
    preprocessing_summary = Column(Text)  # JSON
    preprocessed_path = Column(String)
    status = Column(String, default="uploaded")  # uploaded | preprocessed | error
    created_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text)


class GenerationRecord(Base):
    __tablename__ = "generations"
    id = Column(String, primary_key=True)
    dataset_id = Column(String, nullable=False)
    model_used = Column(String)
    num_requested = Column(Integer)
    num_generated = Column(Integer)
    cohort_config = Column(Text)  # JSON
    cohort_results = Column(Text)  # JSON
    output_path = Column(String)
    source_for_validation_path = Column(String)  # generation-ready source CSV for validation
    status = Column(String, default="pending")  # pending | training | generating | done | error
    progress = Column(Integer, default=0)
    progress_message = Column(String)
    generation_time_seconds = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)


class ValidationRecord(Base):
    __tablename__ = "validations"
    id = Column(String, primary_key=True)
    generation_id = Column(String, nullable=False)
    dataset_id = Column(String, nullable=False)
    numerical_stats = Column(Text)  # JSON
    categorical_stats = Column(Text)  # JSON
    correlation_stats = Column(Text)  # JSON
    ks_tests = Column(Text)  # JSON
    overall_scores = Column(Text)  # JSON
    created_at = Column(DateTime, default=datetime.utcnow)


class PrivacyRecord(Base):
    __tablename__ = "privacy_checks"
    id = Column(String, primary_key=True)
    generation_id = Column(String, nullable=False)
    dataset_id = Column(String, nullable=False)
    exact_duplicates = Column(Integer, default=0)
    near_duplicates = Column(Integer, default=0)
    risk_level = Column(String)  # Low | Medium | High
    details = Column(Text)  # JSON
    created_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
