# ==============================================================================
# CALYX UNIT TESTS: RESILIENCE & CIRCUIT BREAKER
# ==============================================================================
import time
import pytest
from common.resilience import CircuitBreaker, CircuitBreakerOpenException, CircuitState, retry_with_backoff


def test_circuit_breaker_transitions():
    """
    Verifies state transitions: CLOSED -> OPEN -> HALF_OPEN -> CLOSED.
    """
    breaker = CircuitBreaker(name="test-service", failure_threshold=3, recovery_timeout_seconds=0.2)
    assert breaker.state == CircuitState.CLOSED

    # Failure 1
    with pytest.raises(ValueError):
        breaker.call(lambda: (_ for _ in ()).throw(ValueError("Error 1")))
    assert breaker.state == CircuitState.CLOSED
    assert breaker.consecutive_failures == 1

    # Failure 2
    with pytest.raises(ValueError):
        breaker.call(lambda: (_ for _ in ()).throw(ValueError("Error 2")))
    assert breaker.state == CircuitState.CLOSED

    # Failure 3 -> Trips to OPEN
    with pytest.raises(ValueError):
        breaker.call(lambda: (_ for _ in ()).throw(ValueError("Error 3")))
    assert breaker.state == CircuitState.OPEN

    # While OPEN, calls are blocked immediately with CircuitBreakerOpenException
    with pytest.raises(CircuitBreakerOpenException):
        breaker.call(lambda: "should never run")

    # Wait for recovery timeout (0.2s)
    time.sleep(0.25)

    # Next call transitions to HALF_OPEN and succeeds -> resets to CLOSED
    result = breaker.call(lambda: "recovered!")
    assert result == "recovered!"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.consecutive_failures == 0


def test_retry_with_backoff():
    """
    Verifies that retry_with_backoff retries and succeeds on subsequent attempts.
    """
    call_count = 0

    @retry_with_backoff(max_retries=3, initial_delay_seconds=0.05, backoff_multiplier=1.5)
    def flaky_network_call():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary timeout")
        return "SUCCESS"

    result = flaky_network_call()
    assert result == "SUCCESS"
    assert call_count == 3


if __name__ == "__main__":
    pytest.main(["-v", __file__])
