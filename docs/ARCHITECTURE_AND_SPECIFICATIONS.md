# CALYX: System Architecture, Microservices Dissection & Technical Specifications

---

## 1. Architectural Philosophy & Design Principles
CALYX is architected to showcase enterprise-level distributed systems engineering. It adheres to the following core tenets:

1. **Database-per-Service Pattern**:
   - Each microservice has exclusive ownership over its persistent datastore.
   - Services never query another service's database directly. Data sharing occurs exclusively via secure REST/gRPC APIs or asynchronous event streaming.
2. **Domain-Driven Design (DDD)**:
   - Services are split along clear bounded contexts: Identity Domain, Hiring Requisition Domain, Document Intelligence Domain, Agentic Reasoning Domain, and Analytics Domain.
3. **Polyglot Persistence**:
   - Different types of data demand different storage engines: Relational ACID for Auth, Flexible Document for Jobs, High-Dimensional Vector Index for Resumes, and Fast In-Memory Key-Value/Streams for Agent Workflows.
4. **Resilience & Asynchronous Decoupling**:
   - Long-running AI operations (resume evaluation, embedding computation) are non-blocking. Clients receive a job ID immediately (`202 Accepted`) and can poll or receive websocket/webhook updates as agents complete their tasks.
5. **Autoscaling & Container Portability**:
   - Microservices are packaged as lightweight, multi-stage Docker containers with non-root security contexts, deployed on Kubernetes with Horizontal Pod Autoscalers (HPA).

---

## 2. Microservice Dissection & Detailed Specifications

```
                                  +------------------------------------+
                                  |         Kubernetes Ingress         |
                                  |     (Reverse Proxy & Routing)      |
                                  +-----------------+------------------+
                                                    |
             +--------------------+-----------------+--------------------+--------------------+
             |                    |                                      |                    |
             v                    v                                      v                    v
      /api/v1/auth/*        /api/v1/jobs/*                        /api/v1/resumes/*    /api/v1/analytics/*
   +--------------------+  +--------------------+               +--------------------+  +--------------------+
   | calyx-auth-service |  |  calyx-job-service |               |calyx-resume-service|  |  calyx-analytics   |
   |   (FastAPI/Python) |  |  (FastAPI/Python)  |               |  (FastAPI/Python)  |  |   (FastAPI/Python) |
   +---------+----------+  +---------+----------+               +---------+----------+  +---------+----------+
             |                       |                                    |                       |
             v                       v                                    v                       v
     +---------------+       +---------------+                    +---------------+       +---------------+
     |  PostgreSQL   |       |    MongoDB    |                    |   Vector DB   |       |  PostgreSQL   |
     |   Auth DB     |       |    Job DB     |                    |  (Chroma/Qdr) |       |  Analytics DB |
     +---------------+       +---------------+                    +---------------+       +---------------+
                                     |                                    |
                                     +------------------+-----------------+
                                                        |
                                                        v
                                            +------------------------+
                                            |   calyx-agent-service  |
                                            |  (Multi-Agent Mesh)    |
                                            +-----------+------------+
                                                        |
                                                        v
                                                +---------------+
                                                |     Redis     |
                                                | (Memory/Queue)|
                                                +---------------+
```

### Microservice 1: `calyx-auth-service`
* **Primary Role**: Authentication, User Management, Role-Based Access Control (RBAC), and Token Lifecycle.
* **Technology Stack**: Python 3.12, FastAPI, SQLAlchemy ORM, Alembic migrations, PyJWT, Passlib (Argon2 / Bcrypt).
* **Database**: **PostgreSQL**
  * *Tables*: `users` (id, email, password_hash, full_name, role [candidate/recruiter/admin], is_active, created_at), `refresh_tokens` (id, user_id, token_hash, expires_at, revoked), `audit_logs` (id, user_id, action, ip_address, timestamp).
* **Key Endpoints**:
  * `POST /api/v1/auth/register` - Create candidate or recruiter profile.
  * `POST /api/v1/auth/login` - Authenticate credentials and return short-lived JWT access token + refresh token.
  * `POST /api/v1/auth/refresh` - Issue new access token using refresh token.
  * `GET /api/v1/auth/verify` - Internal token verification endpoint for downstream services.
  * `GET /health/live` & `GET /health/ready` - K8s readiness & liveness probes.

### Microservice 2: `calyx-job-service`
* **Primary Role**: Job Posting Lifecycle, Candidate Applications, Requirement Rubrics.
* **Technology Stack**: Python 3.12, FastAPI, Motor/Beanie (Async MongoDB client), Pydantic v2.
* **Database**: **MongoDB**
  * *Collections*: `job_postings` (id, recruiter_id, title, department, experience_level, min_years_exp, required_skills, nice_to_have_skills, compensation_range, rubric_weights, status [active/closed]), `applications` (id, job_id, candidate_id, resume_id, status [applied/screening/shortlisted/rejected], match_score, created_at).
* **Key Endpoints**:
  * `POST /api/v1/jobs` - Create new job requisition with detailed skill rubrics.
  * `GET /api/v1/jobs` - Search and list active jobs.
  * `GET /api/v1/jobs/{id}` - Fetch specific job details.
  * `POST /api/v1/jobs/{id}/apply` - Candidate submits application linked to a parsed resume.
  * `GET /api/v1/jobs/{id}/applications` - Recruiter views candidate pipeline.

### Microservice 3: `calyx-resume-service`
* **Primary Role**: Asynchronous resume upload, PDF/DOCX text extraction, token chunking, and semantic vector embedding computation.
* **Technology Stack**: Python 3.12, FastAPI, PyPDF2/pdfplumber, sentence-transformers / embedding models, ChromaDB / Qdrant vector client.
* **Database**: **Vector Database (ChromaDB / Qdrant)**
  * *Vector Collections*: `candidate_embeddings` (vector: 384-dimensional dense vectors representing resume experience, metadata: candidate_id, resume_id, file_name, skills_detected, education, total_experience_years).
* **Key Endpoints**:
  * `POST /api/v1/resumes/upload` - Securely upload resume file (PDF/DOCX), parse entities, generate vector embeddings, and store in Vector DB.
  * `GET /api/v1/resumes/{id}` - Retrieve extracted resume structured data.
  * `POST /api/v1/resumes/search` - Semantic vector search: given a job description or skill query, perform cosine distance search to return top-k matching candidates.

### Microservice 4: `calyx-agent-service`
* **Primary Role**: The core Agentic AI Engine. Orchestrates a team of 4 autonomous AI agents cooperating to analyze, score, audit, and generate interview material.
* **Technology Stack**: Python 3.12, FastAPI, LangChain/Custom Agent Orchestration, Redis async client, Gemini API / LLM provider.
* **Database**: **Redis**
  * *Data Structures*:
    * Hashes: `agent:session:{evaluation_id}` (stores intermediate agent reasoning steps).
    * Lists/Streams: `queue:agent:evaluations` (task queue for background batch evaluation).
    * Sets: `agent:locks` (distributed lock to prevent duplicate parallel evaluations).
* **The 4 Autonomous Agents**:
  1. **Extraction & Normalization Agent**: Parses nuanced resume jargon (e.g. maps "k8s admin" to "Kubernetes Orchestration").
  2. **Rubric Matcher Agent**: Performs deterministic & semantic rubric scoring across technical skills, leadership, and project complexity.
  3. **Fairness & Bias Audit Agent**: Inspects candidate profiles, strips demographic indicators, and verifies that scoring is strictly merit-based.
  4. **Dynamic Interview Question Agent**: Identifies candidate weak spots and synthesizes 5 targeted, high-value technical interview questions with expected answers and scoring criteria.
* **Key Endpoints**:
  * `POST /api/v1/agents/evaluate` - Dispatch an agentic evaluation job for an application.
  * `GET /api/v1/agents/evaluate/{task_id}` - Check agent evaluation status and review full agent reasoning trace.
  * `POST /api/v1/agents/generate-interview` - Generate tailor-made technical interview questionnaire for candidate.

### Microservice 5: `calyx-analytics-service`
* **Primary Role**: Aggregates metrics, recruitment velocity, candidate score distributions, and pipeline health for enterprise executive dashboards.
* **Technology Stack**: Python 3.12, FastAPI, SQLAlchemy, SQLite/PostgreSQL.
* **Database**: **PostgreSQL / SQLite Analytics Database**
  * *Tables*: `pipeline_events` (id, event_type, entity_id, timestamp, payload), `job_metrics` (job_id, total_applications, average_score, time_to_shortlist).
* **Key Endpoints**:
  * `GET /api/v1/analytics/dashboard` - High-level statistics (total candidates, pass rates, average evaluation latency).
  * `GET /api/v1/analytics/jobs/{job_id}/distribution` - Score histogram and diversity distribution metrics.
  * `POST /api/v1/analytics/events` - Ingest audit and hiring pipeline events.

---

## 3. Beginner-Friendly Concept Glossary
To help beginners grasp advanced distributed systems concepts, here are key definitions:

* **Microservice**: Instead of packaging the entire software into one giant monolithic program, we divide it into independent, smaller programs that do one specific job really well. If one crashes, the others keep running!
* **Database-per-Service**: A gold-standard architectural pattern where microservices are strictly prohibited from sharing a single database. This prevents tight coupling and ensures one service cannot corrupt another service's tables.
* **Polyglot Persistence**: "Polyglot" means speaking multiple languages. Polyglot persistence means choosing the *right tool for the right job*—e.g., PostgreSQL for user login safety, MongoDB for dynamic documents, Vector DB for AI searches, and Redis for lightning-fast caches.
* **Agentic AI**: Traditional AI answers a single prompt. Agentic AI refers to autonomous software agents that can reason, plan, use tools, make multi-step decisions, and collaborate with other specialized agents to achieve complex goals without constant human intervention.
* **Vector Embeddings & Cosine Similarity**: An embedding translates text into a list of numbers (a vector) in mathematical space where concepts with similar meanings cluster together. "Cosine similarity" measures the angle between two vectors to see how closely a resume matches a job description, even if they use different words!
* **Kubernetes (K8s)**: An open-source orchestrator that automatically manages, deploys, scales, and repairs our containerized microservice pods across a cluster of servers.
* **Pod**: The smallest deployable computing unit in Kubernetes. Think of a Pod as a wrapper around one or more running Docker containers.
* **Horizontal Pod Autoscaler (HPA)**: An automated Kubernetes robot that monitors CPU/RAM usage. If traffic spikes and CPU goes above 70%, HPA automatically spins up new Pod replicas to share the load, and spins them down when traffic slows down to save money!
* **Ingress**: The front door of our Kubernetes cluster that routes incoming internet requests to the appropriate internal microservice based on the URL path.
