# ==============================================================================
# CALYX ANALYTICS SERVICE: DATABASE CONNECTION & SESSION FACTORY
# ==============================================================================
# Concept Explanation for Beginners:
# Dedicated database for analytics events, pipeline metric rollups, and reporting.
# Uses SQLAlchemy ORM with connection pooling.
# ==============================================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator
from services.calyx_analytics_service.config import analytics_settings

is_sqlite = analytics_settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    analytics_settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_analytics_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding an independent database session per request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
