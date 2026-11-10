# ==============================================================================
# CALYX AGENT SERVICE: FASTAPI APPLICATION ENTRYPOINT & API ROUTES
# ==============================================================================
# Concept Explanation for Beginners:
# The Agent Service coordinates the 4 specialized agents.
# Recruiters or automated pipeline workers invoke `POST /api/v1/agents/evaluate`.
# The service runs the multi-agent loop, persists state to Redis, and provides
# endpoints to inspect the full agent reasoning trace.
# ==============================================================================

from contextlib import asynccontextmanager
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, Request, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Shared kernel imports
from common.responses import StandardResponse, StandardErrorResponse, ErrorDetail
from common.logging_config import configure_logger
from common.security import decode_and_verify_token

# Internal agent service imports
from services.calyx_agent_service.config import agent_settings
from services.calyx_agent_service.state_store import get_state_store, AgentStateStore
from services.calyx_agent_service.schemas import (
    EvaluationRequest,
    EvaluationResponse,
    AgentTraceResponse,
    AgentTraceStep,
)
from services.calyx_agent_service.orchestrator import AgentOrchestrator

logger = configure_logger(agent_settings.SERVICE_NAME, agent_settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan context manager:
    Initializes Redis client and state store upon startup.
    """
    logger.info("Initializing CALYX Agent Service Redis state store...")
    store = get_state_store()
    logger.info("Agent Service ready to execute multi-agent workflows.")
    yield
    logger.info("Shutting down CALYX Agent Service...")


# Initialize FastAPI application
app = FastAPI(
    title="CALYX Agentic AI Orchestration Service",
    description="Microservice coordinating autonomous multi-agent reasoning, bias auditing, and dynamic interview synthesis.",
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
    return {"status": "alive", "service": agent_settings.SERVICE_NAME}


@app.get("/health/ready", tags=["Health & Monitoring"])
def readiness_probe(store: AgentStateStore = Depends(get_state_store)):
    """Kubernetes Readiness Probe. Verifies Redis connection."""
    try:
        is_healthy = store.ping()
        if not is_healthy:
            raise Exception("Redis ping returned False")
        return {
            "status": "ready",
            "database": "connected (Redis)",
            "service": agent_settings.SERVICE_NAME
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis state store connectivity failure."
        )


# ------------------------------------------------------------------------------
# AGENTIC AI EVALUATION API ROUTES
# ------------------------------------------------------------------------------
@app.post("/api/v1/agents/evaluate", response_model=StandardResponse, status_code=status.HTTP_200_OK, tags=["Agentic AI Mesh"])
def evaluate_candidate_application(
    req: EvaluationRequest,
    store: AgentStateStore = Depends(get_state_store)
):
    """
    Dispatches the 4-agent evaluation loop:
    1. Extraction & Normalization Agent standardizes technical competencies.
    2. Criteria Matching Agent grades against custom hiring rubrics.
    3. Bias Audit Agent scrubs demographics and verifies merit-based scoring.
    4. Technical Interview Agent synthesizes customized questions with answer keys.
    """
    evaluation_result = AgentOrchestrator.evaluate_candidate(
        state_store=store,
        application_id=req.application_id,
        candidate_profile=req.candidate_profile,
        job_requirements=req.job_requirements
    )

    return StandardResponse(
        success=True,
        message="Multi-agent evaluation completed successfully.",
        data=evaluation_result
    )


@app.get("/api/v1/agents/tasks/{task_id}", response_model=StandardResponse, tags=["Agentic AI Mesh"])
def get_evaluation_task(
    task_id: str,
    store: AgentStateStore = Depends(get_state_store)
):
    """
    Retrieves evaluation task results from Redis by task ID.
    """
    state = store.get_task_state(task_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation task '{task_id}' not found in Redis state store."
        )

    return StandardResponse(
        success=True,
        message="Task state retrieved from Redis.",
        data=state
    )


@app.get("/api/v1/agents/tasks/{task_id}/trace", response_model=StandardResponse, tags=["Agentic AI Mesh"])
def get_evaluation_reasoning_trace(
    task_id: str,
    store: AgentStateStore = Depends(get_state_store)
):
    """
    Inspects the transparent, step-by-step reasoning trace of all sub-agents.
    Provides complete Explainable AI (XAI) for every hiring decision!
    """
    trace_steps = store.get_full_trace(task_id)
    return StandardResponse(
        success=True,
        message=f"Retrieved {len(trace_steps)} reasoning steps from Redis trace list.",
        data={"task_id": task_id, "steps": trace_steps}
    )


# Local development server entrypoint
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.calyx_agent_service.main:app", host="0.0.0.0", port=agent_settings.PORT, reload=True)
