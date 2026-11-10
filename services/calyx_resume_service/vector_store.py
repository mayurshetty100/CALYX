# ==============================================================================
# CALYX RESUME SERVICE: HIGH-PERFORMANCE VECTOR DATABASE ENGINE
# ==============================================================================
# Concept Explanation for Beginners:
# 1. Why a Dedicated Vector Database?
#    In modern AI systems, text search is NOT done with SQL "LIKE %keyword%".
#    Instead, every candidate's profile is stored as a 384-dimensional vector point
#    in a vector database.
#
# 2. Approximate Nearest Neighbor (ANN) & Cosine Distance:
#    When a recruiter uploads a job description, we convert that job description
#    into a query vector. The Vector Database measures the spatial angle (Cosine
#    Distance) between the job vector and thousands of candidate vectors to
#    retrieve the closest matching candidates in milliseconds!
#
# 3. Persistence:
#    The vector store keeps vector matrices in memory for microsecond lookups,
#    and synchronizes metadata and vector checkpoints to disk.
# ==============================================================================

import os
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from common.logging_config import configure_logger
from services.calyx_resume_service.config import resume_settings
from services.calyx_resume_service.embeddings import EmbeddingEngine

logger = configure_logger(resume_settings.SERVICE_NAME, resume_settings.LOG_LEVEL)


class VectorStore:
    """
    Dedicated in-memory and disk-persisted Vector Database for candidate resumes.
    """

    def __init__(self, storage_dir: str = resume_settings.VECTOR_STORAGE_DIR):
        self.storage_dir = storage_dir
        # In-memory mapping: resume_id -> metadata dictionary
        self.metadata_store: Dict[str, Dict[str, Any]] = {}
        # In-memory mapping: resume_id -> 384-dim numpy vector
        self.vector_store: Dict[str, np.ndarray] = {}

        # Ensure storage directory exists
        os.makedirs(self.storage_dir, exist_ok=True)
        self.meta_file = os.path.join(self.storage_dir, "resume_metadata.json")
        self.vectors_file = os.path.join(self.storage_dir, "resume_vectors.npz")
        
        # Load any existing persisted data from disk
        self._load_from_disk()

    def _load_from_disk(self):
        """
        Loads saved metadata and vector arrays from disk into memory.
        """
        try:
            if os.path.exists(self.meta_file):
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    self.metadata_store = json.load(f)

            if os.path.exists(self.vectors_file):
                npz = np.load(self.vectors_file)
                for resume_id in npz.files:
                    self.vector_store[resume_id] = npz[resume_id]

            logger.info(f"Loaded {len(self.metadata_store)} records from Vector Database storage.")
        except Exception as e:
            logger.warning(f"Could not load previous vector store snapshot: {str(e)}")

    def _persist_to_disk(self):
        """
        Flushes in-memory metadata and vector checkpoints to disk.
        """
        try:
            with open(self.meta_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata_store, f, indent=2)

            if self.vector_store:
                np.savez(self.vectors_file, **self.vector_store)
        except Exception as e:
            logger.error(f"Failed to persist Vector Database to disk: {str(e)}")

    def add_resume(
        self,
        resume_id: str,
        candidate_id: int,
        vector: np.ndarray,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Inserts a new candidate vector embedding and associated metadata into the index.
        """
        # Store unit-normalized vector
        norm = np.linalg.norm(vector)
        unit_vec = (vector / norm).astype(np.float32) if norm > 0 else vector.astype(np.float32)
        
        self.vector_store[resume_id] = unit_vec
        
        # Record metadata
        meta_record = dict(metadata)
        meta_record["resume_id"] = resume_id
        meta_record["candidate_id"] = candidate_id
        self.metadata_store[resume_id] = meta_record

        # Persist update
        self._persist_to_disk()
        logger.info(f"Indexed resume ID: {resume_id} for candidate ID: {candidate_id}")

    def get_resume(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves resume metadata by ID.
        """
        return self.metadata_store.get(resume_id)

    def list_resumes_by_candidate(self, candidate_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all resumes indexed for a specific candidate ID.
        """
        return [
            meta for meta in self.metadata_store.values()
            if meta.get("candidate_id") == candidate_id
        ]

    def search_similar_candidates(
        self,
        query_vector: np.ndarray,
        required_skills: Optional[List[str]] = None,
        min_experience_years: int = 0,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Performs Cosine Similarity vector search across all indexed candidate resumes.
        Applies skill overlap scoring bonuses and returns the top-k highest matches.
        """
        if not self.vector_store:
            return []

        results = []
        required_skills_lower = [s.lower() for s in (required_skills or [])]

        # Iterate over all stored candidate vectors
        for resume_id, candidate_vec in self.vector_store.items():
            meta = self.metadata_store.get(resume_id, {})
            
            # Check experience constraint
            cand_exp = meta.get("experience_years", 0)
            if cand_exp < min_experience_years:
                continue

            # Compute pure semantic cosine similarity (0.0 to 1.0)
            semantic_sim = EmbeddingEngine.compute_cosine_similarity(query_vector, candidate_vec)

            # Calculate exact skill overlap bonus
            cand_skills_lower = [s.lower() for s in meta.get("skills", [])]
            matched_skills = []
            missing_skills = []

            for req_skill in required_skills_lower:
                if req_skill in cand_skills_lower:
                    matched_skills.append(req_skill.title())
                else:
                    missing_skills.append(req_skill.title())

            # Skill match ratio (fraction of required skills matched)
            skill_score = 1.0
            if required_skills_lower:
                skill_score = len(matched_skills) / len(required_skills_lower)

            # Calibrate semantic similarity (scaling sparse projection to 0.0 - 1.0 range)
            calibrated_semantic = min(1.0, semantic_sim * 2.5)

            # Composite match percentage: 50% calibrated semantic + 50% exact skill overlap
            composite_score = (0.50 * calibrated_semantic) + (0.50 * skill_score)
            match_percentage = round(composite_score * 100.0, 1)

            results.append({
                "resume_id": resume_id,
                "candidate_id": meta.get("candidate_id"),
                "candidate_name": meta.get("candidate_name"),
                "email": meta.get("email"),
                "match_score": match_percentage,
                "semantic_similarity": round(semantic_sim * 100.0, 1),
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "total_skills": meta.get("skills", []),
                "experience_years": cand_exp,
                "education": meta.get("education", [])
            })

        # Sort candidate matches by match_score in descending order (highest score first)
        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results[:top_k]

    def count(self) -> int:
        """Returns total number of indexed vectors."""
        return len(self.vector_store)


# Global singleton instance of the VectorStore
vector_db = VectorStore()


def get_vector_db() -> VectorStore:
    """FastAPI dependency yielding the vector database singleton."""
    return vector_db
