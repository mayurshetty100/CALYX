# ==============================================================================
# CALYX ANALYTICS SERVICE: AUTOMATED TEST SUITE
# ==============================================================================
# Concept Explanation for Beginners:
# This automated test suite verifies:
# 1. Kubernetes health probes for the Analytics microservice.
# 2. Ingesting asynchronous pipeline events from upstream services.
# 3. Computing conversion funnels and score histograms for recruiter dashboards.
# ==============================================================================

import pytest
from fastapi.testclient import TestClient
from services.calyx_analytics_service.main import app
from services.calyx_analytics_service.database import Base, engine


@pytest.fixture(scope="module")
def client():
    """
    TestClient fixture that sets up fresh analytics database tables.
    """
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


def test_01_health_probes(client):
    """
    Tests Kubernetes Liveness and Readiness probes.
    """
    live_res = client.get("/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "alive"

    ready_res = client.get("/health/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"


def test_02_record_pipeline_events(client):
    """
    Tests ingesting various pipeline events and verifies persistence.
    """
    target_job = "job_k8s_777"

    # Event 1: Application submitted
    client.post("/api/v1/analytics/events", json={
        "event_type": "APPLICATION_SUBMITTED",
        "entity_id": "app_01",
        "user_id": 501,
        "metadata": {"job_id": target_job}
    })

    # Event 2: Agent evaluation completed (Score 92.5)
    eval1 = client.post("/api/v1/analytics/events", json={
        "event_type": "AGENT_EVALUATION_COMPLETED",
        "entity_id": "app_01",
        "user_id": 501,
        "metadata": {"job_id": target_job, "score": 92.5}
    })
    assert eval1.status_code == 201

    # Event 3: Another candidate evaluation (Score 78.0)
    eval2 = client.post("/api/v1/analytics/events", json={
        "event_type": "AGENT_EVALUATION_COMPLETED",
        "entity_id": "app_02",
        "user_id": 502,
        "metadata": {"job_id": target_job, "score": 78.0}
    })
    assert eval2.status_code == 201

    # Event 4: Interview scheduled
    client.post("/api/v1/analytics/events", json={
        "event_type": "INTERVIEW_SCHEDULED",
        "entity_id": "app_01",
        "user_id": 501,
        "metadata": {"job_id": target_job, "round": "Technical"}
    })

    # Event 5: Offer extended
    client.post("/api/v1/analytics/events", json={
        "event_type": "OFFER_EXTENDED",
        "entity_id": "app_01",
        "user_id": 501,
        "metadata": {"job_id": target_job}
    })


def test_03_dashboard_overview(client):
    """
    Tests executive dashboard metrics and funnel conversion calculation.
    """
    res = client.get("/api/v1/analytics/dashboard")
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["total_events_recorded"] >= 5
    assert data["total_applications_evaluated"] >= 2
    assert data["average_pipeline_score"] > 80.0

    funnel = data["status_funnel"]
    assert funnel["applications_submitted"] >= 1
    assert funnel["agent_evaluations_completed"] >= 2
    assert funnel["interviews_scheduled"] >= 1
    assert funnel["offers_extended"] >= 1


def test_04_job_score_distribution(client):
    """
    Tests score distribution histogram for job_k8s_777.
    """
    res = client.get("/api/v1/analytics/jobs/job_k8s_777/distribution")
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["job_id"] == "job_k8s_777"
    assert data["total_applicants"] == 2
    assert data["highest_score"] == 92.5
    assert data["lowest_score"] == 78.0

    brackets = data["score_brackets"]
    assert brackets["top_tier_85_100"] == 1  # 92.5
    assert brackets["strong_70_84"] == 1     # 78.0


if __name__ == "__main__":
    pytest.main(["-v", __file__])
