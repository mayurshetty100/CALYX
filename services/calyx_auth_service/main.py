# ==============================================================================
# CALYX AUTH SERVICE: FASTAPI APPLICATION ENTRYPOINT & API ROUTES
# ==============================================================================
# Concept Explanation for Beginners:
# 1. FastAPI:
#    A modern, high-performance web framework for building APIs with Python 3.8+
#    based on standard Python type hints. It automatically produces interactive
#    Swagger/OpenAPI documentation at `/docs`.
#
# 2. Kubernetes Probes (/health/live and /health/ready):
#    - Liveness Probe: "Is this container alive or frozen in an infinite loop?"
#      If this returns 500 or times out, Kubernetes automatically restarts the container.
#    - Readiness Probe: "Is this container ready to accept user traffic?"
#      If the database connection is still starting up, Kubernetes waits and does NOT
#      route traffic to this pod until readiness returns HTTP 200!
# ==============================================================================

from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Request, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

# Import shared modules from common
from common.responses import StandardResponse, StandardErrorResponse, ErrorDetail
from common.logging_config import configure_logger
from common.security import decode_and_verify_token

# Import internal service modules
from services.calyx_auth_service.config import auth_settings
from services.calyx_auth_service.database import engine, Base, get_db
from services.calyx_auth_service.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenRefreshRequest,
    UserResponse,
    AuthTokensData,
    TokenVerifyResponse,
)
from services.calyx_auth_service.service import AuthService
from services.calyx_auth_service.models import User

# Initialize structured logger
logger = configure_logger(auth_settings.SERVICE_NAME, auth_settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan Context Manager.
    Executes startup tasks before accepting traffic, and teardown tasks upon shutdown.
    """
    logger.info("Initializing CALYX Auth Service database tables...")
    # Create tables if they do not exist
    Base.metadata.create_all(bind=engine)
    logger.info("Auth Service database tables verified/created successfully.")
    yield
    logger.info("Shutting down CALYX Auth Service...")


# Initialize FastAPI Application
app = FastAPI(
    title="CALYX Authentication & Identity Service",
    description="Microservice responsible for user registration, authentication, RBAC, and JWT lifecycles.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable Cross-Origin Resource Sharing (CORS) to allow browser UI access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------
# GLOBAL EXCEPTION HANDLER: Standardize all HTTP errors
# ------------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Catches all raised HTTPExceptions and formats them into our unified
    StandardErrorResponse envelope.
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
# KUBERNETES PROBE ENDPOINTS
# ------------------------------------------------------------------------------
@app.get("/health/live", tags=["Health & Monitoring"])
def liveness_probe():
    """
    Kubernetes Liveness Probe.
    Returns HTTP 200 to signal that the process is running and not deadlocked.
    """
    return {"status": "alive", "service": auth_settings.SERVICE_NAME}


@app.get("/health/ready", tags=["Health & Monitoring"])
def readiness_probe(db: Session = Depends(get_db)):
    """
    Kubernetes Readiness Probe.
    Tests live database connectivity by executing a lightweight SELECT 1 query.
    If the database is down or unreachable, returns HTTP 503 so Kubernetes stops
    routing traffic to this instance.
    """
    try:
        # Execute basic SQL ping
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected", "service": auth_settings.SERVICE_NAME}
    except Exception as e:
        logger.error(f"Readiness probe failed - Database unreachable: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connectivity check failed"
        )


# ------------------------------------------------------------------------------
# AUTHENTICATION API ROUTES
# ------------------------------------------------------------------------------
@app.post("/api/v1/auth/register", response_model=StandardResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register_user(
    req: UserRegisterRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user account (Candidate, Recruiter, or Admin).
    Passes plain password through salted bcrypt hashing.
    """
    client_ip = request.client.host if request.client else "unknown"
    user = AuthService.register(db=db, req=req, ip_address=client_ip)
    
    return StandardResponse(
        success=True,
        message="User account registered successfully.",
        data=UserResponse.model_validate(user).model_dump()
    )


@app.post("/api/v1/auth/login", response_model=StandardResponse, tags=["Authentication"])
def login_user(
    req: UserLoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user credentials and issue signed JWT Access & Refresh tokens.
    """
    client_ip = request.client.host if request.client else "unknown"
    tokens_data = AuthService.authenticate_and_generate_tokens(
        db=db,
        email=req.email,
        plain_password=req.password,
        ip_address=client_ip
    )
    
    return StandardResponse(
        success=True,
        message="Authentication successful.",
        data=tokens_data.model_dump()
    )


@app.post("/api/v1/auth/refresh", response_model=StandardResponse, tags=["Authentication"])
def refresh_token(
    req: TokenRefreshRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Issue a new short-lived JWT access token using a valid, unrevoked refresh token.
    """
    client_ip = request.client.host if request.client else "unknown"
    new_tokens = AuthService.refresh_access_token(
        db=db,
        refresh_token_str=req.refresh_token,
        ip_address=client_ip
    )
    
    return StandardResponse(
        success=True,
        message="Access token refreshed successfully.",
        data=new_tokens.model_dump()
    )


@app.get("/api/v1/auth/verify", response_model=StandardResponse, tags=["Authentication"])
def verify_token(authorization: Optional[str] = Header(None)):
    """
    Internal verification endpoint used by downstream microservices or API Gateway.
    Inspects Authorization header 'Bearer <token>' and decodes claims.
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
            secret_key=auth_settings.JWT_SECRET_KEY,
            algorithm=auth_settings.JWT_ALGORITHM
        )
        return StandardResponse(
            success=True,
            message="Token is valid.",
            data=TokenVerifyResponse(
                valid=True,
                user_id=int(payload.get("sub")),
                email=payload.get("email"),
                role=payload.get("role")
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}"
        )


@app.get("/api/v1/auth/me", response_model=StandardResponse, tags=["Authentication"])
def get_current_user_profile(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Retrieve profile details of currently authenticated user.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header."
        )

    token_str = authorization.split(" ")[1]
    payload = decode_and_verify_token(
        token_str,
        secret_key=auth_settings.JWT_SECRET_KEY,
        algorithm=auth_settings.JWT_ALGORITHM
    )
    user_id = int(payload.get("sub"))
    
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return StandardResponse(
        success=True,
        message="User profile retrieved.",
        data=UserResponse.model_validate(user).model_dump()
    )


# Entry point for direct execution
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.calyx_auth_service.main:app", host="0.0.0.0", port=auth_settings.PORT, reload=True)
