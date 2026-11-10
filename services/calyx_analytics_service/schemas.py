# ==============================================================================
# CALYX ANALYTICS SERVICE: PYDANTIC DATA VALIDATION SCHEMAS
# ==============================================================================
# Concept Explanation for Beginners:
# These schemas format analytical metrics, histogram distributions, and pipeline
# event ingestions for recruiter dashboards.
# ==============================================================================

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class PipelineEventCreate(BaseModel):
    """
    Schema for ingesting a pipeline lifecycle event.
    """
    event_type: str = Field(..., description="Action code: APPLICATION_SUBMITTED, AGENT_EVALUATION_COMPLETED, etc.")
    entity_id: str = Field(..., description="Unique application ID or job ID")
    user_id: Optional[int] = Field(default=None, description="Optional user ID associated with event")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="JSON dictionary of diagnostic metrics")


class PipelineEventResponse(BaseModel):
    """
    Schema representing an immutable logged event.
    """
    id: int
    event_type: str
    entity_id: str
    user_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardOverviewResponse(BaseModel):
    """
    Executive dashboard metrics summary.
    """
    total_events_recorded: int
    total_applications_evaluated: int
    average_pipeline_score: float
    status_funnel: Dict[str, int]
    recent_activity: List[PipelineEventResponse]


class JobDistributionResponse(BaseModel):
    """
    Candidate scoring histogram and breakdown for a specific job opening.
    """
    job_id: str
    total_applicants: int
    average_score: float
    highest_score: float
    lowest_score: float
    score_brackets: Dict[str, int] = Field(
        description="Distribution buckets: top_tier (>=85), strong (70-84), average (50-69), below_50 (<50)"
    )
