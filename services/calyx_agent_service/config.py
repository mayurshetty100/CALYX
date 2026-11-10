# ==============================================================================
# CALYX AGENT SERVICE: CONFIGURATION MODULE
# ==============================================================================
# Concept Explanation for Beginners:
# The `calyx-agent-service` is the AI Brain of CALYX.
# Instead of a single LLM call, it orchestrates a team of specialized AI Agents
# that collaborate, critique, and build consensus.
#
# Dedicated Database: Redis (In-Memory Key-Value & Queue)
# Why Redis for the Agent Service?
# 1. Microsecond State Storage: Multi-agent conversations and reasoning traces
#    produce rapid state updates that require sub-millisecond writes.
# 2. Distributed Locks (`SETNX`): When hundreds of candidates apply simultaneously,
#    Redis locks ensure two agent workers don't evaluate the same application at once.
# 3. Task Queues: Redis Lists/Streams decouple web requests from compute-heavy
#    AI agent execution.
# ==============================================================================

import os
from pydantic import Field
from pydantic_settings import SettingsConfigDict
from common.config import BaseMicroserviceSettings


class AgentServiceSettings(BaseMicroserviceSettings):
    """
    Configuration settings specific to the Agentic AI Orchestration microservice.
    """

    # Service identifier used in logs and tracing
    SERVICE_NAME: str = Field(default="calyx-agent-service", description="Service name")

    # TCP Network Port this microservice listens on
    PORT: int = Field(default=8004, description="TCP port for Agent service")

    # Redis connection URL (e.g. 'redis://calyx-redis:6379/0' in Kubernetes)
    # If a live Redis container is not running, falls back automatically to in-memory fakeredis
    REDIS_URL: str = Field(
        default=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        description="Redis connection URL for agent memory and distributed locks"
    )

    # URL of downstream calyx-job-service for writing back evaluation results
    JOB_SERVICE_URL: str = Field(
        default=os.getenv("JOB_SERVICE_URL", "http://localhost:8002"),
        description="Base URL for Job service"
    )

    # AI Reasoning model temperature (0.1 for high determinism and consistency)
    AGENT_TEMPERATURE: float = Field(default=0.1, description="LLM sampling temperature")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


# Instantiate singleton settings object
agent_settings = AgentServiceSettings()
