# ==============================================================================
# CALYX AUTH SERVICE: CONFIGURATION MODULE
# ==============================================================================
# Concept Explanation for Beginners:
# Each microservice needs its own database connection string and network port.
# Here, we define the settings for `calyx-auth-service`.
# Notice how the default database URL uses SQLite for instant local zero-setup
# testing (`sqlite:///./calyx_auth.db`), but when deployed to Kubernetes or
# Docker Compose, setting `DATABASE_URL=postgresql://user:pass@calyx-auth-db:5432/calyx_auth`
# seamlessly switches it to enterprise PostgreSQL with ZERO code changes!
# This is called "Environment Agnostic Design".
# ==============================================================================

import os
from pydantic import Field
from common.config import BaseMicroserviceSettings


class AuthServiceSettings(BaseMicroserviceSettings):
    """
    Configuration settings specific to the Auth & Identity microservice.
    Inherits global JWT and logging settings from BaseMicroserviceSettings.
    """

    # Service identifier used in logs and tracing
    SERVICE_NAME: str = Field(default="calyx-auth-service", description="Service name")

    # Network port this microservice listens on
    PORT: int = Field(default=8001, description="TCP port for Auth service")

    # Database connection string (Database-per-service: PostgreSQL for Auth)
    # Defaults to local SQLite if POSTGRES_URL environment variable is not set
    DATABASE_URL: str = Field(
        default=os.getenv("DATABASE_URL", "sqlite:///./calyx_auth.db"),
        description="SQLAlchemy database connection URL (PostgreSQL in production, SQLite fallback)"
    )

    # Rate limiting: Maximum login attempts allowed per minute from a single IP
    MAX_LOGIN_ATTEMPTS_PER_MINUTE: int = Field(default=10, description="Brute-force protection threshold")


# Instantiate a singleton settings object for this microservice
auth_settings = AuthServiceSettings()
