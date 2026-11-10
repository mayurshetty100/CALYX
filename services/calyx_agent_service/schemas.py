# ==============================================================================
# CALYX AGENT SERVICE: PYDANTIC DATA VALIDATION SCHEMAS
# ==============================================================================
# Concept Explanation for Beginners:
# These schemas define the data contracts for dispatching multi-agent evaluations,
# inspecting transparent reasoning traces, and retrieving generated questionnaires.
# ==============================================================================

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class EvaluationRequest(BaseModel):
    """
    Request schema for dispatching an autonomous agentic evaluation.
    """
    application_id: str = Field(..., description="Unique job application ID from calyx-job-service")
    candidate_profile: Dict[str, Any] = Field(..., description="Extracted resume data from calyx-resume-service")
    job_requirements: Dict[str, Any] = Field(..., description="Requisition rubrics from calyx-job-service")


class RubricCategoryScore(BaseModel):
    """Score for a specific rubric dimension."""
    category: str
    weight: float
    score: float
    weighted_score: float
    justification: str


class InterviewQuestionItem(BaseModel):
    """Tailored technical interview question synthesized by AI."""
    question_id: str
    focus_area: str
    question_prompt: str
    rationale: str
    ideal_response_key: str
    follow_up_probe: str


class EvaluationResponse(BaseModel):
    """
    Comprehensive multi-agent evaluation output.
    """
    task_id: str
    application_id: str
    candidate_id: Optional[int] = None
    status: str
    final_score: float = Field(..., description="Multi-agent composite score from 0.0 to 100.0%")
    detected_specialty: str
    fairness_audit: Dict[str, Any]
    rubric_breakdown: List[Dict[str, Any]]
    interview_questionnaire: List[InterviewQuestionItem]
    executive_summary: str
    completed_at: str

    model_config = ConfigDict(from_attributes=True)


class AgentTraceStep(BaseModel):
    """A single atomic reasoning step recorded by an autonomous agent."""
    agent: str
    timestamp: str
    thought: str
    action: str
    output: Any


class AgentTraceResponse(BaseModel):
    """Chronological list of all agent reasoning steps for auditing."""
    task_id: str
    steps: List[AgentTraceStep]
