# CALYX Master Execution Plan: 20/20 Rubric Fulfillment & Full-Stack Deployment

This plan maps directly to the official rubric criteria (**Database 4M**, **Cross-Service Communication 4M**, **Resilience 4M**, **Security 3M**, **Deployment 5M = Total 20M**), outlines the creation of the user interface requested by the professor, and configures cloud deployment for Render and Vercel.

---

## Rubric-to-Architecture Mapping Matrix

| Rubric Dimension | Marks | CALYX Implementation & Proof Artifacts |
| :--- | :---: | :--- |
| **1. Database** | **4M** | • **PostgreSQL**: Relational schema for Auth (`users`, `refresh_tokens`, `audit_logs`).<br>• **MongoDB**: Flexible BSON documents for Jobs (`job_postings`, `applications`, dynamic rubrics).<br>• **Vector DB**: 384-dimensional dense semantic vectors with Cosine Similarity indexing.<br>• **Redis**: In-memory state store, distributed locks (`SETNX`), and async task queues.<br>• **PostgreSQL Analytics**: Event sourcing pipeline for conversion funnels and score histograms.<br>• **Cloud Ready**: Automatic support for Neon/Supabase PostgreSQL and MongoDB Atlas. |
| **2. Cross-Service Communication** | **4M** | • **Unified API Gateway**: Routes `/api/v1/*` to individual microservices with CORS handling.<br>• **Inter-Service Communication**: `calyx-agent-service` calls `calyx-job-service` to write back evaluation scores.<br>• **Event Sourcing**: All services emit asynchronous pipeline events to `calyx-analytics-service`.<br>• **Distributed Tracing**: Standardized `X-Request-ID` and correlation IDs across all service hops. |
| **3. Resilience** | **4M** | • **Circuit Breaker Pattern**: Fails fast and recovers automatically during downstream degradation.<br>• **Exponential Backoff Retries**: Automatic retries for transient database or network errors.<br>• **Health Probes**: `/health/live` and `/health/ready` on every single microservice.<br>• **Horizontal Pod Autoscaling (HPA)**: Kubernetes HPA scaling pods from 2 to 10 based on CPU/RAM load. |
| **4. Security** | **3M** | • **Cryptographic Hashing**: Salted `bcrypt` password hashing (defensive 72-byte truncation).<br>• **JWT Stateless Auth**: Cryptographically signed access tokens and refresh token rotation.<br>• **Role-Based Access Control (RBAC)**: Strict role barriers (`candidate` vs `recruiter` vs `admin`).<br>• **Input Validation**: Pydantic v2 schemas preventing SQL/NoSQL injection and mass assignment.<br>• **Container Security**: Non-root user `calyxuser` in all Dockerfiles. |
| **5. Deployment** | **5M** | • **Kubernetes Manifests**: 10 production manifests in `k8s/` (Deployments, Services, Ingress, HPA, PVCs).<br>• **Docker Compose**: Complete 9-container local development stack.<br>• **Render Deployment**: `render.yaml` blueprint Infrastructure-as-Code for backend services.<br>• **Vercel Deployment**: `frontend/vercel.json` for 1-click cloud frontend hosting. |
| **Total** | **20M** | **100% Comprehensive Rubric Coverage** |

---

## Detailed Step-by-Step Implementation Roadmap

### Step 1: Resilience & Circuit Breaker Module (`common/resilience.py`)
- Implement the `CircuitBreaker` class with `CLOSED`, `OPEN`, and `HALF_OPEN` state transitions.
- Implement `@retry_with_backoff` decorator for safe inter-service HTTP requests.
- Add centralized system health aggregator.

### Step 2: Unified API Gateway Service (`services/calyx_gateway_service/`)
- Single unified entrypoint on port `8000` handling CORS, reverse-proxying requests to:
  - `/api/v1/auth/*` ➔ `calyx-auth-service`
  - `/api/v1/jobs/*` ➔ `calyx-job-service`
  - `/api/v1/resumes/*` ➔ `calyx-resume-service`
  - `/api/v1/agents/*` ➔ `calyx-agent-service`
  - `/api/v1/analytics/*` ➔ `calyx-analytics-service`
- Includes circuit-breaker-backed health aggregation (`/health/all`).

### Step 3: Interactive Full-Stack Frontend User Interface (`frontend/`)
- Built with modern React/HTML5/Tailwind/JavaScript.
- **Portals Included**:
  1. **Authentication Portal**: Toggle between Recruiter and Candidate login/registration.
  2. **Candidate Portal**: Browse published jobs, upload resume (PDF or text), track application status, view AI evaluation match score, and view AI-generated personalized interview questions.
  3. **Recruiter Portal**: Post jobs with custom skill weights and rubric criteria, view applicants ranked by score, trigger AI agent consensus, and inspect the transparent 4-agent reasoning trace.
  4. **Executive Analytics Dashboard**: Conversion funnel metrics, candidate score distribution charts, and live microservice health telemetry.
- Configured with `frontend/package.json` and `frontend/vercel.json` for 1-click Vercel deployment.

### Step 4: Cloud Deployment Configuration (Render & Vercel)
- Author `render.yaml`: Infrastructure-as-Code Blueprint defining the backend services and databases on Render.
- Author `frontend/vercel.json`: Vercel deployment configuration with proxy routing and environment variables.
- Step-by-step instructions for 1-click cloud deployment.

### Step 5: Verification & Presentation Script
- Verify all unit, integration, and end-to-end tests pass.
- Write `docs/PRESENTATION_AND_VIVA_GUIDE.md`: The exact script and terminal commands to demonstrate every rubric category during the project presentation.
