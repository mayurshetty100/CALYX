# CALYX: Autonomous Agentic AI Smart Hiring and Talent Screening Platform
## Official Topic Proposal & Architecture Specification Document

---

### 1. Project Title & Submission Details
* **Project Name**: CALYX (Autonomous Agentic AI Smart Hiring & Talent Screening Platform)
* **Topic Category**: AI-Powered Smart Hiring and Resume Screening Platform
* **Domain**: Cloud-Native Enterprise HR-Tech / Distributed Multi-Agent Systems
* **Architecture Pattern**: Polyglot Microservices with Database-per-Service & Event-Driven Orchestration
* **Deployment Target**: Kubernetes (K8s) with Horizontal Pod Autoscaling (HPA)
* **Team Size**: 2 Engineers

---

### 2. Executive Summary & Pitch
Modern recruitment pipelines suffer from resume overload, high latency, unconscious human bias, and static keyword-matching Applicant Tracking Systems (ATS) that fail to understand true candidate competence. 

**CALYX** is a next-generation, microservices-driven talent intelligence platform powered by an **Agentic AI Multi-Agent Mesh**. CALYX automates the entire candidate journey—from multi-format resume ingestion, semantic entity parsing, vector similarity scoring against job rubrics, to autonomous multi-agent candidate critique, bias auditing, and dynamic technical interview generation.

Built from the ground up on cloud-native distributed architecture, CALYX dissects the hiring workflow into five decoupled microservices, where **every single service owns and manages its dedicated database (Database-per-Service pattern)**. The system is engineered to handle massive applicant surges during nationwide campus drives or viral recruitment campaigns using Kubernetes Horizontal Pod Autoscaling (HPA) and resilient inter-service messaging.

---

### 3. Problem Statement & Industry Need
1. **Keyword Gaming vs. Semantic Understanding**: Traditional ATS filter candidates via literal keyword hits. Talented candidates with equivalent synonym skills (e.g., "K8s orchestration" vs. "Kubernetes cluster administration") are routinely discarded.
2. **Compute & Throughput Bottlenecks in Monoliths**: Parsing gigabytes of PDF resumes and invoking Large Language Models (LLMs) are compute-heavy and blocking. In a monolithic system, sudden applicant spikes exhaust thread pools, bringing down user login and job portals.
3. **Data Model Mismatch**: A single database cannot efficiently store relational user permissions, polymorphic semi-structured job applications, high-dimensional vector embeddings, and real-time transient agent execution states.
4. **Lack of Explainable AI**: Standard AI tools give black-box scores. CALYX employs autonomous specialized agents that debate, verify, and generate transparent scoring rubrics and feedback.

---

### 4. Justification: Why Microservices Architecture is Strictly Required
The assignment rubric strictly mandates that the selected project *must actually require microservices architecture and justify the choice*. CALYX fulfills this requirement through the following technical justifications:

| Factor | Monolithic Limitation | CALYX Microservices Solution |
| :--- | :--- | :--- |
| **Heterogeneous Scaling Requirements** | Authentication and Job Browsing have high request frequencies with low CPU/RAM demands. Resume Parsing and Agentic AI reasoning require massive CPU/GPU and async worker pools. | Separate deployments allow scaling the `calyx-agent-service` and `calyx-resume-service` from 2 to 20 replicas without over-provisioning memory for the Auth or Job services. |
| **Polyglot Persistence (Database-per-Service)** | Forcing relational schemas to store high-dimensional vectors (e.g., 768-dim embeddings) and unstructured PDF parse trees leads to terrible query performance and lock contention. | Each microservice connects exclusively to the storage engine optimized for its workload: PostgreSQL (ACID relational), MongoDB (flexible JSON documents), Vector DB (fast ANN vector similarity), and Redis (in-memory agent state & queues). |
| **Fault Isolation & High Availability** | If an external LLM provider experiences latency spikes or token throttling during resume evaluation, the entire monolithic web application hangs. | The AI evaluation is fully decoupled via asynchronous message queues. Even if the AI agent service experiences external backoff, candidates can still apply, recruiters can post jobs, and authentication remains 100% responsive. |
| **Independent Team Velocity (Team of 2)** | Team members step on each other's toes when modifying shared database migrations, ORM models, and deployment pipelines. | Engineer 1 owns Identity, Job Lifecycle, and Analytics; Engineer 2 owns Resume Vectorization, Agentic AI Mesh, and Kubernetes Orchestration. |

---

### 5. Service Dissection & Database-per-Service Matrix
Every microservice in CALYX is isolated with strict network boundaries and dedicated data persistence. No service directly accesses another service's database.

```
                    ┌───────────────────────────────┐
                    │      Client Browser / UI      │
                    └───────────────┬───────────────┘
                                    │ HTTP / REST
                    ┌───────────────▼───────────────┐
                    │      API Gateway (K8s)        │
                    └───┬───────────┬───────────┬───┘
                        │           │           │
       ┌────────────────┘           │           └────────────────┐
       ▼                            ▼                            ▼
┌──────────────┐             ┌──────────────┐             ┌──────────────┐
│  calyx-auth  │             │  calyx-job   │             │ calyx-resume │
│   service    │             │   service    │             │   service    │
└──────┬───────┘             └──────┬───────┘             └──────┬───────┘
       │                            │                            │
 ┌─────▼──────┐               ┌─────▼──────┐               ┌─────▼──────┐
 │ PostgreSQL │               │  MongoDB   │               │  VectorDB  │
 │  Database  │               │  Database  │               │ (Embeddings│
 └────────────┘               └────────────┘               └────────────┘
                                    ▲                            ▲
                                    │ gRPC / Event Bus           │
                             ┌──────┴───────┐                    │
                             │ calyx-agent  │────────────────────┘
                             │   service    │
                             └──────┬───────┘
                                    │
                              ┌─────▼──────┐
                              │   Redis    │
                              │State & Queues
                              └────────────┘
                                    │ Events
                             ┌──────▼───────┐
                             │calyx-analytics
                             └──────┬───────┘
                                    │
                              ┌─────▼──────┐
                              │Analytics DB│
                              └────────────┘
```

#### Service Inventory:
1. **`calyx-auth-service`**:
   - **Purpose**: User registration, login, role-based access control (RBAC), and cryptographically signed JWT issuance.
   - **Database**: **PostgreSQL** (Stores users, password hashes with Argon2id/Bcrypt, role assignments, audit logs).
2. **`calyx-job-service`**:
   - **Purpose**: Job requisition management, custom hiring rubrics, candidate application submissions, and status progression.
   - **Database**: **MongoDB** (Stores polymorphic job descriptions, dynamic question lists, candidate profile summaries).
3. **`calyx-resume-service`**:
   - **Purpose**: Document ingestion (PDF, DOCX), optical entity extraction, token chunking, and high-dimensional semantic embedding computation.
   - **Database**: **Vector Database (Qdrant / Pgvector / ChromaDB)** (Stores candidate skill embeddings and conducts Approximate Nearest Neighbor [ANN] cosine searches).
4. **`calyx-agent-service`**:
   - **Purpose**: The Agentic AI reasoning mesh containing 4 autonomous sub-agents:
     - *Extraction & Normalization Agent*: Cleans resume text, resolves job title ambiguities.
     - *Criteria Matching Agent*: Evaluates candidate against hiring rubrics and scores experience depth.
     - *Bias & Fairness Audit Agent*: Scrubs PII (names, gender, age markers) to enforce unbiased scoring.
     - *Technical Interview Synthesizer*: Autonomously crafts customized follow-up interview questions targeting resume gaps.
   - **Database**: **Redis** (Stores transient agent conversation history, sub-agent task coordination memory, rate-limit buckets, and distributed job locks).
5. **`calyx-analytics-service`**:
   - **Purpose**: Real-time hiring dashboard, system performance metrics, candidate distribution charts, and recruitment cycle metrics.
   - **Database**: **PostgreSQL Analytics / SQLite Analytics** (Stores aggregated metric tables, audit logs, and performance events).

---

### 6. Kubernetes Deployment & Autoscaling (HPA) Strategy
CALYX is containerized and orchestrated via Kubernetes manifests supporting:
- **Horizontal Pod Autoscaler (HPA)**: 
  - `calyx-agent-service`: Autoscales from 2 to 10 pods when CPU utilization exceeds 70% or queue depth exceeds 20 jobs.
  - `calyx-resume-service`: Autoscales from 2 to 8 pods during bulk resume upload batches.
  - `calyx-job-service` & `calyx-auth-service`: Scaled independently based on HTTP request throughput and memory usage.
- **Resilience & Production Readiness**:
  - `livenessProbe` and `readinessProbe` on every microservice.
  - `ConfigMap` and `Secret` segregation for zero hardcoded secrets.
  - Resource limits (`requests` and `limits`) to prevent Pod noisy-neighbor evictions.
  - Ingress controller routing requests via reverse proxy paths (`/api/v1/auth`, `/api/v1/jobs`, `/api/v1/resumes`, `/api/v1/agents`, `/api/v1/analytics`).

---

### 7. Team of 2 Workload Allocation

| Member | Focus Area | Detailed Responsibilities |
| :--- | :--- | :--- |
| **Engineer 1 (Backend Core & Infrastructure)** | Platform, Auth, Job Management & K8s DevOps | - Design API Gateway, Routing, and Security.<br>- Implement `calyx-auth-service` with PostgreSQL.<br>- Implement `calyx-job-service` with MongoDB.<br>- Implement `calyx-analytics-service`.<br>- Build Dockerfiles, K8s manifests, HPA configs, and automated test pipelines. |
| **Engineer 2 (AI, Vector Search & Agentic Mesh)** | Document Intelligence, Vector Engine & Agentic AI | - Implement `calyx-resume-service` (PDF extraction, text chunking, embedding generation).<br>- Set up Vector DB for cosine similarity search.<br>- Implement `calyx-agent-service` with Redis state orchestration.<br>- Build the 4-agent reasoning loop (Extraction, Matching, Bias Audit, Interview Synthesis).<br>- Benchmark load and autoscaling triggers under simulated applicant traffic. |

---

### 8. Functional & Non-Functional Requirements Checklist

#### Functional Requirements:
- [x] Secure multi-tenant authentication (Candidates vs. Recruiters) with JWT tokens.
- [x] Job creation with dynamic skill requirements, weights, and rubric thresholds.
- [x] Multi-format resume upload and asynchronous document parsing.
- [x] Vector embedding search for instant semantic ranking of candidates against job descriptions.
- [x] Agentic AI multi-agent evaluation pipeline providing explainable scoring breakdowns and bias scrub reports.
- [x] Autonomous generation of personalized technical interview questions based on candidate resume weaknesses.
- [x] Real-time hiring analytics dashboard and candidate pipeline tracking.

#### Non-Functional Requirements:
- [x] **Scalability**: Horizontal auto-scaling under load (K8s HPA based on CPU/Memory/Queues).
- [x] **Fault Isolation**: Independent failure domains via Database-per-Service.
- [x] **Security**: Bcrypt/Argon2 password hashing, JWT stateless validation, role-based middleware, input validation with Pydantic/Zod.
- [x] **Performance**: Fast vector retrieval (< 100ms) and asynchronous processing for heavy AI tasks.
- [x] **Observability**: Structured logging, health check endpoints (`/health/live`, `/health/ready`), and metric endpoints.
- [x] **Code Quality**: Production-grade modular code, line-by-line documentation, and beginner-friendly conceptual explanations.
