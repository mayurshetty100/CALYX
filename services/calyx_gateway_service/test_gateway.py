"""
================================================================================
CALYX GATEWAY SERVICE UNIT & INTEGRATION TESTS
================================================================================
File: services/calyx_gateway_service/test_gateway.py
Purpose:
  Validates API Gateway routing, distributed tracing middleware, circuit breaker
  fast-failing, and aggregate system health monitoring.
================================================================================
"""

# Import pytest framework for writing readable, parameterized unit tests
import pytest

# Import TestClient from starlette/fastapi to simulate HTTP requests in memory
from starlette.testclient import TestClient

# Import the FastAPI application instance and CircuitState
from common.resilience import CircuitState
from services.calyx_gateway_service.main import app, auth_breaker


@pytest.fixture(scope="module")
def client():
    """
    Creates an in-memory HTTP TestClient bound to the Gateway FastAPI application.
    """
    with TestClient(app) as test_client:
        yield test_client


def test_01_gateway_liveness_and_readiness(client):
    """
    Tests that Kubernetes liveness and readiness probes return 200 OK.
    """
    live_res = client.get("/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "alive"

    ready_res = client.get("/health/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"


def test_02_distributed_tracing_header_injection(client):
    """
    Verifies that every incoming request gets an X-Request-ID header attached
    and returned in the response headers.
    """
    # 1. Test automatic UUID generation when caller doesn't provide one
    res_auto = client.get("/")
    assert res_auto.status_code == 200
    assert "X-Request-ID" in res_auto.headers
    assert len(res_auto.headers["X-Request-ID"]) > 10

    # 2. Test propagation when caller supplies their own custom X-Request-ID
    custom_trace_id = "trace-custom-evaluation-12345"
    res_custom = client.get("/", headers={"X-Request-ID": custom_trace_id})
    assert res_custom.status_code == 200
    assert res_custom.headers["X-Request-ID"] == custom_trace_id


def test_03_aggregate_system_health(client):
    """
    Verifies that the /api/v1/system/health endpoint returns structured status
    for all 5 microservices.
    """
    res = client.get("/api/v1/system/health")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["gateway_status"] == "UP"
    assert "services" in data
    # All 5 services must be tracked in the health matrix
    assert "calyx-auth-service" in data["services"]
    assert "calyx-job-service" in data["services"]
    assert "calyx-resume-service" in data["services"]
    assert "calyx-agent-service" in data["services"]
    assert "calyx-analytics-service" in data["services"]


def test_04_circuit_breaker_fast_fail_when_open(client):
    """
    Tests that when an upstream service's circuit breaker is forced into the OPEN state,
    the gateway returns 503 SERVICE UNAVAILABLE without hanging.
    """
    # Manually simulate 5 consecutive failures to trip the auth_breaker into OPEN state
    auth_breaker.state = CircuitState.OPEN
    auth_breaker.consecutive_failures = 5

    try:
        # Send a request that would proxy to the Auth service
        res = client.get("/api/v1/auth/profile")
        
        # Must return 503 Service Unavailable immediately
        assert res.status_code == 503
        body = res.json()
        assert body["success"] is False
        assert body["error"]["code"] == "CIRCUIT_BREAKER_OPEN"
    finally:
        # Reset the circuit breaker state to CLOSED so subsequent tests aren't impacted
        auth_breaker.state = CircuitState.CLOSED
        auth_breaker.consecutive_failures = 0
