# ==============================================================================
# CALYX AGENT SERVICE: REDIS STATE STORE & DISTRIBUTED LOCKS
# ==============================================================================
# Concept Explanation for Beginners:
# 1. Distributed Locking (`SETNX`):
#    In a distributed Kubernetes cluster with 5 pod replicas running `calyx-agent-service`,
#    what happens if two pods try to evaluate Candidate #42 at the exact same moment?
#    Without a lock, both pods would waste GPU tokens running duplicate work!
#    Redis provides atomic locking (`SET key value NX EX 30`). Only ONE pod can
#    successfully set the key; all other pods back off.
#
# 2. Agent Memory & Reasoning Trace:
#    Each autonomous agent writes its thought process (e.g. "I found a weakness in
#    concurrency, proposing a targeted question") into Redis in real time.
#    Recruiters can inspect this transparent trace to see WHY the AI made a decision!
# ==============================================================================

import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import redis
from redis.exceptions import ConnectionError, TimeoutError
import fakeredis
from common.logging_config import configure_logger
from services.calyx_agent_service.config import agent_settings

logger = configure_logger(agent_settings.SERVICE_NAME, agent_settings.LOG_LEVEL)

_redis_client = None


def get_redis_client(force_mock: bool = False):
    """
    Initializes Redis client with graceful fallback to in-memory fakeredis.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    if force_mock or agent_settings.REDIS_URL == "mock":
        logger.info("Using in-memory Redis mock engine (fakeredis).")
        _redis_client = fakeredis.FakeRedis(decode_responses=True)
    else:
        try:
            logger.info(f"Connecting to Redis at {agent_settings.REDIS_URL}...")
            client = redis.Redis.from_url(
                agent_settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2
            )
            # Test connection with PING
            client.ping()
            _redis_client = client
            logger.info("Successfully established connection to real Redis server.")
        except (ConnectionError, TimeoutError, Exception) as exc:
            logger.warning(
                f"Could not connect to external Redis ({str(exc)}). "
                "Gracefully falling back to in-memory fakeredis for local development/testing."
            )
            _redis_client = fakeredis.FakeRedis(decode_responses=True)

    return _redis_client


class AgentStateStore:
    """
    Abstraction over Redis for agent task state, distributed locks, and reasoning traces.
    """

    def __init__(self, client=None):
        self.r = client or get_redis_client()

    def acquire_lock(self, lock_name: str, expire_seconds: int = 60) -> bool:
        """
        Acquires an atomic distributed lock using Redis SET with NX and EX flags.
        Returns True if lock was acquired, False if another worker holds it.
        """
        key = f"agent:lock:{lock_name}"
        # nx=True: set only if key does NOT exist
        # ex=expire_seconds: automatically releases lock if worker crashes to prevent deadlocks
        acquired = self.r.set(key, "locked", nx=True, ex=expire_seconds)
        return bool(acquired)

    def release_lock(self, lock_name: str) -> None:
        """
        Releases a held distributed lock.
        """
        key = f"agent:lock:{lock_name}"
        self.r.delete(key)

    def save_task_state(self, task_id: str, state_data: Dict[str, Any]) -> None:
        """
        Saves or updates task status and evaluation state in Redis.
        """
        key = f"agent:task:{task_id}"
        payload = json.dumps(state_data)
        self.r.set(key, payload, ex=86400)  # Persist for 24 hours

    def get_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves task state from Redis by task ID.
        """
        key = f"agent:task:{task_id}"
        raw = self.r.get(key)
        if not raw:
            return None
        return json.loads(raw)

    def append_trace_step(self, task_id: str, agent_name: str, thought: str, action: str, output: Any) -> None:
        """
        Appends an immutable reasoning step to the agent trace in Redis.
        """
        key = f"agent:trace:{task_id}"
        step_record = {
            "agent": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "thought": thought,
            "action": action,
            "output": output
        }
        self.r.rpush(key, json.dumps(step_record))

    def get_full_trace(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves the complete chronological reasoning trace for an evaluation task.
        """
        key = f"agent:trace:{task_id}"
        raw_items = self.r.lrange(key, 0, -1)
        return [json.loads(item) for item in raw_items]

    def ping(self) -> bool:
        """Verifies Redis connection health."""
        return bool(self.r.ping())


# Instantiate global state store
state_store = AgentStateStore()


def get_state_store() -> AgentStateStore:
    """FastAPI dependency yielding the AgentStateStore."""
    return state_store
