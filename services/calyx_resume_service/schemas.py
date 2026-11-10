# ==============================================================================
# CALYX RESUME SERVICE: PYDANTIC DATA VALIDATION SCHEMAS
# ==============================================================================
# Concept Explanation for Beginners:
# These schemas define the data contracts for resume ingestion, parsed candidate
# intelligence, and vector similarity search results.
# ==============================================================================

from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class ParsedResumeResponse(BaseModel):
    """
    Structured data extracted from an uploaded resume document.
    """
    resume_id: str = Field(..., description="Unique resume identifier")
    candidate_id: int = Field(..., description="User ID of the candidate")
    file_name: str = Field(..., description="Original document file name")
    candidate_name: str = Field(..., description="Detected candidate name")
    email: Optional[str] = Field(default=None, description="Extracted contact email")
    phone: Optional[str] = Field(default=None, description="Extracted phone number")
    skills: List[str] = Field(default=[], description="Detected technical and domain skills")
    experience_years: int = Field(default=0, description="Estimated years of professional experience")
    education: List[str] = Field(default=[], description="Detected academic degrees")
    word_count: int = Field(default=0, description="Total word count in resume")
    character_count: int = Field(default=0, description="Total character count in resume")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(from_attributes=True)


class ResumeUploadTextRequest(BaseModel):
    """
    Schema for uploading resume content directly as raw text or markdown.
    """
    text_content: str = Field(..., min_length=20, description="Raw textual resume content")
    file_name: str = Field(default="resume.txt", description="Document filename")


class ResumeSearchRequest(BaseModel):
    """
    Request schema for performing semantic vector similarity search against candidate resumes.
    """
    job_description: str = Field(..., min_length=10, description="Job description or query text to vectorize")
    required_skills: List[str] = Field(default=[], description="List of required technical skills to match")
    min_experience_years: int = Field(default=0, ge=0, description="Minimum experience threshold")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of top candidates to return")


class CandidateMatchItem(BaseModel):
    """
    Individual candidate match result returned by the vector search engine.
    """
    resume_id: str
    candidate_id: int
    candidate_name: str
    email: Optional[str] = None
    match_score: float = Field(..., description="Overall composite match score (0.0 to 100.0%)")
    semantic_similarity: float = Field(..., description="Pure cosine similarity percentage in vector space")
    matched_skills: List[str] = Field(default=[], description="Required skills candidate possesses")
    missing_skills: List[str] = Field(default=[], description="Required skills candidate lacks")
    total_skills: List[str] = Field(default=[], description="Complete list of candidate's skills")
    experience_years: int
    education: List[str] = Field(default=[])


class ResumeSearchResponse(BaseModel):
    """
    Response schema returning top matching candidates from vector similarity search.
    """
    total_candidates_indexed: int
    top_matches: List[CandidateMatchItem]
