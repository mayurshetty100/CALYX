# ==============================================================================
# CALYX AGENT SERVICE: AUTOMATED TEST SUITE
# ==============================================================================
# Concept Explanation for Beginners:
# This automated test suite verifies:
# 1. Redis state store connectivity and health probes.
# 2. Execution of the 4 autonomous agents in sequence:
#    - Extraction & Normalization
#    - Criteria & Rubric Matching
#    - Fairness & Bias Auditing
#    - Dynamic Technical Interview Synthesis
# 3. Transparent audit trail retrieval from Redis (`agent:trace:{task_id}`).
# ==============================================================================

import pytest
from fastapi.testclient import TestClient
from services.calyx_agent_service.main import app
from services.calyx_agent_service.state_store import get_state_store, get_redis_client, AgentStateStore


@pytest.fixture(scope="module")
def client():
    """
    TestClient fixture configured with in-memory fakeredis engine.
    """
    # Force mock Redis for tests
    mock_redis = get_redis_client(force_mock=True)
    test_store = AgentStateStore(client=mock_redis)
    app.dependency_overrides[get_state_store] = lambda: test_store

    with TestClient(app) as test_client:
        yield test_client


def test_01_health_probes(client):
    """
    Tests Kubernetes Liveness and Readiness probes against Redis.
    """
    live_res = client.get("/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "alive"

    ready_res = client.get("/health/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"
    assert "Redis" in ready_res.json()["database"]


def test_02_evaluate_candidate_application(client):
    """
    Tests full multi-agent consensus evaluation on a Senior Cloud Engineer applicant.
    """
    payload = {
        "application_id": "app_cloud_999",
        "candidate_profile": {
            "candidate_id": 401,
            "candidate_name": "Jordan Lee",
            "skills": ["k8s", "docker", "python", "fastapi", "terraform", "hpa"],
            "experience_years": 6,
            "raw_text_preview": (
                "Lead Cloud Engineer with 6 years experience building Kubernetes microservices "
                "with Horizontal Pod Autoscaler and FastAPI backends."
            )
        },
        "job_requirements": {
            "title": "Senior Cloud Infrastructure Engineer",
            "min_years_exp": 5,
            "required_skills": [
                {"name": "Kubernetes", "weight": 1.0},
                {"name": "Docker", "weight": 0.9},
                {"name": "Python", "weight": 0.8}
            ],
            "rubric_criteria": [
                {"category": "Cloud & Container Orchestration", "weight": 0.5, "description": "Hands-on K8s and Docker"},
                {"category": "Distributed Systems", "weight": 0.5, "description": "Microservices and concurrency"}
            ]
        }
    }

    res = client.post("/api/v1/agents/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()["data"]
    
    assert "task_id" in data
    assert data["status"] == "COMPLETED"
    assert data["final_score"] >= 80.0
    assert "Cloud" in data["detected_specialty"]

    # Verify Fairness Audit Agent results
    audit = data["fairness_audit"]
    assert audit["audit_passed"] is True
    assert "AUDIT-" in audit["audit_token"]

    # Verify Technical Interview Synthesizer results
    questions = data["interview_questionnaire"]
    assert len(questions) >= 3
    assert any("Autoscaling" in q["focus_area"] or "Kubernetes" in q["focus_area"] for q in questions)
    assert "ideal_response_key" in questions[0]

    pytest.shared_task_id = data["task_id"]


def test_03_retrieve_task_from_redis(client):
    """
    Verifies that the completed task state is successfully retrieved from Redis.
    """
    task_id = pytest.shared_task_id
    res = client.get(f"/api/v1/agents/tasks/{task_id}")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["task_id"] == task_id
    assert data["status"] == "COMPLETED"
    assert "executive_summary" in data


def test_04_retrieve_reasoning_trace_from_redis(client):
    """
    Verifies that the complete Explainable AI (XAI) multi-agent reasoning trace
    is logged in Redis and retrieved successfully.
    """
    task_id = pytest.shared_task_id
    res = client.get(f"/api/v1/agents/tasks/{task_id}/trace")
    assert res.status_code == 200
    steps = res.json()["data"]["steps"]
    
    # 4 distinct agents should have logged their reasoning steps
    assert len(steps) >= 4
    agent_names = [s["agent"] for s in steps]
    assert "Extraction & Normalization Agent" in agent_names
    assert "Criteria & Rubric Matching Agent" in agent_names
    assert "Fairness & Bias Audit Agent" in agent_names
    assert "Dynamic Technical Interview Synthesizer Agent" in agent_names


if __name__ == "__main__":
    pytest.main(["-v", __file__])
