# ==============================================================================
# CALYX RESUME SERVICE: FASTAPI APPLICATION ENTRYPOINT & API ROUTES
# ==============================================================================
# Concept Explanation for Beginners:
# 1. Asynchronous Document Processing:
#    Handling PDF uploads, text parsing, and vector embeddings can take CPU cycles.
#    FastAPI handles requests asynchronously so concurrent users can upload
#    resumes without blocking each other.
#
# 2. Vector Search Routing:
#    Recruiters search for candidates by passing job descriptions into
#    `POST /api/v1/resumes/search`. The service computes the query embedding and
#    queries the Vector Database for the top-k closest candidate vectors.
# ==============================================================================

from contextlib import asynccontextmanager
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, Request, Header, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Shared kernel imports
from common.responses import StandardResponse, StandardErrorResponse, ErrorDetail
from common.logging_config import configure_logger
from common.security import decode_and_verify_token

# Internal resume service imports
from services.calyx_resume_service.config import resume_settings
from services.calyx_resume_service.vector_store import get_vector_db, VectorStore
from services.calyx_resume_service.schemas import (
    ParsedResumeResponse,
    ResumeUploadTextRequest,
    ResumeSearchRequest,
    ResumeSearchResponse,
)
from services.calyx_resume_service.service import ResumeService

logger = configure_logger(resume_settings.SERVICE_NAME, resume_settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan context manager:
    Initializes vector database store upon startup.
    """
    logger.info("Initializing CALYX Resume Vector Database...")
    db = get_vector_db()
    logger.info(f"Resume Service ready. Currently holding {db.count()} indexed candidate vectors.")
    yield
    logger.info("Shutting down CALYX Resume Service...")


# Initialize FastAPI application
app = FastAPI(
    title="CALYX Resume Intelligence & Vector Search Service",
    description="Microservice responsible for PDF/DOCX parsing, entity extraction, and high-dimensional vector search.",
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
    """Formats all raised HTTP exceptions into unified error envelopes."""
    error_payload = StandardErrorResponse(
        success=False,
        error=ErrorDetail(code=f"HTTP_{exc.status_code}", message=str(exc.detail))
    )
    return JSONResponse(status_code=exc.status_code, content=error_payload.model_dump())


# ------------------------------------------------------------------------------
# SECURITY & RBAC DEPENDENCIES
# ------------------------------------------------------------------------------
def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Decodes JWT Bearer token and returns caller claims."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected 'Bearer <token>'"
        )
    token_str = authorization.split(" ")[1]
    try:
        payload = decode_and_verify_token(
            token_str,
            secret_key=resume_settings.JWT_SECRET_KEY,
            algorithm=resume_settings.JWT_ALGORITHM
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


def require_candidate(user: dict = Depends(get_current_user)) -> dict:
    """Restricts endpoint to Candidates or Admins."""
    if user["role"] not in ["candidate", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only candidates may upload resumes."
        )
    return user


def require_recruiter(user: dict = Depends(get_current_user)) -> dict:
    """Restricts endpoint to Recruiters or Admins."""
    if user["role"] not in ["recruiter", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only recruiters may perform candidate vector searches."
        )
    return user


# ------------------------------------------------------------------------------
# KUBERNETES PROBES
# ------------------------------------------------------------------------------
@app.get("/health/live", tags=["Health & Monitoring"])
def liveness_probe():
    """Kubernetes Liveness Probe."""
    return {"status": "alive", "service": resume_settings.SERVICE_NAME}


@app.get("/health/ready", tags=["Health & Monitoring"])
def readiness_probe(vdb: VectorStore = Depends(get_vector_db)):
    """Kubernetes Readiness Probe. Verifies Vector Database is online."""
    try:
        count = vdb.count()
        return {
            "status": "ready",
            "database": "connected",
            "indexed_vectors": count,
            "service": resume_settings.SERVICE_NAME
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector database storage check failed."
        )


# ------------------------------------------------------------------------------
# RESUME INGESTION & SEARCH API ROUTES
# ------------------------------------------------------------------------------
@app.post("/api/v1/resumes/upload", response_model=StandardResponse, status_code=status.HTTP_201_CREATED, tags=["Resume Ingestion"])
async def upload_resume_file(
    file: UploadFile = File(..., description="Resume document (PDF, DOCX, or TXT)"),
    user: dict = Depends(require_candidate),
    vdb: VectorStore = Depends(get_vector_db)
):
    """
    Upload a resume file. Automatically extracts text, identifies technical skills,
    computes 384-dimensional vector embedding, and indexes in Vector Database.
    """
    file_bytes = await file.read()
    
    # Check file size limit
    max_bytes = resume_settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {resume_settings.MAX_UPLOAD_SIZE_MB} MB."
        )

    parsed_result = ResumeService.process_and_index_resume(
        vector_db=vdb,
        file_bytes=file_bytes,
        filename=file.filename or "resume.pdf",
        candidate_id=user["user_id"]
    )

    return StandardResponse(
        success=True,
        message="Resume successfully uploaded, parsed, and vectorized.",
        data=parsed_result.model_dump()
    )


@app.post("/api/v1/resumes/upload-text", response_model=StandardResponse, status_code=status.HTTP_201_CREATED, tags=["Resume Ingestion"])
def upload_resume_raw_text(
    req: ResumeUploadTextRequest,
    user: dict = Depends(require_candidate),
    vdb: VectorStore = Depends(get_vector_db)
):
    """
    Directly upload resume text content. Extracts entities and generates vector embedding.
    """
    file_bytes = req.text_content.encode("utf-8")
    parsed_result = ResumeService.process_and_index_resume(
        vector_db=vdb,
        file_bytes=file_bytes,
        filename=req.file_name,
        candidate_id=user["user_id"]
    )

    return StandardResponse(
        success=True,
        message="Resume text parsed and indexed successfully.",
        data=parsed_result.model_dump()
    )


@app.get("/api/v1/resumes/{resume_id}", response_model=StandardResponse, tags=["Resume Intelligence"])
def get_resume_by_id(
    resume_id: str,
    vdb: VectorStore = Depends(get_vector_db)
):
    """Retrieve extracted metadata for a specific resume ID."""
    meta = ResumeService.get_resume_by_id(vector_db=vdb, resume_id=resume_id)
    return StandardResponse(
        success=True,
        message="Resume metadata retrieved.",
        data=meta
    )


@app.get("/api/v1/resumes/candidate/me", response_model=StandardResponse, tags=["Resume Intelligence"])
def get_my_resumes(
    user: dict = Depends(require_candidate),
    vdb: VectorStore = Depends(get_vector_db)
):
    """List all resumes uploaded by the currently authenticated candidate."""
    resumes = ResumeService.list_resumes_by_candidate(vector_db=vdb, candidate_id=user["user_id"])
    return StandardResponse(
        success=True,
        message=f"Retrieved {len(resumes)} resumes.",
        data=resumes
    )


@app.post("/api/v1/resumes/search", response_model=StandardResponse, tags=["Vector Search"])
def semantic_vector_search(
    req: ResumeSearchRequest,
    user: dict = Depends(require_recruiter),
    vdb: VectorStore = Depends(get_vector_db)
):
    """
    Semantic Vector Search: Recruiter submits a job description and required skills.
    Engine computes Cosine Similarity in 384-dimensional space and returns ranked candidates.
    """
    search_results = ResumeService.semantic_search(vector_db=vdb, req=req)
    return StandardResponse(
        success=True,
        message=f"Vector search returned {len(search_results.top_matches)} candidate matches.",
        data=search_results.model_dump()
    )


# Local development server entrypoint
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.calyx_resume_service.main:app", host="0.0.0.0", port=resume_settings.PORT, reload=True)
