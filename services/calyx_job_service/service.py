# ==============================================================================
# CALYX JOB SERVICE: BUSINESS LOGIC SERVICE LAYER
# ==============================================================================
# Concept Explanation for Beginners:
# 1. MongoDB Document IDs (`_id`):
#    Every document in MongoDB automatically receives an `_id` field. In PyMongo,
#    this is often an `ObjectId('65f1...')`. For clean REST APIs, we convert this
#    `_id` into a standard string named `id`.
#
# 2. Atomic Database Operations (`$inc`):
#    When thousands of candidates apply at the exact same moment during a recruitment
#    drive, incrementing the applicant counter naively (read -> add 1 -> save)
#    causes "Race Conditions" where counts get lost. MongoDB's `$inc` operator
#    guarantees that the counter increments atomically inside the database engine.
#
# 3. Defensive Authorization Checks:
#    A recruiter should only be able to view and edit THEIR OWN jobs. The service
#    layer enforces ownership checks before executing any update or query.
# ==============================================================================

import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status
from services.calyx_job_service.schemas import (
    JobPostingCreate,
    JobPostingUpdate,
    JobApplicationCreate,
    ApplicationEvaluationUpdate,
    JobStatus,
    ApplicationStatus,
)


class JobService:
    """
    Business logic layer for managing jobs and candidate applications.
    """

    @staticmethod
    def _doc_to_dict(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Converts MongoDB internal BSON types into JSON-serializable dictionaries.
        Specifically maps `_id` (ObjectId) to `id` (str).
        """
        if not doc:
            return None
        doc_copy = dict(doc)
        if "_id" in doc_copy:
            doc_copy["id"] = str(doc_copy.pop("_id"))
        return doc_copy

    @classmethod
    def create_job(cls, db, recruiter_id: int, req: JobPostingCreate) -> Dict[str, Any]:
        """
        Creates a new job posting in the MongoDB database.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        
        # Prepare document dictionary from validated Pydantic model
        job_doc = req.model_dump()
        job_doc["recruiter_id"] = recruiter_id
        job_doc["status"] = JobStatus.PUBLISHED.value
        job_doc["total_applicants"] = 0
        job_doc["created_at"] = now_str
        job_doc["updated_at"] = now_str

        # Insert document into MongoDB collection
        result = db.job_postings.insert_one(job_doc)
        job_doc["id"] = str(result.inserted_id)
        if "_id" in job_doc:
            del job_doc["_id"]

        return job_doc

    @classmethod
    def get_job_by_id(cls, db, job_id: str) -> Dict[str, Any]:
        """
        Fetches a single job requisition by its string ID.
        Raises HTTP 404 Not Found if missing.
        """
        query = {}
        try:
            # Attempt to query by BSON ObjectId
            query = {"_id": ObjectId(job_id)}
        except (InvalidId, TypeError, Exception):
            # Fall back to string matching for mock engines
            query = {"_id": job_id}

        doc = db.job_postings.find_one(query)
        if not doc:
            # Also try string query if ObjectId query returned None
            doc = db.job_postings.find_one({"_id": str(job_id)})

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job posting with ID '{job_id}' does not exist."
            )
        return cls._doc_to_dict(doc)

    @classmethod
    def search_jobs(
        cls,
        db,
        keyword: Optional[str] = None,
        department: Optional[str] = None,
        experience_level: Optional[str] = None,
        status_filter: str = JobStatus.PUBLISHED.value,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Filters and searches active job postings with pagination.
        Returns a tuple of (list_of_jobs, total_matching_count).
        """
        filter_query: Dict[str, Any] = {}
        
        # Filter by job lifecycle status
        if status_filter:
            filter_query["status"] = status_filter

        # Filter by exact department match
        if department:
            filter_query["department"] = {"$regex": f"^{re.escape(department)}$", "$options": "i"}

        # Filter by seniority level
        if experience_level:
            filter_query["experience_level"] = experience_level

        # Keyword search across title and description
        if keyword:
            regex_pattern = {"$regex": re.escape(keyword), "$options": "i"}
            filter_query["$or"] = [
                {"title": regex_pattern},
                {"description": regex_pattern},
                {"department": regex_pattern}
            ]

        # Execute count and paginated query
        total_count = db.job_postings.count_documents(filter_query)
        cursor = db.job_postings.find(filter_query).skip(skip).limit(limit).sort("created_at", -1)
        
        jobs = [cls._doc_to_dict(doc) for doc in cursor]
        return jobs, total_count

    @classmethod
    def update_job(
        cls,
        db,
        job_id: str,
        recruiter_id: int,
        req: JobPostingUpdate,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Updates an existing job requisition.
        Enforces that only the owning recruiter (or admin) can modify the job.
        """
        job = cls.get_job_by_id(db, job_id)

        # Ownership verification
        if not is_admin and job["recruiter_id"] != recruiter_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this job posting."
            )

        # Build update dictionary, excluding None values
        update_data = {k: v for k, v in req.model_dump().items() if v is not None}
        if not update_data:
            return job

        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Update in MongoDB
        query = {"_id": ObjectId(job_id)} if ObjectId.is_valid(job_id) else {"_id": job_id}
        db.job_postings.update_one(query, {"$set": update_data})

        return cls.get_job_by_id(db, job_id)

    @classmethod
    def submit_application(cls, db, candidate_id: int, req: JobApplicationCreate) -> Dict[str, Any]:
        """
        Submits a candidate application linked to a job opening and resume document.
        Enforces that candidates cannot apply twice to the same job.
        """
        # Step 1: Verify the job exists and is actively published
        job = cls.get_job_by_id(db, req.job_id)
        if job["status"] != JobStatus.PUBLISHED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This job posting is {job['status']} and is not accepting applications."
            )

        # Step 2: Check for existing duplicate application
        existing_app = db.applications.find_one({
            "job_id": req.job_id,
            "candidate_id": candidate_id
        })
        if existing_app:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already submitted an application for this job posting."
            )

        # Step 3: Construct and insert application document
        now_str = datetime.now(timezone.utc).isoformat()
        app_doc = {
            "job_id": req.job_id,
            "candidate_id": candidate_id,
            "resume_id": req.resume_id,
            "answers": [a.model_dump() for a in req.answers],
            "status": ApplicationStatus.SUBMITTED.value,
            "match_score": None,
            "agent_summary": None,
            "created_at": now_str,
            "updated_at": now_str
        }
        result = db.applications.insert_one(app_doc)
        app_doc["id"] = str(result.inserted_id)
        if "_id" in app_doc:
            del app_doc["_id"]

        # Step 4: Atomically increment total applicant count on the job document
        job_query = {"_id": ObjectId(req.job_id)} if ObjectId.is_valid(req.job_id) else {"_id": req.job_id}
        db.job_postings.update_one(job_query, {"$inc": {"total_applicants": 1}})

        return app_doc

    @classmethod
    def get_applications_for_job(
        cls,
        db,
        job_id: str,
        recruiter_id: int,
        status_filter: Optional[str] = None,
        is_admin: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all candidate applications for a specific job requisition.
        Restricted to the owning recruiter or admin.
        """
        job = cls.get_job_by_id(db, job_id)
        if not is_admin and job["recruiter_id"] != recruiter_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view applicants for this job."
            )

        query: Dict[str, Any] = {"job_id": job_id}
        if status_filter:
            query["status"] = status_filter

        # Sort applications by match_score descending (top AI candidates first)
        cursor = db.applications.find(query).sort("match_score", -1)
        return [cls._doc_to_dict(doc) for doc in cursor]

    @classmethod
    def get_candidate_applications(cls, db, candidate_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all job applications submitted by a specific candidate.
        """
        cursor = db.applications.find({"candidate_id": candidate_id}).sort("created_at", -1)
        return [cls._doc_to_dict(doc) for doc in cursor]

    @classmethod
    def update_application_evaluation(
        cls,
        db,
        application_id: str,
        req: ApplicationEvaluationUpdate
    ) -> Dict[str, Any]:
        """
        Internal method used by the Agentic AI mesh (calyx-agent-service) to record
        the computed semantic match score and multi-agent synthesis critique.
        """
        query = {"_id": ObjectId(application_id)} if ObjectId.is_valid(application_id) else {"_id": application_id}
        app_doc = db.applications.find_one(query)
        if not app_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID '{application_id}' does not exist."
            )

        update_data = {
            "match_score": req.match_score,
            "agent_summary": req.agent_summary,
            "status": req.status.value,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        db.applications.update_one(query, {"$set": update_data})
        updated = db.applications.find_one(query)
        return cls._doc_to_dict(updated)
