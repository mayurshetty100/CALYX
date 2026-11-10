# ==============================================================================
# CALYX ANALYTICS SERVICE: CONFIGURATION MODULE
# ==============================================================================
# Concept Explanation for Beginners:
# In the Database-per-Service architecture, running expensive aggregate queries
# (like calculating average scores, time-to-hire percentiles, or histograms)
# directly on the primary Auth or Job databases will lock operational tables
# and cause latency spikes for active users.
# The Analytics Service maintains its own dedicated Analytics Database
# (PostgreSQL Analytics / SQLite Analytics) fed by asynchronous pipeline events.
# ==============================================================================

import os
from pydantic import Field
from pydantic_settings import SettingsConfigDict
from common.config import BaseMicroserviceSettings


class AnalyticsServiceSettings(BaseMicroserviceSettings):
    """
    Configuration settings specific to the Analytics & Reporting microservice.
    """

    # Service identifier used in logs and tracing
    SERVICE_NAME: str = Field(default="calyx-analytics-service", description="Service name")

    # TCP Network Port this microservice listens on
    PORT: int = Field(default=8005, description="TCP port for Analytics service")

    # Database connection URL for analytics storage (PostgreSQL in production, SQLite locally)
    DATABASE_URL: str = Field(
        default=os.getenv("ANALYTICS_DATABASE_URL", "sqlite:///./calyx_analytics.db"),
        description="SQLAlchemy database connection URL for analytics"
    )

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


# Instantiate singleton settings object
analytics_settings = AnalyticsServiceSettings()
