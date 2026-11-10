# ==============================================================================
# CALYX AUTH SERVICE: AUTOMATED TEST SUITE
# ==============================================================================
# Concept Explanation for Beginners:
# Automated testing is what separates amateur code from production-grade engineering.
# Using FastAPI's TestClient (built on top of `httpx`), we can simulate real HTTP
# requests against our microservice endpoints in memory without having to manually
# open Postman or run a browser!
# ==============================================================================

import os
import pytest
from fastapi.testclient import TestClient
from services.calyx_auth_service.main import app
from services.calyx_auth_service.database import Base, engine


@pytest.fixture(scope="module")
def client():
    """
    Module-level test client fixture that manages the FastAPI lifespan context.
    """
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


def test_01_liveness_and_readiness_probes(client):
    """
    Verifies Kubernetes health probes return HTTP 200 OK.
    """
    # Test Liveness
    live_res = client.get("/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "alive"

    # Test Readiness (DB connectivity)
    ready_res = client.get("/health/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"
    assert ready_res.json()["database"] == "connected"


def test_02_user_registration_success(client):
    """
    Tests registering a new candidate account.
    """
    payload = {
        "email": "ada.lovelace@calyx.ai",
        "password": "SecurePassword123!",
        "full_name": "Ada Lovelace",
        "role": "candidate"
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["success"] is True
    assert data["data"]["email"] == "ada.lovelace@calyx.ai"
    assert data["data"]["role"] == "candidate"
    assert "password_hash" not in data["data"]  # Security check!


def test_03_duplicate_email_conflict(client):
    """
    Verifies that attempting to register an existing email returns HTTP 409 Conflict.
    """
    payload = {
        "email": "ada.lovelace@calyx.ai",
        "password": "AnotherPassword456!",
        "full_name": "Duplicate Ada",
        "role": "candidate"
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 409
    assert res.json()["success"] is False


def test_04_user_login_success(client):
    """
    Tests logging in with correct credentials to obtain JWT access & refresh tokens.
    """
    login_payload = {
        "email": "ada.lovelace@calyx.ai",
        "password": "SecurePassword123!"
    }
    res = client.post("/api/v1/auth/login", json=login_payload)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"
    assert data["user"]["email"] == "ada.lovelace@calyx.ai"


def test_05_login_invalid_password(client):
    """
    Tests that submitting an incorrect password fails with HTTP 401 Unauthorized.
    """
    login_payload = {
        "email": "ada.lovelace@calyx.ai",
        "password": "WrongPassword999!"
    }
    res = client.post("/api/v1/auth/login", json=login_payload)
    assert res.status_code == 401
    assert res.json()["success"] is False


def test_06_token_verification_and_profile(client):
    """
    Tests token verification and fetching current user profile using Bearer token.
    """
    # 1. Login to get token
    login_res = client.post("/api/v1/auth/login", json={
        "email": "ada.lovelace@calyx.ai",
        "password": "SecurePassword123!"
    })
    tokens = login_res.json()["data"]
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # 2. Test /verify endpoint
    headers = {"Authorization": f"Bearer {access_token}"}
    verify_res = client.get("/api/v1/auth/verify", headers=headers)
    assert verify_res.status_code == 200
    assert verify_res.json()["data"]["valid"] is True
    assert verify_res.json()["data"]["email"] == "ada.lovelace@calyx.ai"

    # 3. Test /me profile endpoint
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["full_name"] == "Ada Lovelace"

    # 4. Test /refresh endpoint
    refresh_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.json()["data"]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
