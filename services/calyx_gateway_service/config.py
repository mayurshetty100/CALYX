"""
================================================================================
CALYX UNIFIED API GATEWAY SERVICE CONFIGURATION
================================================================================
File: services/calyx_gateway_service/config.py
Purpose:
  Defines environment variables, port assignments, upstream microservice URLs,
  and timeouts for the reverse-proxy API Gateway.
  
Key Concepts Explained:
  - API Gateway Pattern: A single front-door reverse-proxy that intercepts all
    incoming client requests (from browsers, mobile apps, or CLI), terminates SSL/TLS,
    handles Cross-Origin Resource Sharing (CORS), injects correlation IDs (X-Request-ID)
    for distributed tracing, and securely routes requests to internal backend microservices.
  - Reverse Proxy: A server that takes requests from the internet and forwards them
    to servers in an internal network, hiding the private internal network topology.
================================================================================
"""

# Import the standard os module to read environment variables from the operating system
import os

# Import Pydantic SettingsConfigDict to enable automatic reading of .env files
from pydantic_settings import SettingsConfigDict

# Import the shared BaseMicroserviceSettings class from our common kernel
from common.config import BaseMicroserviceSettings


# Define the GatewaySettings class inheriting from BaseMicroserviceSettings
class GatewaySettings(BaseMicroserviceSettings):
    """
    Configuration settings for the Calyx API Gateway Service.
    Inherits SERVICE_NAME, ENVIRONMENT, LOG_LEVEL from BaseMicroserviceSettings.
    """

    # Human-readable service name for identification in logs and Swagger UI
    SERVICE_NAME: str = "calyx-gateway-service"

    # Default port for the API gateway (Standard 8000 port for API gateways)
    PORT: int = int(os.getenv("GATEWAY_SERVICE_PORT", "8000"))

    # Upstream Microservice URL: Calyx Auth Service (Port 8001)
    # Inside Docker / Kubernetes, this will be "http://calyx-auth-service:8001"
    AUTH_SERVICE_URL: str = os.getenv("AUTH_SERVICE_URL", "http://127.0.0.1:8001")

    # Upstream Microservice URL: Calyx Job Service (Port 8002)
    # Inside Docker / Kubernetes, this will be "http://calyx-job-service:8002"
    JOB_SERVICE_URL: str = os.getenv("JOB_SERVICE_URL", "http://127.0.0.1:8002")

    # Upstream Microservice URL: Calyx Resume Service (Port 8003)
    # Inside Docker / Kubernetes, this will be "http://calyx-resume-service:8003"
    RESUME_SERVICE_URL: str = os.getenv("RESUME_SERVICE_URL", "http://127.0.0.1:8003")

    # Upstream Microservice URL: Calyx Agent Service (Port 8004)
    # Inside Docker / Kubernetes, this will be "http://calyx-agent-service:8004"
    AGENT_SERVICE_URL: str = os.getenv("AGENT_SERVICE_URL", "http://127.0.0.1:8004")

    # Upstream Microservice URL: Calyx Analytics Service (Port 8005)
    # Inside Docker / Kubernetes, this will be "http://calyx-analytics-service:8005"
    ANALYTICS_SERVICE_URL: str = os.getenv("ANALYTICS_SERVICE_URL", "http://127.0.0.1:8005")

    # Timeout in seconds for proxying HTTP requests to upstream services
    # If a service takes longer than this to respond, a 504 Gateway Timeout is returned
    PROXY_TIMEOUT_SECONDS: float = float(os.getenv("PROXY_TIMEOUT_SECONDS", "30.0"))

    # Allowed CORS origins (Frontends allowed to talk to this API)
    # By default allows localhost for dev, plus Vercel production domains
    ALLOWED_CORS_ORIGINS: str = os.getenv(
        "ALLOWED_CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173,*"
    )

    # Standalone mode: when true, routes directly in-process (ideal for Render single free tier)
    STANDALONE_GATEWAY_MODE: bool = os.getenv("STANDALONE_GATEWAY_MODE", "false").lower() in ("true", "1", "yes")

    # Configuration dictionary specifying case-insensitivity and environment file loading
    model_config = SettingsConfigDict(
        # Read from .env file if present in the execution path
        env_file=".env",
        # Allow extra environment variables without throwing validation errors
        extra="ignore"
    )


# Instantiate a singleton instance of GatewaySettings to be used across the service
gateway_settings = GatewaySettings()
