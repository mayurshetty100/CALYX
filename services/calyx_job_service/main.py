# ==============================================================================
# CALYX JOB SERVICE: FASTAPI APPLICATION ENTRYPOINT & API ROUTES
# ==============================================================================
# Concept Explanation for Beginners:
# 1. Stateless Microservice Security:
#    Notice how `calyx-job-service` does NOT make a slow HTTP call to the Auth service
#    or query the PostgreSQL database just to verify if a user is logged in!
#    Instead, it decodes and verifies the cryptographically signed JWT token locally
#    using the shared secret key. This is the cornerstone of high-throughput microservices.
#
# 2. Role-Based Access Control (RBAC):
#    - Candidates can view jobs and submit applications.
#    - Recruiters can create jobs and review applicant pools.
#    The `require_role()` dependency automatically validates permissions before
#    allowing a request to proceed.
# ==============================================================================

from contextlib import asynccontextmanager
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, Request, Header, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Shared kernel imports
from common.responses import StandardResponse, StandardErrorResponse, ErrorDetail
from common.logging_config import configure_logger
from common.security import decode_and_verify_token

# Internal job service imports
from services.calyx_job_service.config import job_settings
from services.calyx_job_service.database import init_db, get_job_database
from services.calyx_job_service.schemas import (
    JobPostingCreate,
    JobPostingUpdate,
    JobPostingResponse,
    JobApplicationCreate,
    JobApplicationResponse,
    ApplicationEvaluationUpdate,
    JobStatus,
)
from services.calyx_job_service.service import JobService

# Initialize structured logger
logger = configure_logger(job_settings.SERVICE_NAME, job_settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan context manager:
    Initializes database connections and indexes upon startup.
    """
    logger.info("Initializing CALYX Job Service database and indexes...")
    init_db()
    logger.info("Job Service database ready.")
    yield
    logger.info("Shutting down CALYX Job Service...")


# Initialize FastAPI application
app = FastAPI(
    title="CALYX Job & Application Service",
    description="Microservice managing job postings, hiring rubrics, and candidate application lifecycles.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend UI communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------
# GLOBAL EXCEPTION HANDLER
# ------------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Ensures all error responses adhere to the standard envelope.
    """
    error_payload = StandardErrorResponse(
        success=False,
        error=ErrorDetail(
            code=f"HTTP_{exc.status_code}",
            message=str(exc.detail)
        )
    )
    return JSONResponse(status_code=exc.status_code, content=error_payload.model_dump())


# ------------------------------------------------------------------------------
# SECURITY & RBAC DEPENDENCIES
# ------------------------------------------------------------------------------
def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Decodes the JWT Bearer token and returns the caller's claims dictionary.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected 'Bearer <token>'"
        )
    token_str = authorization.split(" ")[1]
    try:
        payload = decode_and_verify_token(
            token_str,
            secret_key=job_settings.JWT_SECRET_KEY,
            algorithm=job_settings.JWT_ALGORITHM
        )
        return {
            "user_id": int(payload.get("sub")),
            "role": payload.get("role", "candidate"),
            "email": payload.get("email")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}"
        )


def require_recruiter(user: dict = Depends(get_current_user)) -> dict:
    """
    Restricts endpoint access strictly to Recruiters or Admins.
    """
    if user["role"] not in ["recruiter", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: This action requires Recruiter privileges."
        )
    return user


def require_candidate(user: dict = Depends(get_current_user)) -> dict:
    """
    Restricts endpoint access to Candidates or Admins.
    """
    if user["role"] not in ["candidate", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: This action requires Candidate privileges."
        )
    return user


# ------------------------------------------------------------------------------
# KUBERNETES PROBES
# ------------------------------------------------------------------------------
@app.get("/health/live", tags=["Health & Monitoring"])
def liveness_probe():
    """
    Kubernetes Liveness Probe. Returns HTTP 200 if container process is running.
    """
    return {"status": "alive", "service": job_settings.SERVICE_NAME}


@app.get("/health/ready", tags=["Health & Monitoring"])
def readiness_probe(db=Depends(get_job_database)):
    """
    Kubernetes Readiness Probe.
    Tests MongoDB connectivity. Returns HTTP 503 if datastore is unavailable.
    """
    try:
        # Check that collection is accessible
        db.job_postings.find_one({})
        return {"status": "ready", "database": "connected", "service": job_settings.SERVICE_NAME}
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MongoDB datastore connectivity failure"
        )


# ------------------------------------------------------------------------------
# JOB POSTING API ROUTES
# ------------------------------------------------------------------------------
@app.post("/api/v1/jobs", response_model=StandardResponse, status_code=status.HTTP_201_CREATED, tags=["Jobs"])
def create_job_posting(
    req: JobPostingCreate,
    user: dict = Depends(require_recruiter),
    db=Depends(get_job_database)
):
    """
    Create a new job requisition with skills and rubrics. Restricted to recruiters.
    """
    job = JobService.create_job(db=db, recruiter_id=user["user_id"], req=req)
    return StandardResponse(
        success=True,
        message="Job posting created successfully.",
        data=job
    )


@app.get("/api/v1/jobs", response_model=StandardResponse, tags=["Jobs"])
def list_and_search_jobs(
    keyword: Optional[str] = Query(None, description="Search term for title or description"),
    department: Optional[str] = Query(None, description="Filter by department"),
    experience_level: Optional[str] = Query(None, description="Filter by seniority level"),
    status: str = Query(JobStatus.PUBLISHED.value, description="Job status filter"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Limit of results per page"),
    db=Depends(get_job_database)
):
    """
    Public endpoint to search and filter active job openings.
    """
    jobs, total = JobService.search_jobs(
        db=db,
        keyword=keyword,
        department=department,
        experience_level=experience_level,
        status_filter=status,
        skip=skip,
        limit=limit
    )
    return StandardResponse(
        success=True,
        message=f"Found {len(jobs)} jobs (total: {total}).",
        data={"jobs": jobs, "total": total, "skip": skip, "limit": limit}
    )


@app.get("/api/v1/jobs/{job_id}", response_model=StandardResponse, tags=["Jobs"])
def get_job_details(
    job_id: str,
    db=Depends(get_job_database)
):
    """
    Fetch complete details of a specific job requisition.
    """
    job = JobService.get_job_by_id(db=db, job_id=job_id)
    return StandardResponse(
        success=True,
        message="Job details retrieved.",
        data=job
    )


@app.put("/api/v1/jobs/{job_id}", response_model=StandardResponse, tags=["Jobs"])
def update_job_details(
    job_id: str,
    req: JobPostingUpdate,
    user: dict = Depends(require_recruiter),
    db=Depends(get_job_database)
):
    """
    Update an existing job posting. Only the owning recruiter or admin may update.
    """
    is_admin = user["role"] == "admin"
    updated_job = JobService.update_job(
        db=db,
        job_id=job_id,
        recruiter_id=user["user_id"],
        req=req,
        is_admin=is_admin
    )
    return StandardResponse(
        success=True,
        message="Job posting updated successfully.",
        data=updated_job
    )


# ------------------------------------------------------------------------------
# CANDIDATE APPLICATION ROUTES
# ------------------------------------------------------------------------------
@app.post("/api/v1/jobs/{job_id}/apply", response_model=StandardResponse, status_code=status.HTTP_201_CREATED, tags=["Applications"])
def apply_for_job(
    job_id: str,
    req: JobApplicationCreate,
    user: dict = Depends(require_candidate),
    db=Depends(get_job_database)
):
    """
    Submit an application for a published job. Restricted to candidates.
    """
    # Enforce path job_id consistency with body job_id
    req.job_id = job_id
    application = JobService.submit_application(
        db=db,
        candidate_id=user["user_id"],
        req=req
    )
    return StandardResponse(
        success=True,
        message="Application submitted successfully. Queued for AI screening.",
        data=application
    )


@app.get("/api/v1/jobs/{job_id}/applications", response_model=StandardResponse, tags=["Applications"])
def get_job_applications(
    job_id: str,
    status: Optional[str] = Query(None, description="Optional application status filter"),
    user: dict = Depends(require_recruiter),
    db=Depends(get_job_database)
):
    """
    View candidate pipeline for a job. Restricted to the owning recruiter.
    Results are pre-sorted by match_score descending.
    """
    is_admin = user["role"] == "admin"
    applications = JobService.get_applications_for_job(
        db=db,
        job_id=job_id,
        recruiter_id=user["user_id"],
        status_filter=status,
        is_admin=is_admin
    )
    return StandardResponse(
        success=True,
        message=f"Retrieved {len(applications)} applications for job {job_id}.",
        data=applications
    )


@app.get("/api/v1/applications/me", response_model=StandardResponse, tags=["Applications"])
def get_my_applications(
    user: dict = Depends(require_candidate),
    db=Depends(get_job_database)
):
    """
    List all job applications submitted by the currently logged-in candidate.
    """
    apps = JobService.get_candidate_applications(db=db, candidate_id=user["user_id"])
    return StandardResponse(
        success=True,
        message=f"Retrieved {len(apps)} applications.",
        data=apps
    )


@app.patch("/api/v1/applications/{application_id}/evaluation", response_model=StandardResponse, tags=["Internal AI Integration"])
def update_application_evaluation_result(
    application_id: str,
    req: ApplicationEvaluationUpdate,
    db=Depends(get_job_database)
):
    """
    Internal endpoint called by the Agentic AI Orchestrator (calyx-agent-service)
    to persist the semantic rubric match score and multi-agent critique.
    """
    updated_app = JobService.update_application_evaluation(
        db=db,
        application_id=application_id,
        req=req
    )
    return StandardResponse(
        success=True,
        message="Application evaluation updated by AI Agent.",
        data=updated_app
    )


# Local development server entrypoint
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.calyx_job_service.main:app", host="0.0.0.0", port=job_settings.PORT, reload=True)
