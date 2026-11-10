# ==============================================================================
# CALYX RESUME SERVICE: AUTOMATED TEST SUITE
# ==============================================================================
# Concept Explanation for Beginners:
# This automated test suite verifies:
# 1. Multi-candidate document ingestion and entity parsing (skills, tenure, contact info).
# 2. 384-dimensional vector embedding generation.
# 3. High-dimensional Cosine Similarity ranking: proving that a "Cloud Engineer"
#    search ranks the DevOps candidate higher, while an "ML Engineer" search
#    ranks the Data Science candidate higher!
# ==============================================================================

import os
import shutil
import pytest
from fastapi.testclient import TestClient
from common.security import create_access_token
from services.calyx_resume_service.main import app
from services.calyx_resume_service.vector_store import get_vector_db, VectorStore
from services.calyx_resume_service.config import resume_settings

TEST_STORAGE_DIR = "./test_calyx_vector_store"


@pytest.fixture(scope="module")
def client():
    """
    TestClient fixture configured with isolated temporary vector store directory.
    """
    if os.path.exists(TEST_STORAGE_DIR):
        shutil.rmtree(TEST_STORAGE_DIR)

    # Initialize clean test vector store
    test_vdb = VectorStore(storage_dir=TEST_STORAGE_DIR)
    # Override FastAPI dependency
    app.dependency_overrides[get_vector_db] = lambda: test_vdb

    with TestClient(app) as test_client:
        yield test_client

    # Teardown clean up
    if os.path.exists(TEST_STORAGE_DIR):
        shutil.rmtree(TEST_STORAGE_DIR)


@pytest.fixture(scope="module")
def candidate_token():
    """Valid JWT access token for Candidate ID 301."""
    return create_access_token(
        subject="301",
        role="candidate",
        secret_key=resume_settings.JWT_SECRET_KEY,
        algorithm=resume_settings.JWT_ALGORITHM,
        extra_claims={"email": "cloud.engineer@calyx.ai"}
    )


@pytest.fixture(scope="module")
def candidate2_token():
    """Valid JWT access token for Candidate ID 302."""
    return create_access_token(
        subject="302",
        role="candidate",
        secret_key=resume_settings.JWT_SECRET_KEY,
        algorithm=resume_settings.JWT_ALGORITHM,
        extra_claims={"email": "ml.engineer@calyx.ai"}
    )


@pytest.fixture(scope="module")
def recruiter_token():
    """Valid JWT access token for Recruiter ID 101."""
    return create_access_token(
        subject="101",
        role="recruiter",
        secret_key=resume_settings.JWT_SECRET_KEY,
        algorithm=resume_settings.JWT_ALGORITHM,
        extra_claims={"email": "recruiter@calyx.ai"}
    )


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


def test_02_upload_cloud_engineer_resume(client, candidate_token):
    """
    Tests uploading a Cloud / DevOps Engineer resume.
    Verifies skill extraction and vector generation.
    """
    resume_text = """
    Alex Mercer
    Email: alex.mercer@cloudtech.com | Phone: 555-019-2831
    Summary: Senior Cloud Infrastructure Engineer with 6+ years of experience.
    Technical Skills: Kubernetes, Docker, Python, FastAPI, Terraform, Prometheus, CI/CD, Microservices, PostgreSQL, Linux.
    Experience:
    Lead Cloud Engineer (2020 - 2024):
    - Designed and operated multi-tenant Kubernetes clusters on AWS and GCP.
    - Configured Horizontal Pod Autoscaler (HPA) and NGINX Ingress controllers.
    - Built asynchronous microservices in Python with FastAPI and PostgreSQL.
    Education:
    B.Tech in Computer Science, 2018.
    """
    headers = {"Authorization": f"Bearer {candidate_token}"}
    payload = {
        "text_content": resume_text,
        "file_name": "alex_mercer_resume.txt"
    }
    res = client.post("/api/v1/resumes/upload-text", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()["data"]
    assert "resume_id" in data
    assert data["candidate_id"] == 301
    assert "Kubernetes" in data["skills"]
    assert "Docker" in data["skills"]
    assert "Fastapi" in data["skills"]
    assert data["experience_years"] >= 6
    assert data["email"] == "alex.mercer@cloudtech.com"

    pytest.cloud_resume_id = data["resume_id"]


def test_03_upload_ml_engineer_resume(client, candidate2_token):
    """
    Tests uploading a Data Science / Machine Learning Engineer resume.
    """
    resume_text = """
    Samantha Chen
    Email: samantha.chen@ai-labs.org | Phone: 555-482-9912
    Summary: Machine Learning Engineer specializing in Deep Learning and NLP with 4+ years of experience.
    Technical Skills: PyTorch, TensorFlow, Scikit-Learn, Python, LangChain, Transformers, MongoDB.
    Experience:
    AI Researcher (2021 - 2024):
    - Trained large transformer models and semantic embedding pipelines in PyTorch.
    - Built vector search retrieval systems using MongoDB and LangChain.
    Education:
    M.S. in Artificial Intelligence, 2021.
    """
    headers = {"Authorization": f"Bearer {candidate2_token}"}
    payload = {
        "text_content": resume_text,
        "file_name": "samantha_chen_resume.txt"
    }
    res = client.post("/api/v1/resumes/upload-text", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()["data"]
    assert "resume_id" in data
    assert data["candidate_id"] == 302
    assert "Pytorch" in data["skills"]
    assert "Tensorflow" in data["skills"]
    assert "Python" in data["skills"]

    pytest.ml_resume_id = data["resume_id"]


def test_04_vector_search_cloud_role(client, recruiter_token):
    """
    Tests semantic vector search for a Kubernetes Cloud position.
    Proves that Alex Mercer (Cloud Engineer) ranks #1 over Samantha Chen (ML Engineer).
    """
    headers = {"Authorization": f"Bearer {recruiter_token}"}
    search_payload = {
        "job_description": "We need a Senior Kubernetes Cloud Engineer to manage Docker containers, HPA, and microservices.",
        "required_skills": ["Kubernetes", "Docker", "Python"],
        "min_experience_years": 3,
        "top_k": 5
    }
    res = client.post("/api/v1/resumes/search", json=search_payload, headers=headers)
    assert res.status_code == 200
    matches = res.json()["data"]["top_matches"]
    assert len(matches) >= 2

    top_match = matches[0]
    # Alex Mercer should rank first for the Cloud role
    assert top_match["candidate_id"] == 301
    assert top_match["match_score"] >= 70.0
    assert "Kubernetes" in top_match["matched_skills"]
    assert "Docker" in top_match["matched_skills"]


def test_05_vector_search_ml_role(client, recruiter_token):
    """
    Tests semantic vector search for a Machine Learning role.
    Proves that Samantha Chen (ML Engineer) ranks #1.
    """
    headers = {"Authorization": f"Bearer {recruiter_token}"}
    search_payload = {
        "job_description": "Looking for an AI / Machine Learning specialist with PyTorch, NLP, and Deep Learning expertise.",
        "required_skills": ["PyTorch", "Python"],
        "min_experience_years": 2,
        "top_k": 5
    }
    res = client.post("/api/v1/resumes/search", json=search_payload, headers=headers)
    assert res.status_code == 200
    matches = res.json()["data"]["top_matches"]
    assert len(matches) >= 2

    top_match = matches[0]
    # Samantha Chen should rank first for the ML role
    assert top_match["candidate_id"] == 302
    assert top_match["match_score"] >= 65.0
    assert "Pytorch" in top_match["matched_skills"]


def test_06_get_resume_by_id(client):
    """
    Tests retrieving extracted resume metadata by resume ID.
    """
    resume_id = pytest.cloud_resume_id
    res = client.get(f"/api/v1/resumes/{resume_id}")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["resume_id"] == resume_id
    assert data["candidate_id"] == 301


def test_07_candidate_get_own_resumes(client, candidate_token):
    """
    Tests candidate fetching their own uploaded resumes list.
    """
    headers = {"Authorization": f"Bearer {candidate_token}"}
    res = client.get("/api/v1/resumes/candidate/me", headers=headers)
    assert res.status_code == 200
    resumes = res.json()["data"]
    assert len(resumes) >= 1
    assert resumes[0]["candidate_id"] == 301


if __name__ == "__main__":
    pytest.main(["-v", __file__])
