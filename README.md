# CALYX: Autonomous Agentic AI Smart Hiring & Talent Screening Platform

[![Kubernetes](https://img.shields.io/badge/Kubernetes-HPA_Autoscaling-326CE5?logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![Microservices](https://img.shields.io/badge/Architecture-Polyglot_Microservices-blue)](#architecture-blueprint)
[![Database-per-Service](https://img.shields.io/badge/Pattern-Database--per--Service-green)](#database-per-service-matrix)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.162-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 1. Executive Summary & Pitch
**CALYX** is a production-grade, cloud-native enterprise recruitment intelligence platform driven by an **Agentic AI Multi-Agent Mesh**. 

CALYX dissects the hiring workflow into five decoupled microservices adhering strictly to the **Database-per-Service pattern**. It automates multi-format resume ingestion (PDF, Word, Text), extracts 384-dimensional dense semantic vector embeddings, performs Cosine Similarity candidate matching, and runs a collaborative 4-agent reasoning consensus loop (Normalization, Rubric Matching, Fairness/Bias Audit, and Dynamic Technical Interview Synthesis).

The platform is fully containerized and orchestrated on **Kubernetes**, featuring **Horizontal Pod Autoscaling (HPA)** to autoscale under massive applicant surges.

---

## 2. Architecture Blueprint

```
                                  ┌───────────────────────────────┐
                                  │      Client Browser / UI      │
                                  └───────────────┬───────────────┘
                                                  │ HTTP / REST
                                  ┌───────────────▼───────────────┐
                                  │   Kubernetes Ingress Gateway  │
                                  └───┬───────────┬───────────┬───┘
                                      │           │           │
                     ┌────────────────┘           │           └────────────────┐
                     ▼                            ▼                            ▼
              /api/v1/auth/*               /api/v1/jobs/*               /api/v1/resumes/*
              ┌──────────────┐             ┌──────────────┐             ┌──────────────┐
              │  calyx-auth  │             │  calyx-job   │             │ calyx-resume │
              │   service    │             │   service    │             │   service    │
              └──────┬───────┘             └──────┬───────┘             └──────┬───────┘
                     │                            │                            │
               ┌─────▼──────┐               ┌─────▼──────┐               ┌─────▼──────┐
               │ PostgreSQL │               │  MongoDB   │               │  VectorDB  │
               │  Auth DB   │               │   Job DB   │               │ (Embeddings│
               └────────────┘               └────────────┘               └────────────┘
                                                  ▲                            ▲
                                                  │ Async Tasks / gRPC         │
                                           ┌──────┴───────┐                    │
                                           │ calyx-agent  │────────────────────┘
                                           │   service    │
                                           └──────┬───────┘
                                                  │
                                            ┌─────▼──────┐
                                            │   Redis    │
                                            │State & Lock│
                                            └────────────┘
                                                  │ Events
                                           ┌──────▼───────┐
                                           │calyx-analytic│
                                           └──────┬───────┘
                                                  │
                                            ┌─────▼──────┐
                                            │Analytics DB│
                                            └────────────┘
```

---

## 3. Database-per-Service Matrix

Every microservice strictly owns its persistent datastore. No service directly queries another service's database:

| Microservice | Primary Responsibility | Dedicated Database | Storage Justification |
| :--- | :--- | :--- | :--- |
| **`calyx-auth-service`** | User registration, login, RBAC, JWT rotation | **PostgreSQL** | Relational ACID guarantees for sensitive credentials, audit logs, and token hashes. |
| **`calyx-job-service`** | Job postings, hiring rubrics, applications | **MongoDB** | Flexible NoSQL document model for dynamic screening questions and nested candidate answers. |
| **`calyx-resume-service`**| PDF parsing, 384-dim vector embeddings | **Vector Database** | Specialized multi-dimensional spatial indexing and sub-millisecond Cosine Similarity (ANN) search. |
| **`calyx-agent-service`** | 4-agent reasoning consensus & XAI traces | **Redis** | Microsecond in-memory key-value store, distributed locks (`SETNX`), and async queues. |
| **`calyx-analytics-service`**| Pipeline conversion funnels & score histograms | **PostgreSQL Analytics** | Time-stamped event sourcing and materialized dashboard summaries. |

---

## 4. The 4 Autonomous Agents (Agentic AI Mesh)

1. **Extraction & Normalization Agent**: Cleans resume text, maps colloquial synonyms (e.g. "k8s admin" -> "Kubernetes Orchestration"), and identifies candidate engineering specialties.
2. **Criteria & Rubric Matching Agent**: Grades candidates against recruiter hiring rubrics (System Design, Concurrency, Architecture) with weighted mathematical justification.
3. **Fairness & Bias Audit Agent**: Objective ethics auditor that scrubs demographic signals (gender, age, ethnicity) and verifies that scoring is 100% merit-based, issuing an immutable audit certificate (`AUDIT-XXXX`).
4. **Dynamic Technical Interview Synthesizer Agent**: Pinpoints candidate blindspots and synthesizes 3-5 personalized, high-signal technical interview questions complete with context, ideal answer keys, and follow-up probes.

---

## 5. Kubernetes & HPA Autoscaling

* **Horizontal Pod Autoscaling (HPA)**: Automatically scales pods when CPU utilization exceeds target thresholds:
  * `calyx-agent-service`: Autoscales from **2 to 10 pods** (70% CPU threshold).
  * `calyx-resume-service`: Autoscales from **2 to 8 pods** (75% CPU threshold).
  * `calyx-job-service`: Autoscales from **2 to 6 pods** (80% CPU threshold).
  * `calyx-auth-service`: Autoscales from **2 to 6 pods** (80% CPU threshold).
* **Resilience**: Configured with `livenessProbe` and `readinessProbe` on every service, multi-stage non-root Dockerfiles, and unified NGINX Ingress routing.

---

## 6. How to Run the Automated Test Suites

All tests feature zero external runtime requirements (using embedded engines and mock fallbacks) and can be executed immediately:

### Run Individual Microservice Unit Tests:
```powershell
# 1. Test Auth Service (6/6 tests passing)
python -m pytest services/calyx_auth_service/test_auth.py -v

# 2. Test Job Service (7/7 tests passing)
python -m pytest services/calyx_job_service/test_job.py -v

# 3. Test Resume Vector Service (7/7 tests passing)
python -m pytest services/calyx_resume_service/test_resume.py -v

# 4. Test Agentic AI Service (4/4 tests passing)
python -m pytest services/calyx_agent_service/test_agent.py -v

# 5. Test Analytics Service (4/4 tests passing)
python -m pytest services/calyx_analytics_service/test_analytics.py -v
```

### Run Full End-to-End Recruitment Lifecycle:
```powershell
python -m pytest tests/test_e2e_recruitment_flow.py -v -s
```

### Run High-Concurrency Load & HPA Scaling Benchmark:
```powershell
python tests/load_test_hpa_simulation.py
```

---

## 7. Local Deployment via Docker Compose

To launch all 5 microservices and all 4 databases simultaneously:

```bash
docker compose up -d --build
```

Check running services:
```bash
docker compose ps
```

Access Interactive OpenAPI / Swagger Documentation:
* Auth Service: `http://localhost:8001/docs`
* Job Service: `http://localhost:8002/docs`
* Resume Service: `http://localhost:8003/docs`
* Agent Service: `http://localhost:8004/docs`
* Analytics Service: `http://localhost:8005/docs`

---

## 8. Kubernetes Cluster Deployment

Deploy the entire stack to your Kubernetes cluster with a single command:

```bash
kubectl apply -f k8s/
```

Verify deployment and autoscalers:
```bash
# Check all pods and services in calyx namespace
kubectl get all -n calyx

# Check Horizontal Pod Autoscalers (HPA)
kubectl get hpa -n calyx
```
