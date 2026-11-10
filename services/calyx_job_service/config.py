# ==============================================================================
# CALYX JOB SERVICE: CONFIGURATION MODULE
# ==============================================================================
# Concept Explanation for Beginners:
# In the Database-per-Service pattern, `calyx-job-service` uses MongoDB instead
# of a relational SQL database.
# Why MongoDB for Jobs & Applications?
# 1. Semi-Structured Data: Job descriptions, rubric weightings, custom screening
#    questions, and candidate answers vary greatly across roles (e.g. Frontend vs
#    Data Scientist). MongoDB documents (JSON-like BSON) store nested arrays
#    and dynamic schemas naturally without requiring complex SQL JOIN tables.
# 2. Dual-Mode Connection:
#    If a live MongoDB server is available at MONGODB_URL, PyMongo connects to it.
#    If running in a local lightweight development environment without MongoDB installed,
#    the database engine automatically falls back to 'mongomock' (an in-memory
#    MongoDB clone). This guarantees 100% zero-dependency local testing while
#    remaining completely cloud-native for Docker and Kubernetes!
# ==============================================================================

import os
from pydantic import Field
from pydantic_settings import SettingsConfigDict
from common.config import BaseMicroserviceSettings


class JobServiceSettings(BaseMicroserviceSettings):
    """
    Configuration settings specific to the Job & Application microservice.
    Inherits global JWT and logging settings from BaseMicroserviceSettings.
    """

    # Service identifier used in logs and tracing
    SERVICE_NAME: str = Field(default="calyx-job-service", description="Service name")

    # TCP Network Port this microservice listens on
    PORT: int = Field(default=8002, description="TCP port for Job service")

    # MongoDB connection URI (e.g., 'mongodb://calyx-job-db:27017' in Kubernetes)
    # If set to 'mock' or if the connection fails locally, the system falls back to in-memory mongomock
    MONGODB_URL: str = Field(
        default=os.getenv("MONGODB_URL", "mongodb://localhost:27017"),
        description="MongoDB connection URI"
    )

    # Name of the MongoDB database
    MONGODB_DATABASE_NAME: str = Field(
        default=os.getenv("MONGODB_DATABASE_NAME", "calyx_jobs_db"),
        description="Target MongoDB database name"
    )

    # Maximum applications returned per paginated page
    DEFAULT_PAGE_SIZE: int = Field(default=20, description="Default pagination size")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


# Instantiate singleton settings object
job_settings = JobServiceSettings()
