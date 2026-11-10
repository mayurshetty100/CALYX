# ==============================================================================
# CALYX JOB SERVICE: PYDANTIC DATA VALIDATION SCHEMAS
# ==============================================================================
# Concept Explanation for Beginners:
# In NoSQL databases like MongoDB, documents don't have rigid tables enforced by
# the database engine. This flexibility is powerful, but if you're not careful,
# bad data can corrupt your system.
# Pydantic acts as the "Gatekeeper" at the API layer. Every piece of data entering
# or leaving our microservice is strictly validated against these Python schemas.
# ==============================================================================

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class JobStatus(str, Enum):
    """Lifecycle statuses of a job requisition."""
    DRAFT = "draft"          # Job created by recruiter but not visible to candidates
    PUBLISHED = "published"  # Active and accepting candidate applications
    CLOSED = "closed"        # Hiring complete; no new applications accepted
    ARCHIVED = "archived"    # Soft-deleted record for historical reporting


class EmploymentType(str, Enum):
    """Type of employment contract."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"


class ExperienceLevel(str, Enum):
    """Seniority level expected for the position."""
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"


class ApplicationStatus(str, Enum):
    """Progression state of a candidate's job application."""
    SUBMITTED = "submitted"              # Application received, awaiting AI parsing
    SCREENING = "screening"              # Currently being processed by Agentic AI mesh
    AGENT_EVALUATED = "agent_evaluated"  # Scored and analyzed by multi-agent consensus
    INTERVIEWING = "interviewing"        # Moved to human or AI technical interview round
    OFFERED = "offered"                  # Job offer extended
    REJECTED = "rejected"                # Candidate rejected


class SkillRequirement(BaseModel):
    """
    Structured skill requirement with importance weighting.
    Used by the Agentic AI service to compute semantic rubric matches.
    """
    name: str = Field(..., description="Name of the skill, e.g. 'Kubernetes', 'Python', 'FastAPI'")
    weight: float = Field(default=1.0, ge=0.1, le=1.0, description="Importance multiplier from 0.1 to 1.0")
    required: bool = Field(default=True, description="Whether this skill is a mandatory hard requirement")


class RubricCriteria(BaseModel):
    """
    Scoring rubric category evaluated by the AI Criteria Matching Agent.
    """
    category: str = Field(..., description="Category name, e.g. 'System Design', 'Concurrency', 'Leadership'")
    weight: float = Field(default=0.25, ge=0.0, le=1.0, description="Relative weight in final composite score")
    description: str = Field(..., description="Guideline for evaluating this criterion")


class ScreeningQuestion(BaseModel):
    """
    Custom question specified by recruiter for candidates to answer during application.
    """
    question_id: str = Field(..., description="Unique question identifier, e.g. 'q1'")
    question_text: str = Field(..., description="Question prompt shown to applicant")
    required: bool = Field(default=True, description="Whether an answer is required to submit")


class CandidateAnswer(BaseModel):
    """
    Candidate's submitted response to a screening question.
    """
    question_id: str = Field(..., description="Reference to question_id")
    answer_text: str = Field(..., description="Candidate's typed response")


class JobPostingCreate(BaseModel):
    """
    Request schema for recruiters creating a new job opening.
    """
    title: str = Field(..., min_length=3, max_length=150, description="Job title, e.g. 'Senior Cloud Engineer'")
    department: str = Field(..., description="Organizational unit, e.g. 'Engineering', 'DevOps'")
    location: str = Field(default="Remote", description="Job location or 'Remote'")
    employment_type: EmploymentType = Field(default=EmploymentType.FULL_TIME)
    experience_level: ExperienceLevel = Field(default=ExperienceLevel.MID)
    min_years_exp: int = Field(default=3, ge=0, description="Minimum years of professional experience")
    max_years_exp: Optional[int] = Field(default=None, description="Maximum years of experience, or None")
    salary_min: Optional[float] = Field(default=None, ge=0, description="Minimum base salary")
    salary_max: Optional[float] = Field(default=None, ge=0, description="Maximum base salary")
    salary_currency: str = Field(default="USD", max_length=3, description="Currency code (USD, EUR, INR)")
    description: str = Field(..., min_length=20, description="Full job description and company overview")
    required_skills: List[SkillRequirement] = Field(..., min_length=1, description="List of required technical skills")
    nice_to_have_skills: List[str] = Field(default=[], description="Secondary skills that give bonus points")
    rubric_criteria: List[RubricCriteria] = Field(default=[], description="Agent evaluation rubric guidelines")
    screening_questions: List[ScreeningQuestion] = Field(default=[], description="Custom application questions")


class JobPostingUpdate(BaseModel):
    """
    Request schema for updating an existing job requisition.
    All fields are optional to support partial updates (PATCH / PUT).
    """
    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[EmploymentType] = None
    experience_level: Optional[ExperienceLevel] = None
    min_years_exp: Optional[int] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    description: Optional[str] = None
    status: Optional[JobStatus] = None


class JobPostingResponse(BaseModel):
    """
    Response schema returning complete job posting details.
    """
    id: str = Field(..., description="Unique MongoDB string ID")
    recruiter_id: int = Field(..., description="User ID of the recruiter who posted this job")
    title: str
    department: str
    location: str
    employment_type: str
    experience_level: str
    min_years_exp: int
    max_years_exp: Optional[int] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str
    description: str
    required_skills: List[SkillRequirement]
    nice_to_have_skills: List[str]
    rubric_criteria: List[RubricCriteria]
    screening_questions: List[ScreeningQuestion]
    status: str
    total_applicants: int = Field(default=0, description="Current number of candidates who applied")
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class JobApplicationCreate(BaseModel):
    """
    Request schema for a candidate applying to an open job requisition.
    """
    job_id: str = Field(..., description="MongoDB string ID of the job posting")
    resume_id: str = Field(..., description="Unique resume identifier generated by calyx-resume-service")
    answers: List[CandidateAnswer] = Field(default=[], description="Answers to custom screening questions")


class JobApplicationResponse(BaseModel):
    """
    Response schema representing a candidate's application record.
    """
    id: str = Field(..., description="Unique application document ID")
    job_id: str = Field(..., description="Referenced job ID")
    candidate_id: int = Field(..., description="User ID of the applying candidate")
    resume_id: str = Field(..., description="Associated resume document ID")
    answers: List[CandidateAnswer]
    status: str = Field(..., description="Application stage (submitted, screening, agent_evaluated, etc.)")
    match_score: Optional[float] = Field(default=None, description="Composite score (0-100) computed by AI agents")
    agent_summary: Optional[str] = Field(default=None, description="Executive synthesis critique from Agentic AI mesh")
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class ApplicationEvaluationUpdate(BaseModel):
    """
    Internal request schema used by calyx-agent-service to record AI evaluation results.
    """
    match_score: float = Field(..., ge=0.0, le=100.0, description="Overall match percentage from 0.0 to 100.0")
    agent_summary: str = Field(..., description="Detailed AI reasoning and evaluation breakdown")
    status: ApplicationStatus = Field(default=ApplicationStatus.AGENT_EVALUATED)
