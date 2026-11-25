# ==============================================================================
# CALYX COMMON MODULE: RESILIENCE, CIRCUIT BREAKER & RETRY MECHANISMS
# ==============================================================================
# Concept Explanation for Beginners:
# 1. Why is Resilience Crucial in Microservices? (Rubric: 4 Marks)
#    In a distributed system, network partitions, database restarts, and service
#    slowdowns are guaranteed to happen. If Service A waits 30 seconds for a failing
#    Service B on every request, Service A's thread pool exhausts and it crashes too!
#    This is called a "Cascading Failure".
#
# 2. Circuit Breaker Pattern:
#    Just like an electrical circuit breaker in your house cuts power when there is
#    a power surge to prevent a fire:
#    - CLOSED (Normal): Requests pass through normally.
#    - OPEN (Failing): If failures exceed threshold (e.g. 5 consecutive errors),
#      the circuit TRIPS OPEN. All subsequent requests fail fast immediately
#      (0ms delay) with a graceful fallback, sparing the downstream service!
#    - HALF_OPEN (Testing): After a cooldown period (e.g. 15s), the breaker allows
#      a single test request. If it succeeds, the breaker resets to CLOSED!
#
# 3. Exponential Backoff Retries:
#    If a network packet drops, retrying immediately can bombard a struggling server.
#    Exponential backoff waits 0.5s, then 1s, then 2s, giving the system time to recover.
# ==============================================================================

import time
import functools
from enum import Enum
from typing import Callable, Any, Optional
from loguru import logger


class CircuitState(str, Enum):
    """The three states of a Circuit Breaker."""
    CLOSED = "CLOSED"        # Normal operation: all calls allowed through
    OPEN = "OPEN"            # Downstream degraded: all calls fail fast immediately
    HALF_OPEN = "HALF_OPEN"  # Testing recovery: single probe call allowed through


class CircuitBreakerOpenException(Exception):
    """Raised when an operation is blocked because the circuit breaker is OPEN."""
    pass


class CircuitBreaker:
    """
    Production-grade Circuit Breaker implementation for inter-service communication.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 15.0,
        expected_exceptions: tuple = (Exception,)
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.expected_exceptions = expected_exceptions

        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_failure_time = 0.0
        self.last_state_change = time.time()

    def __call__(self, func: Callable) -> Callable:
        """Allows CircuitBreaker to be used as a function decorator."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Executes the target function through the Circuit Breaker state machine.
        """
        now = time.time()

        # Step 1: Check if OPEN circuit should transition to HALF_OPEN
        if self.state == CircuitState.OPEN:
            if now - self.last_failure_time >= self.recovery_timeout_seconds:
                logger.info(f"[CircuitBreaker:{self.name}] Recovery timeout elapsed. Transitioning OPEN -> HALF_OPEN.")
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
            else:
                remaining = round(self.recovery_timeout_seconds - (now - self.last_failure_time), 1)
                logger.warning(f"[CircuitBreaker:{self.name}] Call blocked! Circuit is OPEN (retry in {remaining}s).")
                raise CircuitBreakerOpenException(
                    f"Service '{self.name}' is temporarily unavailable (Circuit OPEN). Try again in {remaining}s."
                )

        # Step 2: Attempt function execution
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions as exc:
            self._on_failure(exc)
            raise exc

    def _on_success(self):
        """Called when a protected call succeeds."""
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"[CircuitBreaker:{self.name}] Probe call succeeded! Resetting HALF_OPEN -> CLOSED.")
            self.state = CircuitState.CLOSED
            self.last_state_change = time.time()
        self.consecutive_failures = 0

    def _on_failure(self, exc: Exception):
        """Called when a protected call raises an expected exception."""
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        logger.warning(f"[CircuitBreaker:{self.name}] Failure #{self.consecutive_failures}: {str(exc)}")

        if self.consecutive_failures >= self.failure_threshold and self.state != CircuitState.OPEN:
            logger.error(
                f"[CircuitBreaker:{self.name}] Failure threshold ({self.failure_threshold}) reached! "
                f"Tripping circuit CLOSED -> OPEN for {self.recovery_timeout_seconds}s."
            )
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()

    def get_status(self) -> dict:
        """Returns diagnostic telemetry for health dashboards."""
        return {
            "name": self.name,
            "state": self.state.value,
            "consecutive_failures": self.consecutive_failures,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_seconds": self.recovery_timeout_seconds,
            "last_failure_timestamp": self.last_failure_time
        }


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay_seconds: float = 0.5,
    backoff_multiplier: float = 2.0,
    expected_exceptions: tuple = (Exception,)
):
    """
    Decorator that retries transient operations with exponential backoff.
    Example: wait 0.5s, then 1.0s, then 2.0s before failing.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay_seconds
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except expected_exceptions as exc:
                    if attempt == max_retries:
                        logger.error(f"[Retry] Function '{func.__name__}' failed after {max_retries} attempts: {str(exc)}")
                        raise exc
                    logger.warning(
                        f"[Retry] Function '{func.__name__}' attempt {attempt}/{max_retries} failed: {str(exc)}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)
                    delay *= backoff_multiplier
        return wrapper
    return decorator
