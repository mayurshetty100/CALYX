# ==============================================================================
# CALYX RESUME SERVICE: CONFIGURATION MODULE
# ==============================================================================
# Concept Explanation for Beginners:
# The Resume Service is responsible for Document Intelligence and Vector Search.
# Instead of storing high-dimensional vectors in a traditional SQL table (which
# causes severe performance degradation on large datasets), this service connects
# to a dedicated Vector Store optimized for multidimensional spatial indexing
# and Cosine Similarity math.
# ==============================================================================

import os
from pydantic import Field
from pydantic_settings import SettingsConfigDict
from common.config import BaseMicroserviceSettings


class ResumeServiceSettings(BaseMicroserviceSettings):
    """
    Configuration settings specific to the Resume Processing & Vector Engine microservice.
    """

    # Service identifier used in logs and tracing
    SERVICE_NAME: str = Field(default="calyx-resume-service", description="Service name")

    # TCP Network Port this microservice listens on
    PORT: int = Field(default=8003, description="TCP port for Resume service")

    # Dimensionality of the semantic vector embeddings (384-dimensional dense vectors)
    # 384 is the standard dimensionality used by models like all-MiniLM-L6-v2
    EMBEDDING_DIMENSION: int = Field(default=384, description="Dimensionality of vector embeddings")

    # Directory where vector index and resume metadata are persisted
    VECTOR_STORAGE_DIR: str = Field(
        default=os.getenv("VECTOR_STORAGE_DIR", "./calyx_vector_store"),
        description="Path to local vector index storage directory"
    )

    # Maximum allowed resume upload file size in megabytes (e.g. 10 MB)
    MAX_UPLOAD_SIZE_MB: int = Field(default=10, description="Max upload file size in MB")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


# Instantiate singleton settings object
resume_settings = ResumeServiceSettings()
