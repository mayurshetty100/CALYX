# ==============================================================================
# CALYX END-TO-END INTEGRATION TEST SUITE
# ==============================================================================
# Concept Explanation for Beginners:
# This integration suite exercises the entire recruitment journey across all
# FIVE decoupled microservices working together:
# 1. Identity & Auth Service: Registers Recruiter and Candidate, issues JWTs.
# 2. Job Service: Recruiter creates a job requisition with custom rubrics.
# 3. Resume Service: Candidate uploads resume; system generates 384-dim vector embedding.
# 4. Job Service: Candidate submits job application.
# 5. Agentic AI Service: Coordinates 4 autonomous agents (Extraction, Rubric Match,
#    Fairness Audit, Interview Synthesis) with Redis state tracking.
# 6. Analytics Service: Ingests pipeline events and computes executive funnel metrics!
# ==============================================================================

import os
import shutil
import pytest
from fastapi.testclient import TestClient

# Import all microservice applications
from services.calyx_auth_service.main import app as auth_app
from services.calyx_job_service.main import app as job_app
from services.calyx_resume_service.main import app as resume_app
from services.calyx_agent_service.main import app as agent_app
from services.calyx_analytics_service.main import app as analytics_app

# Import database initializers
from services.calyx_auth_service.database import Base as AuthBase, engine as auth_engine
from services.calyx_job_service.database import init_db as init_job_db
from services.calyx_resume_service.vector_store import VectorStore, get_vector_db
from services.calyx_agent_service.state_store import get_state_store, get_redis_client, AgentStateStore
from services.calyx_analytics_service.database import Base as AnalyticsBase, engine as analytics_engine

TEST_VECTOR_DIR = "./test_e2e_vector_store"


@pytest.fixture(scope="module")
def e2e_clients():
    """
    Sets up isolated test clients for all 5 microservices with clean databases.
    """
    # 1. Auth DB Setup
    AuthBase.metadata.drop_all(bind=auth_engine)
    AuthBase.metadata.create_all(bind=auth_engine)
    auth_c = TestClient(auth_app)

    # 2. Job DB Setup (in-memory mock)
    init_job_db(force_mock=True)
    job_c = TestClient(job_app)

    # 3. Resume DB Setup (isolated vector store)
    if os.path.exists(TEST_VECTOR_DIR):
        shutil.rmtree(TEST_VECTOR_DIR)
    vdb = VectorStore(storage_dir=TEST_VECTOR_DIR)
    resume_app.dependency_overrides[get_vector_db] = lambda: vdb
    resume_c = TestClient(resume_app)

    # 4. Agent State Store (in-memory mock Redis)
    mock_redis = get_redis_client(force_mock=True)
    agent_store = AgentStateStore(client=mock_redis)
    agent_app.dependency_overrides[get_state_store] = lambda: agent_store
    agent_c = TestClient(agent_app)

    # 5. Analytics DB Setup
    AnalyticsBase.metadata.drop_all(bind=analytics_engine)
    AnalyticsBase.metadata.create_all(bind=analytics_engine)
    analytics_c = TestClient(analytics_app)

    yield {
        "auth": auth_c,
        "job": job_c,
        "resume": resume_c,
        "agent": agent_c,
        "analytics": analytics_c
    }

    # Teardown
    if os.path.exists(TEST_VECTOR_DIR):
        shutil.rmtree(TEST_VECTOR_DIR)
    AuthBase.metadata.drop_all(bind=auth_engine)
    AnalyticsBase.metadata.drop_all(bind=analytics_engine)


def test_full_autonomous_recruitment_lifecycle(e2e_clients):
    """
    Simulates the complete end-to-end recruitment lifecycle from registration
    to AI agent evaluation and analytics reporting.
    """
    auth = e2e_clients["auth"]
    job = e2e_clients["job"]
    resume = e2e_clients["resume"]
    agent = e2e_clients["agent"]
    analytics = e2e_clients["analytics"]

    # --------------------------------------------------------------------------
    # STAGE 1: Authentication & Identity Management
    # --------------------------------------------------------------------------
    # 1a. Register Recruiter
    recruiter_res = auth.post("/api/v1/auth/register", json={
        "email": "sarah.connor@cyberdyne.io",
        "password": "Password123!",
        "full_name": "Sarah Connor",
        "role": "recruiter"
    })
    assert recruiter_res.status_code == 201

    # 1b. Login Recruiter & obtain JWT
    recruiter_login = auth.post("/api/v1/auth/login", json={
        "email": "sarah.connor@cyberdyne.io",
        "password": "Password123!"
    })
    assert recruiter_login.status_code == 200
    recruiter_token = recruiter_login.json()["data"]["access_token"]
    recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}

    # 1c. Register Candidate
    cand_res = auth.post("/api/v1/auth/register", json={
        "email": "john.doe@clouddev.org",
        "password": "Password123!",
        "full_name": "John Doe",
        "role": "candidate"
    })
    assert cand_res.status_code == 201
    candidate_id = cand_res.json()["data"]["id"]

    # 1d. Login Candidate & obtain JWT
    cand_login = auth.post("/api/v1/auth/login", json={
        "email": "john.doe@clouddev.org",
        "password": "Password123!"
    })
    assert cand_login.status_code == 200
    cand_token = cand_login.json()["data"]["access_token"]
    cand_headers = {"Authorization": f"Bearer {cand_token}"}

    # --------------------------------------------------------------------------
    # STAGE 2: Recruiter Creates Job Requisition
    # --------------------------------------------------------------------------
    job_payload = {
        "title": "Principal Kubernetes Platform Engineer",
        "department": "Infrastructure & Core Services",
        "location": "Remote",
        "employment_type": "full_time",
        "experience_level": "lead",
        "min_years_exp": 5,
        "salary_min": 160000,
        "salary_max": 200000,
        "salary_currency": "USD",
        "description": "Architect cloud-native Kubernetes infrastructure, HPA autoscaling, and microservices mesh.",
        "required_skills": [
            {"name": "Kubernetes", "weight": 1.0, "required": True},
            {"name": "Docker", "weight": 0.9, "required": True},
            {"name": "Python", "weight": 0.8, "required": True}
        ],
        "rubric_criteria": [
            {"category": "Cloud Orchestration", "weight": 0.5, "description": "Production K8s and HPA"},
            {"category": "Distributed Architecture", "weight": 0.5, "description": "Microservices and resilient messaging"}
        ]
    }
    create_job_res = job.post("/api/v1/jobs", json=job_payload, headers=recruiter_headers)
    assert create_job_res.status_code == 201
    job_id = create_job_res.json()["data"]["id"]

    # --------------------------------------------------------------------------
    # STAGE 3: Candidate Uploads Resume (Text & Vector Ingestion)
    # --------------------------------------------------------------------------
    resume_content = """
    John Doe
    Email: john.doe@clouddev.org | Phone: 555-901-2345
    Summary: Lead Cloud Architect with 7+ years of experience specializing in Kubernetes and distributed microservices.
    Technical Skills: Kubernetes, Docker, Python, FastAPI, Terraform, PostgreSQL, Microservices, Prometheus, HPA.
    Experience:
    Senior Platform Engineer (2019 - 2024):
    - Architected multi-region Kubernetes clusters handling 50,000 requests/second.
    - Implemented Horizontal Pod Autoscalers (HPA) and Istio service mesh.
    - Designed Python FastAPI microservices with PostgreSQL polyglot persistence.
    Education:
    B.S. in Computer Engineering, 2017.
    """
    resume_upload_res = resume.post("/api/v1/resumes/upload-text", json={
        "text_content": resume_content,
        "file_name": "john_doe_resume.txt"
    }, headers=cand_headers)
    assert resume_upload_res.status_code == 201
    resume_data = resume_upload_res.json()["data"]
    resume_id = resume_data["resume_id"]
    assert "Kubernetes" in resume_data["skills"]

    # --------------------------------------------------------------------------
    # STAGE 4: Candidate Applies to Job
    # --------------------------------------------------------------------------
    apply_res = job.post(f"/api/v1/jobs/{job_id}/apply", json={
        "job_id": job_id,
        "resume_id": resume_id,
        "answers": []
    }, headers=cand_headers)
    assert apply_res.status_code == 201
    application_id = apply_res.json()["data"]["id"]

    # Log application submitted event to Analytics Service
    analytics.post("/api/v1/analytics/events", json={
        "event_type": "APPLICATION_SUBMITTED",
        "entity_id": application_id,
        "user_id": candidate_id,
        "metadata": {"job_id": job_id}
    })

    # --------------------------------------------------------------------------
    # STAGE 5: Semantic Vector Search
    # --------------------------------------------------------------------------
    search_res = resume.post("/api/v1/resumes/search", json={
        "job_description": "We need an expert in Kubernetes cluster scaling and microservices architecture.",
        "required_skills": ["Kubernetes", "Docker", "Python"],
        "min_experience_years": 4,
        "top_k": 5
    }, headers=recruiter_headers)
    assert search_res.status_code == 200
    top_candidates = search_res.json()["data"]["top_matches"]
    assert len(top_candidates) >= 1
    assert top_candidates[0]["candidate_id"] == candidate_id

    # --------------------------------------------------------------------------
    # STAGE 6: Autonomous Agentic AI Evaluation
    # --------------------------------------------------------------------------
    eval_res = agent.post("/api/v1/agents/evaluate", json={
        "application_id": application_id,
        "candidate_profile": {
            "candidate_id": candidate_id,
            "candidate_name": "John Doe",
            "skills": resume_data["skills"],
            "experience_years": resume_data["experience_years"],
            "raw_text_preview": resume_content
        },
        "job_requirements": job_payload
    })
    assert eval_res.status_code == 200
    eval_data = eval_res.json()["data"]
    task_id = eval_data["task_id"]
    final_score = eval_data["final_score"]
    assert final_score >= 80.0
    assert eval_data["fairness_audit"]["audit_passed"] is True
    assert len(eval_data["interview_questionnaire"]) >= 3

    # Verify transparent reasoning trace in Redis
    trace_res = agent.get(f"/api/v1/agents/tasks/{task_id}/trace")
    assert trace_res.status_code == 200
    steps = trace_res.json()["data"]["steps"]
    assert len(steps) >= 4

    # --------------------------------------------------------------------------
    # STAGE 7: Job Service Persists AI Score & Recruiter Views Pipeline
    # --------------------------------------------------------------------------
    job.patch(f"/api/v1/applications/{application_id}/evaluation", json={
        "match_score": final_score,
        "agent_summary": eval_data["executive_summary"],
        "status": "agent_evaluated"
    })

    # Recruiter inspects candidate pipeline
    pipeline_res = job.get(f"/api/v1/jobs/{job_id}/applications", headers=recruiter_headers)
    assert pipeline_res.status_code == 200
    apps = pipeline_res.json()["data"]
    assert len(apps) == 1
    assert apps[0]["match_score"] == final_score
    assert apps[0]["status"] == "agent_evaluated"

    # Log evaluation completed to Analytics Service
    analytics.post("/api/v1/analytics/events", json={
        "event_type": "AGENT_EVALUATION_COMPLETED",
        "entity_id": application_id,
        "user_id": candidate_id,
        "metadata": {"job_id": job_id, "score": final_score}
    })

    # --------------------------------------------------------------------------
    # STAGE 8: Analytics Executive Dashboard
    # --------------------------------------------------------------------------
    dash_res = analytics.get("/api/v1/analytics/dashboard")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()["data"]
    assert dash_data["total_events_recorded"] >= 2
    assert dash_data["average_pipeline_score"] >= 80.0

    print(f"\n=======================================================")
    print(f"E2E RECRUITMENT LIFECYCLE COMPLETED SUCCESSFULLY!")
    print(f"Candidate: John Doe (ID: {candidate_id})")
    print(f"Job: Principal Kubernetes Platform Engineer (ID: {job_id})")
    print(f"Agentic AI Match Score: {final_score}%")
    print(f"Fairness Audit: PASSED (Token: {eval_data['fairness_audit']['audit_token']})")
    print(f"Synthesized Technical Questions: {len(eval_data['interview_questionnaire'])}")
    print(f"=======================================================")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
