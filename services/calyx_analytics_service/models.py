# ==============================================================================
# CALYX ANALYTICS SERVICE: RELATIONAL DATABASE MODELS
# ==============================================================================
# Concept Explanation for Beginners:
# 1. Pipeline Events (Event Sourcing):
#    Every major milestone in the hiring funnel (candidate applied, AI agent scored,
#    bias audited, interview scheduled) is captured as an immutable event.
#    This allows recruiters to compute historical conversion rates, time-to-hire,
#    and audit trails.
#
# 2. Materialized Analytics Summaries:
#    Pre-calculating average scores and applicant totals inside summary tables
#    enables executive dashboards to render in under 10 milliseconds without
#    performing expensive table-wide aggregation scans on every page refresh.
# ==============================================================================

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from services.calyx_analytics_service.database import Base


class PipelineEvent(Base):
    """
    SQLAlchemy model recording every hiring workflow event.
    """
    __tablename__ = "pipeline_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(String(100), nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class JobAnalyticsSummary(Base):
    """
    Materialized metric summary for a specific job requisition.
    """
    __tablename__ = "job_analytics_summaries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_id = Column(String(100), unique=True, nullable=False, index=True)
    total_applications = Column(Integer, default=0, nullable=False)
    average_score = Column(Float, default=0.0, nullable=False)
    highest_score = Column(Float, default=0.0, nullable=False)
    lowest_score = Column(Float, default=0.0, nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
