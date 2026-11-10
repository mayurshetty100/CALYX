# ==============================================================================
# CALYX RESUME SERVICE: BUSINESS LOGIC SERVICE LAYER
# ==============================================================================
# Concept Explanation for Beginners:
# The ResumeService orchestrates:
# 1. Parsing raw PDF/Word document bytes into clean text and extracted skills.
# 2. Transforming the candidate profile into a high-dimensional vector.
# 3. Indexing the vector inside our dedicated Vector Database.
# 4. Running Cosine Similarity search when recruiters want to find the best talent.
# ==============================================================================

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
from services.calyx_resume_service.parser import ResumeParser
from services.calyx_resume_service.embeddings import EmbeddingEngine
from services.calyx_resume_service.vector_store import VectorStore
from services.calyx_resume_service.schemas import (
    ParsedResumeResponse,
    ResumeSearchRequest,
    ResumeSearchResponse,
    CandidateMatchItem,
)


class ResumeService:
    """
    Business logic layer for parsing, vectorizing, and searching candidate resumes.
    """

    @classmethod
    def process_and_index_resume(
        cls,
        vector_db: VectorStore,
        file_bytes: bytes,
        filename: str,
        candidate_id: int
    ) -> ParsedResumeResponse:
        """
        Parses resume bytes, extracts technical skills, computes 384-dim semantic
        vector embedding, and persists the record into the Vector Database.
        """
        # Step 1: Parse document text and extract structured entities
        parsed = ResumeParser.parse_full_resume(file_bytes, filename)
        if not parsed["raw_text"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract readable text from uploaded file. Please ensure document is not an image-only scan."
            )

        # Step 2: Generate unique resume ID
        resume_id = f"res_{uuid.uuid4().hex[:12]}"
        now_str = datetime.now(timezone.utc).isoformat()

        # Step 3: Compute high-dimensional semantic vector embedding
        # We concatenate the candidate's skills and raw text to construct a dense semantic summary
        summary_text = (
            f"Candidate: {parsed['candidate_name']}. "
            f"Skills: {', '.join(parsed['skills'])}. "
            f"Experience: {parsed['experience_years']} years. "
            f"Details: {parsed['raw_text'][:2000]}"
        )
        vector = EmbeddingEngine.generate_embedding(summary_text)

        # Step 4: Index vector and metadata inside Vector Database
        metadata = {
            "resume_id": resume_id,
            "candidate_id": candidate_id,
            "file_name": parsed["file_name"],
            "candidate_name": parsed["candidate_name"],
            "email": parsed["email"],
            "phone": parsed["phone"],
            "skills": parsed["skills"],
            "experience_years": parsed["experience_years"],
            "education": parsed["education"],
            "character_count": parsed["character_count"],
            "word_count": parsed["word_count"],
            "raw_text_preview": parsed["raw_text"][:500],
            "created_at": now_str
        }
        vector_db.add_resume(
            resume_id=resume_id,
            candidate_id=candidate_id,
            vector=vector,
            metadata=metadata
        )

        return ParsedResumeResponse(
            resume_id=resume_id,
            candidate_id=candidate_id,
            file_name=parsed["file_name"],
            candidate_name=parsed["candidate_name"],
            email=parsed["email"],
            phone=parsed["phone"],
            skills=parsed["skills"],
            experience_years=parsed["experience_years"],
            education=parsed["education"],
            word_count=parsed["word_count"],
            character_count=parsed["character_count"],
            created_at=now_str
        )

    @classmethod
    def semantic_search(
        cls,
        vector_db: VectorStore,
        req: ResumeSearchRequest
    ) -> ResumeSearchResponse:
        """
        Translates a job description into a query vector, measures Cosine Distance
        against all candidate resumes, and returns top-k ranked matches.
        """
        # Step 1: Project the job description and required skills into 384-dim query vector
        query_text = (
            f"Job Requirements: {req.job_description}. "
            f"Required Skills: {', '.join(req.required_skills)}"
        )
        query_vector = EmbeddingEngine.generate_embedding(query_text)

        # Step 2: Query the Vector Database using Cosine Similarity
        raw_matches = vector_db.search_similar_candidates(
            query_vector=query_vector,
            required_skills=req.required_skills,
            min_experience_years=req.min_experience_years,
            top_k=req.top_k
        )

        # Step 3: Format results into standardized response
        match_items = [CandidateMatchItem(**item) for item in raw_matches]

        return ResumeSearchResponse(
            total_candidates_indexed=vector_db.count(),
            top_matches=match_items
        )

    @classmethod
    def get_resume_by_id(cls, vector_db: VectorStore, resume_id: str) -> Dict[str, Any]:
        """
        Retrieves parsed resume metadata by ID.
        Raises HTTP 404 if not found.
        """
        meta = vector_db.get_resume(resume_id)
        if not meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resume with ID '{resume_id}' does not exist in Vector Database."
            )
        return meta

    @classmethod
    def list_resumes_by_candidate(
        cls,
        vector_db: VectorStore,
        candidate_id: int
    ) -> List[Dict[str, Any]]:
        """
        Returns all resumes uploaded by a specific candidate.
        """
        return vector_db.list_resumes_by_candidate(candidate_id)
