# ==============================================================================
# CALYX ANALYTICS SERVICE: FASTAPI APPLICATION ENTRYPOINT & API ROUTES
# ==============================================================================
# Concept Explanation for Beginners:
# The Analytics Service provides real-time hiring metrics, conversion funnels,
# and score histograms.
# Endpoints are optimized for fast dashboard rendering using materialized aggregates.
# ==============================================================================

from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Request, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

# Shared kernel imports
from common.responses import StandardResponse, StandardErrorResponse, ErrorDetail
from common.logging_config import configure_logger

# Internal analytics service imports
from services.calyx_analytics_service.config import analytics_settings
from services.calyx_analytics_service.database import engine, Base, get_analytics_db
from services.calyx_analytics_service.schemas import (
    PipelineEventCreate,
    PipelineEventResponse,
    DashboardOverviewResponse,
    JobDistributionResponse,
)
from services.calyx_analytics_service.service import AnalyticsService

logger = configure_logger(analytics_settings.SERVICE_NAME, analytics_settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan context manager:
    Initializes analytics database tables upon startup.
    """
    logger.info("Initializing CALYX Analytics Service database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Analytics database tables verified/created successfully.")
    yield
    logger.info("Shutting down CALYX Analytics Service...")


# Initialize FastAPI application
app = FastAPI(
    title="CALYX Analytics & Reporting Service",
    description="Microservice responsible for ingesting pipeline events, candidate distributions, and executive metrics.",
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
# KUBERNETES PROBES
# ------------------------------------------------------------------------------
@app.get("/health/live", tags=["Health & Monitoring"])
def liveness_probe():
    """Kubernetes Liveness Probe."""
    return {"status": "alive", "service": analytics_settings.SERVICE_NAME}


@app.get("/health/ready", tags=["Health & Monitoring"])
def readiness_probe(db: Session = Depends(get_analytics_db)):
    """Kubernetes Readiness Probe. Verifies Analytics database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected", "service": analytics_settings.SERVICE_NAME}
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics database check failed."
        )


# ------------------------------------------------------------------------------
# ANALYTICS API ROUTES
# ------------------------------------------------------------------------------
@app.post("/api/v1/analytics/events", response_model=StandardResponse, status_code=status.HTTP_201_CREATED, tags=["Pipeline Events"])
def record_event(
    req: PipelineEventCreate,
    db: Session = Depends(get_analytics_db)
):
    """
    Ingests an asynchronous lifecycle event from other microservices
    (e.g. application submission, agent evaluation completion, interview offer).
    """
    event = AnalyticsService.record_pipeline_event(db=db, req=req)
    return StandardResponse(
        success=True,
        message="Pipeline event recorded successfully.",
        data=PipelineEventResponse.model_validate(event).model_dump()
    )


@app.get("/api/v1/analytics/dashboard", response_model=StandardResponse, tags=["Executive Dashboard"])
def get_dashboard_overview(db: Session = Depends(get_analytics_db)):
    """
    Retrieves global executive recruitment metrics: total events, pipeline funnel counts,
    and average candidate scores.
    """
    overview = AnalyticsService.get_dashboard_overview(db=db)
    return StandardResponse(
        success=True,
        message="Dashboard overview metrics retrieved.",
        data=overview.model_dump()
    )


@app.get("/api/v1/analytics/jobs/{job_id}/distribution", response_model=StandardResponse, tags=["Job Analytics"])
def get_job_distribution(
    job_id: str,
    db: Session = Depends(get_analytics_db)
):
    """
    Returns score histogram distribution (Top Tier, Strong, Average, Below 50)
    for a specific job requisition.
    """
    dist = AnalyticsService.get_job_distribution(db=db, job_id=job_id)
    return StandardResponse(
        success=True,
        message=f"Score distribution retrieved for job {job_id}.",
        data=dist.model_dump()
    )


# Local development server entrypoint
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.calyx_analytics_service.main:app", host="0.0.0.0", port=analytics_settings.PORT, reload=True)
