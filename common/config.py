# ==============================================================================
# CALYX COMMON MODULE: CONFIGURATION MANAGEMENT
# ==============================================================================
# Concept Explanation for Beginners:
# In modern cloud and microservice applications, we follow the "12-Factor App"
# methodology. Rule #3 states: "Store configuration in the environment".
# Hardcoding database passwords, secret keys, or hostnames inside your code is
# a huge security risk.
# Pydantic's BaseSettings reads variables from your operating system's environment
# (or from a .env file) automatically, validates their data types, and makes them
# accessible as typed Python variables.
# ==============================================================================

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class BaseMicroserviceSettings(BaseSettings):
    """
    Base settings class shared across all CALYX microservices.
    Any individual microservice can inherit from this class to gain access to standard
    environment variables such as SERVICE_NAME, ENVIRONMENT, and LOG_LEVEL.
    """

    # Name of the microservice (e.g., 'calyx-auth-service', 'calyx-job-service')
    SERVICE_NAME: str = Field(default="calyx-service", description="Unique identifier for the microservice")

    # Current deployment environment: 'development', 'staging', or 'production'
    ENVIRONMENT: str = Field(default="development", description="Runtime environment: development, staging, production")

    # Minimum logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_LEVEL: str = Field(default="INFO", description="Granularity of log outputs")

    # Secret cryptographic key used to sign and verify JSON Web Tokens (JWT)
    # In production, this must be injected via a Kubernetes Secret!
    JWT_SECRET_KEY: str = Field(
        default="calyx-super-secret-production-grade-encryption-key-change-in-prod-12345",
        description="HMAC SHA-256 secret key for signing tokens"
    )

    # JWT signing algorithm: 'HS256' stands for HMAC using SHA-256 hash algorithm
    JWT_ALGORITHM: str = Field(default="HS256", description="Algorithm used to sign JWTs")

    # Access token lifespan in minutes (short-lived for security, e.g., 30 minutes)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Duration in minutes before access token expires")

    # Refresh token lifespan in days (long-lived to allow re-authentication, e.g., 7 days)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Duration in days before refresh token expires")

    # Pydantic v2 SettingsConfigDict: automatically read from a local .env file if present
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
