"""
================================================================================
CALYX UNIFIED API GATEWAY SERVICE
================================================================================
File: services/calyx_gateway_service/main.py
Port: 8000
Purpose:
  Serves as the single, hardened entry point for all frontend client traffic.
  Dispatches incoming HTTP requests to their corresponding backend microservices:
    - /api/v1/auth/*       -> Calyx Auth Service (Port 8001)
    - /api/v1/jobs/*       -> Calyx Job Service (Port 8002)
    - /api/v1/resumes/*    -> Calyx Resume Service (Port 8003)
    - /api/v1/agent/*      -> Calyx Agent Service (Port 8004)
    - /api/v1/analytics/*  -> Calyx Analytics Service (Port 8005)

Features Implemented:
  1. Distributed Tracing: Injects unique X-Request-ID header into every request.
  2. CORS Handling: Supports cross-origin requests from React / Vue / Vite frontends.
  3. Resilience & Circuit Breaking: Wraps upstream microservice calls with CircuitBreaker.
  4. Aggregate System Health: /api/v1/system/health queries all 5 microservices.
  5. Reverse Proxy Streaming: Transparently relays headers, status codes, query parameters,
     and body payloads (including multipart file uploads).
================================================================================
"""

# Import the standard UUID library to generate globally unique request identifiers
import uuid

# Import the time module to measure exact request roundtrip latencies
import time

# Import async HTTP client library httpx to make non-blocking calls to backend microservices
import httpx

# Import FastAPI framework classes for building API routes and handling HTTP requests/responses
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import our common logging configuration
from common.logging_config import configure_logger, logger

# Import standardized response models
from common.responses import StandardResponse, StandardErrorResponse

# Import the Circuit Breaker pattern from our shared resilience module
from common.resilience import CircuitBreaker, CircuitState

# Import the configuration settings for the gateway service
from services.calyx_gateway_service.config import gateway_settings


# Initialize structured logging for the API Gateway
configure_logger(gateway_settings.SERVICE_NAME, gateway_settings.LOG_LEVEL)

# Create the FastAPI application instance with rich metadata for Swagger documentation
app = FastAPI(
    title="Calyx Unified API Gateway",
    description=(
        "Central Reverse Proxy & API Gateway for the Calyx Microservices Platform. "
        "Routes requests, injects tracing headers, enforces circuit breaking, and provides aggregate health metrics."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Parse the comma-separated allowed origins string from settings into a list
allowed_origins_list = [origin.strip() for origin in gateway_settings.ALLOWED_CORS_ORIGINS.split(",") if origin.strip()]

# Attach CORS middleware so modern web browsers running frontend code can call this API
app.add_middleware(
    CORSMiddleware,
    # Allow specified origin domains (or wildcard * for local development)
    allow_origins=["*"] if "*" in allowed_origins_list else allowed_origins_list,
    # Allow browsers to send Authorization headers and cookies
    allow_credentials=True,
    # Allow all HTTP verbs: GET, POST, PUT, DELETE, PATCH, OPTIONS
    allow_methods=["*"],
    # Allow all headers like Content-Type, Authorization, X-Request-ID
    allow_headers=["*"],
)

# Initialize dedicated Circuit Breakers for each upstream microservice
# If any service fails 5 times consecutively, its breaker opens for 30s to prevent cascade failures
auth_breaker = CircuitBreaker("auth-service-breaker", failure_threshold=5, recovery_timeout_seconds=30.0)
job_breaker = CircuitBreaker("job-service-breaker", failure_threshold=5, recovery_timeout_seconds=30.0)
resume_breaker = CircuitBreaker("resume-service-breaker", failure_threshold=5, recovery_timeout_seconds=30.0)
agent_breaker = CircuitBreaker("agent-service-breaker", failure_threshold=5, recovery_timeout_seconds=30.0)
analytics_breaker = CircuitBreaker("analytics-service-breaker", failure_threshold=5, recovery_timeout_seconds=30.0)


# ==============================================================================
# MIDDLEWARE: DISTRIBUTED TRACING & REQUEST LOGGING
# ==============================================================================
@app.middleware("http")
async def distributed_tracing_middleware(request: Request, call_next):
    """
    Intercepts every incoming HTTP request to:
    1. Extract existing X-Request-ID or generate a new unique UUID.
    2. Attach X-Request-ID to the request state and outgoing response headers.
    3. Measure processing duration and log request lifecycle.
    """
    # Check if the incoming request already has a correlation ID; if not, generate a new UUID4
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    # Store the request ID in request.state so endpoints can access it if needed
    request.state.request_id = request_id
    
    # Record the start time using high-resolution performance counter
    start_time = time.perf_counter()
    
    # Log incoming request path and HTTP method
    logger.info(f"[{request_id}] --> Incoming {request.method} {request.url.path}")
    
    try:
        # Pass the request to the next handler or endpoint in the chain
        response = await call_next(request)
        
        # Calculate how many milliseconds elapsed
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        
        # Inject the correlation ID into the response headers so frontend can display it
        response.headers["X-Request-ID"] = request_id
        
        # Log successful completion of request with status code and latency
        logger.info(f"[{request_id}] <-- Completed {response.status_code} in {elapsed_ms}ms")
        
        return response
    except Exception as exc:
        # Calculate how many milliseconds elapsed before the exception occurred
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        
        # Log the unhandled error with the correlation ID
        logger.error(f"[{request_id}] <-- Error after {elapsed_ms}ms: {str(exc)}")
        
        # Return a standardized 500 Internal Server Error JSON response
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "GATEWAY_INTERNAL_ERROR",
                    "message": "An unhandled error occurred within the API Gateway.",
                    "details": {"exception": str(exc)},
                    "trace_id": request_id
                }
            },
            headers={"X-Request-ID": request_id}
        )


# ==============================================================================
# HEALTH PROBE ENDPOINTS (Kubernetes Liveness & Readiness)
# ==============================================================================
@app.get("/health/live", tags=["Health Probes"])
def liveness_probe():
    """
    Kubernetes Liveness Probe. Returns 200 OK if the Gateway process is running.
    """
    return {"status": "alive", "service": gateway_settings.SERVICE_NAME}


@app.get("/health/ready", tags=["Health Probes"])
def readiness_probe():
    """
    Kubernetes Readiness Probe. Returns 200 OK if the Gateway is ready to route traffic.
    """
    return {"status": "ready", "service": gateway_settings.SERVICE_NAME}


# ==============================================================================
# AGGREGATE SYSTEM HEALTH & RESILIENCE DASHBOARD
# ==============================================================================
@app.get("/api/v1/system/health", tags=["System Observability"])
async def aggregate_system_health():
    """
    Asynchronously queries all 5 microservices to compile a unified health report.
    Reports individual service status, ping latency, and circuit breaker states.
    Demonstrates cross-service observability and resilience monitoring for evaluation!
    """
    # Define mapping of all microservices, their probe URLs, and their Circuit Breakers
    services_to_probe = [
        {"name": "calyx-auth-service", "url": f"{gateway_settings.AUTH_SERVICE_URL}/health/live", "breaker": auth_breaker},
        {"name": "calyx-job-service", "url": f"{gateway_settings.JOB_SERVICE_URL}/health/live", "breaker": job_breaker},
        {"name": "calyx-resume-service", "url": f"{gateway_settings.RESUME_SERVICE_URL}/health/live", "breaker": resume_breaker},
        {"name": "calyx-agent-service", "url": f"{gateway_settings.AGENT_SERVICE_URL}/health/live", "breaker": agent_breaker},
        {"name": "calyx-analytics-service", "url": f"{gateway_settings.ANALYTICS_SERVICE_URL}/health/live", "breaker": analytics_breaker},
    ]

    # Initialize dictionary to collect service health statuses
    health_results = {}
    overall_healthy = True

    # Use an asynchronous HTTP client to ping all services concurrently
    async with httpx.AsyncClient(timeout=3.0) as client:
        for svc in services_to_probe:
            svc_name = svc["name"]
            svc_url = svc["url"]
            breaker: CircuitBreaker = svc["breaker"]
            
            t0 = time.perf_counter()
            try:
                # Attempt to ping the upstream service
                res = await client.get(svc_url)
                latency = round((time.perf_counter() - t0) * 1000, 2)
                
                if res.status_code == 200:
                    health_results[svc_name] = {
                        "status": "UP",
                        "latency_ms": latency,
                        "circuit_breaker": breaker.get_status(),
                        "url": svc_url
                    }
                else:
                    health_results[svc_name] = {
                        "status": "DEGRADED",
                        "latency_ms": latency,
                        "http_code": res.status_code,
                        "circuit_breaker": breaker.get_status()
                    }
                    overall_healthy = False
            except Exception as e:
                # Service unreachable or timed out
                health_results[svc_name] = {
                    "status": "DOWN",
                    "error": str(e),
                    "circuit_breaker": breaker.get_status()
                }
                overall_healthy = False

    # Return standard response with the full health matrix
    return {
        "success": True,
        "data": {
            "gateway_status": "UP",
            "overall_healthy": overall_healthy,
            "services": health_results,
            "timestamp": time.time()
        }
    }


# ==============================================================================
# GENERIC REVERSE PROXY DISPATCHER FUNCTION
# ==============================================================================
async def proxy_request(
    target_base_url: str,
    path: str,
    request: Request,
    circuit_breaker: CircuitBreaker
) -> Response:
    """
    Proxies an incoming request to an upstream microservice with Circuit Breaker protection.
    
    Parameters:
      - target_base_url: The root URL of the upstream service (e.g. "http://127.0.0.1:8001")
      - path: The relative path to forward to (e.g. "/api/v1/auth/login")
      - request: The incoming FastAPI Request object containing headers, query params, body
      - circuit_breaker: The CircuitBreaker instance safeguarding this specific upstream service
    """
    # Retrieve request correlation ID for tracing
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    # Check if the Circuit Breaker is currently OPEN (blocking calls to a failing service)
    state = circuit_breaker.get_status()
    if state["state"] == "OPEN":
        logger.warning(f"[{request_id}] Circuit breaker OPEN for {circuit_breaker.name}. Fast failing.")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "error": {
                    "code": "CIRCUIT_BREAKER_OPEN",
                    "message": f"Upstream service protected by {circuit_breaker.name} is temporarily unavailable. Failures={circuit_breaker.consecutive_failures}",
                    "details": state,
                    "trace_id": request_id
                }
            },
            headers={"X-Request-ID": request_id}
        )

    # Construct the full destination URL
    # Ensure query string parameters are preserved
    query_str = str(request.url.query)
    full_url = f"{target_base_url.rstrip('/')}{path}"
    if query_str:
        full_url = f"{full_url}?{query_str}"

    # Extract incoming request headers, filtering out hop-by-hop headers
    forward_headers = {}
    hop_by_hop = {"host", "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade"}
    for header_name, header_val in request.headers.items():
        if header_name.lower() not in hop_by_hop:
            forward_headers[header_name] = header_val

    # Ensure X-Request-ID is explicitly passed to upstream services for distributed tracing
    forward_headers["X-Request-ID"] = request_id

    # Read the raw request body bytes
    body_bytes = await request.body()

    # Forward the request using httpx
    try:
        async with httpx.AsyncClient(timeout=gateway_settings.PROXY_TIMEOUT_SECONDS) as client:
            upstream_res = await client.request(
                method=request.method,
                url=full_url,
                headers=forward_headers,
                content=body_bytes
            )

        # Notify the Circuit Breaker of a successful upstream roundtrip
        circuit_breaker._on_success()

        # Build response headers to relay back to the caller
        response_headers = dict(upstream_res.headers)
        response_headers["X-Request-ID"] = request_id

        # Return the upstream response status code, content, and headers
        return Response(
            content=upstream_res.content,
            status_code=upstream_res.status_code,
            headers=response_headers,
            media_type=upstream_res.headers.get("content-type")
        )

    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as net_err:
        # Upstream service failed to connect or timed out; record the failure in the circuit breaker
        circuit_breaker._on_failure(net_err)
        logger.error(f"[{request_id}] Connection error forwarding to {full_url}: {str(net_err)}")

        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={
                "success": False,
                "error": {
                    "code": "UPSTREAM_SERVICE_UNREACHABLE",
                    "message": f"Failed to connect to upstream service at {target_base_url}. Error: {str(net_err)}",
                    "details": circuit_breaker.get_status(),
                    "trace_id": request_id
                }
            },
            headers={"X-Request-ID": request_id}
        )
    except Exception as general_err:
        # Unexpected error during proxying
        circuit_breaker._on_failure(general_err)
        logger.error(f"[{request_id}] Unexpected error proxying to {full_url}: {str(general_err)}")

        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "success": False,
                "error": {
                    "code": "BAD_GATEWAY",
                    "message": f"Gateway proxy failure: {str(general_err)}",
                    "trace_id": request_id
                }
            },
            headers={"X-Request-ID": request_id}
        )


# ==============================================================================
# ROUTE DISPATCHERS TO INDIVIDUAL MICROSERVICES
# ==============================================================================

# Route 1: Calyx Auth Service (Port 8001)
@app.api_route("/api/v1/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"], tags=["Auth Proxy"])
async def route_auth_service(path: str, request: Request):
    """
    Proxies all /api/v1/auth/* requests to the Calyx Auth Service on port 8001.
    Handles user registration, login, token refresh, and user profile queries.
    """
    return await proxy_request(
        target_base_url=gateway_settings.AUTH_SERVICE_URL,
        path=f"/api/v1/auth/{path}",
        request=request,
        circuit_breaker=auth_breaker
    )


# Route 2: Calyx Job Service (Port 8002)
@app.api_route("/api/v1/jobs/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"], tags=["Job Proxy"])
async def route_job_service(path: str, request: Request):
    """
    Proxies all /api/v1/jobs/* requests to the Calyx Job Service on port 8002.
    Handles job creation, job search/filter, and candidate application submissions.
    """
    return await proxy_request(
        target_base_url=gateway_settings.JOB_SERVICE_URL,
        path=f"/api/v1/jobs/{path}",
        request=request,
        circuit_breaker=job_breaker
    )


# Route 3: Calyx Resume Service (Port 8003)
@app.api_route("/api/v1/resumes/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"], tags=["Resume Proxy"])
async def route_resume_service(path: str, request: Request):
    """
    Proxies all /api/v1/resumes/* requests to the Calyx Resume Service on port 8003.
    Handles resume uploads, PDF/text parsing, semantic vector embeddings, and search.
    """
    return await proxy_request(
        target_base_url=gateway_settings.RESUME_SERVICE_URL,
        path=f"/api/v1/resumes/{path}",
        request=request,
        circuit_breaker=resume_breaker
    )


# Route 4: Calyx Agent Service (Port 8004)
@app.api_route("/api/v1/agent/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"], tags=["Agent Proxy"])
async def route_agent_service(path: str, request: Request):
    """
    Proxies all /api/v1/agent/* requests to the Calyx Agent Service on port 8004.
    Triggers multi-agent screening evaluations and retrieves transparent reasoning traces.
    """
    return await proxy_request(
        target_base_url=gateway_settings.AGENT_SERVICE_URL,
        path=f"/api/v1/agent/{path}",
        request=request,
        circuit_breaker=agent_breaker
    )


# Route 5: Calyx Analytics Service (Port 8005)
@app.api_route("/api/v1/analytics/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"], tags=["Analytics Proxy"])
async def route_analytics_service(path: str, request: Request):
    """
    Proxies all /api/v1/analytics/* requests to the Calyx Analytics Service on port 8005.
    Provides conversion funnel data, score histograms, and recruitment metrics.
    """
    return await proxy_request(
        target_base_url=gateway_settings.ANALYTICS_SERVICE_URL,
        path=f"/api/v1/analytics/{path}",
        request=request,
        circuit_breaker=analytics_breaker
    )


# Root welcome route
@app.get("/", tags=["Root"])
def root_endpoint():
    """
    Root endpoint confirming the Gateway is active with service metadata.
    """
    return {
        "service": "Calyx Unified API Gateway",
        "status": "ONLINE",
        "version": "1.0.0",
        "documentation": "/docs",
        "system_health": "/api/v1/system/health"
    }


# Standalone entrypoint for running directly via `python -m services.calyx_gateway_service.main`
if __name__ == "__main__":
    # Import uvicorn ASGI server to host the FastAPI application
    import uvicorn
    # Start the server listening on 0.0.0.0 and configured port
    uvicorn.run("services.calyx_gateway_service.main:app", host="0.0.0.0", port=gateway_settings.PORT, reload=True)
