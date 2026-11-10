# ==============================================================================
# CALYX JOB SERVICE: AUTOMATED TEST SUITE
# ==============================================================================
# Concept Explanation for Beginners:
# Microservices communicate using standard HTTP contracts and cryptographically
# signed JWT tokens. In this test suite, we simulate:
# 1. A Recruiter creating a job requisition with skill rubrics.
# 2. A Candidate discovering the job and submitting an application.
# 3. An autonomous Agent service persisting AI evaluation results back to the job record.
# Notice how we test the whole lifecycle without needing any external servers running!
# ==============================================================================

import pytest
from fastapi.testclient import TestClient
from common.security import create_access_token
from services.calyx_job_service.main import app
from services.calyx_job_service.database import init_db
from services.calyx_job_service.config import job_settings


@pytest.fixture(scope="module")
def client():
    """
    TestClient fixture that initializes the MongoDB in-memory mock engine.
    """
    init_db(force_mock=True)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def recruiter_token():
    """
    Generates a valid JWT access token for Recruiter ID 101.
    """
    return create_access_token(
        subject="101",
        role="recruiter",
        secret_key=job_settings.JWT_SECRET_KEY,
        algorithm=job_settings.JWT_ALGORITHM,
        extra_claims={"email": "recruiter@calyx.ai"}
    )


@pytest.fixture(scope="module")
def candidate_token():
    """
    Generates a valid JWT access token for Candidate ID 202.
    """
    return create_access_token(
        subject="202",
        role="candidate",
        secret_key=job_settings.JWT_SECRET_KEY,
        algorithm=job_settings.JWT_ALGORITHM,
        extra_claims={"email": "candidate@calyx.ai"}
    )


def test_01_health_probes(client):
    """
    Verifies that Kubernetes Liveness and Readiness probes return HTTP 200 OK.
    """
    live_res = client.get("/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "alive"

    ready_res = client.get("/health/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"


def test_02_create_job_posting(client, recruiter_token):
    """
    Tests recruiter posting a new job requisition with skills and rubrics.
    """
    headers = {"Authorization": f"Bearer {recruiter_token}"}
    payload = {
        "title": "Lead Cloud Infrastructure Engineer",
        "department": "Platform Engineering",
        "location": "Remote",
        "employment_type": "full_time",
        "experience_level": "lead",
        "min_years_exp": 6,
        "salary_min": 140000,
        "salary_max": 180000,
        "salary_currency": "USD",
        "description": "We are seeking a Lead Cloud Engineer to design microservice architectures on Kubernetes.",
        "required_skills": [
            {"name": "Kubernetes", "weight": 1.0, "required": True},
            {"name": "Python", "weight": 0.9, "required": True},
            {"name": "Docker", "weight": 0.8, "required": True}
        ],
        "nice_to_have_skills": ["Terraform", "Prometheus", "FastAPI"],
        "rubric_criteria": [
            {"category": "Container Orchestration", "weight": 0.4, "description": "Hands-on K8s HPA and ingress experience"},
            {"category": "Distributed Systems", "weight": 0.4, "description": "Microservices and polyglot persistence"},
            {"category": "Architecture Design", "weight": 0.2, "description": "Cloud-native system design"}
        ],
        "screening_questions": [
            {"question_id": "q1", "question_text": "Describe your experience scaling Kubernetes pods with HPA.", "required": True}
        ]
    }
    res = client.post("/api/v1/jobs", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()["data"]
    assert "id" in data
    assert data["title"] == "Lead Cloud Infrastructure Engineer"
    assert data["recruiter_id"] == 101
    assert data["status"] == "published"
    assert data["total_applicants"] == 0

    # Save job_id for subsequent tests
    pytest.shared_job_id = data["id"]


def test_03_search_and_list_jobs(client):
    """
    Tests public job search and filtering by keyword and department.
    """
    # 1. Search by department
    res = client.get("/api/v1/jobs?department=Platform Engineering")
    assert res.status_code == 200
    assert len(res.json()["data"]["jobs"]) >= 1

    # 2. Search by keyword
    kw_res = client.get("/api/v1/jobs?keyword=Infrastructure")
    assert kw_res.status_code == 200
    assert len(kw_res.json()["data"]["jobs"]) >= 1

    # 3. Fetch single job by ID
    job_id = pytest.shared_job_id
    detail_res = client.get(f"/api/v1/jobs/{job_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["id"] == job_id


def test_04_candidate_submit_application(client, candidate_token):
    """
    Tests a candidate submitting an application for the job.
    """
    job_id = pytest.shared_job_id
    headers = {"Authorization": f"Bearer {candidate_token}"}
    payload = {
        "job_id": job_id,
        "resume_id": "res_abc_12345",
        "answers": [
            {"question_id": "q1", "answer_text": "I have configured HPA with CPU and custom metrics across 50 nodes."}
        ]
    }
    res = client.post(f"/api/v1/jobs/{job_id}/apply", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["job_id"] == job_id
    assert data["candidate_id"] == 202
    assert data["status"] == "submitted"
    assert data["resume_id"] == "res_abc_12345"

    pytest.shared_application_id = data["id"]


def test_05_prevent_duplicate_application(client, candidate_token):
    """
    Verifies that a candidate cannot apply to the same job opening twice.
    """
    job_id = pytest.shared_job_id
    headers = {"Authorization": f"Bearer {candidate_token}"}
    payload = {
        "job_id": job_id,
        "resume_id": "res_duplicate_attempt",
        "answers": []
    }
    res = client.post(f"/api/v1/jobs/{job_id}/apply", json=payload, headers=headers)
    assert res.status_code == 409
    assert res.json()["success"] is False


def test_06_recruiter_view_applications(client, recruiter_token):
    """
    Tests recruiter viewing the candidate pipeline for their job.
    """
    job_id = pytest.shared_job_id
    headers = {"Authorization": f"Bearer {recruiter_token}"}
    res = client.get(f"/api/v1/jobs/{job_id}/applications", headers=headers)
    assert res.status_code == 200
    apps = res.json()["data"]
    assert len(apps) == 1
    assert apps[0]["candidate_id"] == 202


def test_07_agent_service_evaluation_callback(client):
    """
    Tests the internal endpoint called by calyx-agent-service
    to record the AI evaluation match score and multi-agent critique.
    """
    app_id = pytest.shared_application_id
    eval_payload = {
        "match_score": 94.5,
        "agent_summary": (
            "Multi-Agent Consensus: Candidate demonstrates exceptional Kubernetes orchestration "
            "and distributed systems expertise. Strongly recommended for technical interview round."
        ),
        "status": "agent_evaluated"
    }
    res = client.patch(f"/api/v1/applications/{app_id}/evaluation", json=eval_payload)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["match_score"] == 94.5
    assert data["status"] == "agent_evaluated"
    assert "Multi-Agent Consensus" in data["agent_summary"]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
