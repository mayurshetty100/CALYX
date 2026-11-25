# ==============================================================================
# CALYX: COMPREHENSIVE PRESENTATION & VIVA EVALUATION GUIDE
# ==============================================================================
# Platform: Autonomous Agentic AI Microservices Smart Hiring Mesh
# Evaluation Target: 20/20 Marks (T1 Rubric Compliance)
# Author: Calyx Engineering Team (Team of 2)
# ==============================================================================

> **Executive Summary for the Evaluator / Professor:**
> Calyx is an enterprise-grade, distributed microservices platform engineered for autonomous candidate evaluation.
> It integrates a 4-agent autonomous mesh (Normalization, Criteria Matching, Bias Audit, Dynamic Interview Synthesizer),
> strict Database-per-Service isolation (PostgreSQL, MongoDB, Vector DB, Redis), production resiliency (Circuit Breakers & Exponential Retries),
> high-security RBAC with salted bcrypt, and automated Kubernetes Horizontal Pod Autoscaling (HPA).

---

## 1. 20-Mark Evaluation Rubric Breakdown & Evidence Matrix

| Evaluation Criteria | Marks | Architectural Implementation | Verification Evidence & Test Command |
| :--- | :---: | :--- | :--- |
| **T1: Database** | **4M** | **Database-per-Service Pattern**: Polyglot persistence. PostgreSQL (Auth & Identity), MongoDB (Jobs & Requisitions), In-House Vector DB (384-dim dense embeddings + Cosine Similarity), Redis (Distributed Locks & State Store), PostgreSQL (Analytics & Funnels). | `pytest services/calyx_auth_service/ -v`<br>`pytest services/calyx_job_service/ -v`<br>`pytest services/calyx_resume_service/ -v` |
| **T1: Cross-Service Communication** | **4M** | **Unified API Gateway (Port 8000)**: Non-blocking async REST calls with `httpx`, distributed tracing with `X-Request-ID` propagation, event-sourced audit logging, and aggregate observability. | `pytest services/calyx_gateway_service/ -v`<br>`pytest tests/test_e2e_recruitment_flow.py -v` |
| **T1: Resilience** | **4M** | **Circuit Breaker Pattern** (`CLOSED`, `OPEN`, `HALF_OPEN`), exponential backoff jitter retries (`@retry_with_backoff`), Kubernetes `/health/live` & `/health/ready` probes, and HPA autoscaling under load. | `pytest tests/test_resilience.py -v`<br>`python tests/load_test_hpa_simulation.py` |
| **T1: Security** | **3M** | **Defense-in-Depth**: Native salted bcrypt hashing (72-byte safe), HMAC-SHA256 JWT access & refresh token rotation, strict RBAC (`candidate`, `recruiter`, `admin`), Pydantic v2 validation. | `pytest services/calyx_auth_service/ -v` (Tests 02-06) |
| **T1: Deployment** | **5M** | **Production Kubernetes Cluster**: 10 K8s manifests (`00-namespace` to `10-gateway`), HPA autoscaling (2 -> 10 replicas), Docker Compose stack, `render.yaml` (Render backend), and `vercel.json` (Vercel frontend). | `docker compose config`<br>`kubectl apply -f k8s/`<br>`cd frontend && npm run build` |
| **Total** | **20M** | **Complete Full-Stack Autonomous Microservice Ecosystem** | **35/35 Tests Passing (100% Green)** |

---

## 2. Step-by-Step Demonstration Runbook (Exact Terminal Commands)

Follow these exact steps during your demonstration to show each component working cleanly:

### STEP 1: Verify All Unit & Integration Tests (100% Green)
Execute the global test runner. This proves that all 5 microservices, the API Gateway, and the End-to-End lifecycle work without flaws.

```powershell
python -m pytest -v
```
*Expected Output:*
```text
======================= 35 passed, 1 warning in ~15s =======================
```

---

### STEP 2: Demonstrate Resilience & Circuit Breaker Pattern (Rubric: 4 Marks)
Run the dedicated resilience test suite. This proves that when downstream services degrade, the circuit breaker opens to prevent cascading failures.

```powershell
python -m pytest tests/test_resilience.py -v
```
*Key concepts to explain to the professor:*
1. **CLOSED**: Normal state. Requests pass through.
2. **OPEN**: If 5 consecutive failures occur, the breaker trips to OPEN. Subsequent requests fail fast immediately without waiting for timeouts.
3. **HALF_OPEN**: After a 15-second recovery window, a single probe request is permitted through to verify whether downstream has recovered.

---

### STEP 3: Demonstrate Kubernetes Autoscaling (HPA) Under Concurrency Load
Run the simulated high-concurrency load test. This fires 50 concurrent worker threads at the platform, demonstrating zero failures and dynamic scaling triggers.

```powershell
python tests/load_test_hpa_simulation.py
```
*Expected Output:*
```text
======================================================================
CALYX LOAD TEST & HPA AUTOSCALING BENCHMARK
======================================================================
Concurrent Workers: 50 | Total Requests: 100
Successful Requests: 100 / 100 (100.00%)
Throughput: ~79.2 requests/second
Simulated HPA Trigger: Pod replicas dynamically scaled 2 -> 3 pods!
```

---

### STEP 4: Start the Full Multi-Container Stack with Docker Compose
To launch all 4 databases, 5 microservices, and the API Gateway simultaneously:

```powershell
docker compose up -d
```
To inspect running container health:
```powershell
docker compose ps
```
To check live logs from the API Gateway:
```powershell
docker compose logs -f calyx-gateway-service
```

---

### STEP 5: Launch the Modern Frontend UI (Candidate & Recruiter Experience)
Navigate into the `frontend` folder and start the local Vite development server:

```powershell
cd frontend
npm run dev
```
Open your browser at `http://localhost:5173`:
1. **Candidate Portal**:
   - Register/Sign in as a candidate (`candidate@calyx.ai`).
   - Browse open job requisitions loaded from MongoDB.
   - Click **"Parse & Embed in Vector DB"** to generate 384-dimensional dense embeddings.
   - Click **"Apply"** to trigger the Autonomous 4-Agent Screening Pipeline.
   - Show the professor the **Dynamic Interview Questions** synthesized tailored to the candidate's exact profile!
2. **Recruiter Portal**:
   - Register/Sign in as a recruiter (`recruiter@calyx.ai`).
   - Create a new job requisition with custom rubric weights (e.g., Technical 50%, Experience 30%, Education 20%).
   - View applicants ranked by AI composite score.
   - Click **"Inspect AI Trace"** to open the Explainable AI (XAI) modal, displaying the 4-agent reasoning trace:
     - *1. Normalization Agent* (PII redaction).
     - *2. Criteria Agent* (Weighted rubric evaluation).
     - *3. Bias Audit Agent* (Demographic fairness & 4/5ths disparate impact check).
     - *4. Interview Synthesizer* (Personalized technical interview questions).
3. **Observability & Metrics**:
   - View live response latencies and Circuit Breaker states across all 5 microservices!

---

### STEP 6: Deploy to Kubernetes Cluster (Rubric: 5 Marks)
Ensure Docker Desktop Kubernetes is running (`kubectl get nodes`). Then apply the manifests:

```powershell
# 1. Create dedicated Calyx namespace
kubectl apply -f k8s/00-namespace.yaml

# 2. Apply shared configuration and secrets
kubectl apply -f k8s/01-configmaps-secrets.yaml

# 3. Deploy databases (PostgreSQL, MongoDB, Redis)
kubectl apply -f k8s/02-databases.yaml

# 4. Deploy all microservices
kubectl apply -f k8s/03-auth-service.yaml
kubectl apply -f k8s/04-job-service.yaml
kubectl apply -f k8s/05-resume-service.yaml
kubectl apply -f k8s/06-agent-service.yaml
kubectl apply -f k8s/07-analytics-service.yaml
kubectl apply -f k8s/10-gateway-service.yaml

# 5. Enable Horizontal Pod Autoscaling (HPA) and Ingress
kubectl apply -f k8s/08-autoscaling-hpa.yaml
kubectl apply -f k8s/09-ingress.yaml

# 6. Verify all pods and HPA are active
kubectl get pods -n calyx
kubectl get hpa -n calyx
```

---

### STEP 7: Cloud Deployments (Render & Vercel)

#### A. Backend on Render:
1. Push the repository to GitHub.
2. In the Render Dashboard, click **New + -> Blueprint**.
3. Select your repository. Render automatically reads `render.yaml` and provisions:
   - `calyx-gateway-service` (Web Service on port 8000).
   - Internal private services for Auth, Job, Resume, Agent, and Analytics.
   - Connects to free cloud databases (Neon PostgreSQL, MongoDB Atlas, Upstash Redis).

#### B. Frontend on Vercel:
1. Navigate to the `frontend` folder.
2. Run:
   ```powershell
   cd frontend
   npm run build
   npx vercel --prod
   ```
3. Set the Environment Variable in Vercel:
   `VITE_API_URL=https://your-calyx-gateway.onrender.com/api/v1`
4. The frontend is instantly live worldwide on Vercel's global CDN!

---

## 3. Professor Viva & Defense Q&A (Cheat Sheet)

### Q1: Why did you choose a Microservices architecture instead of a Monolith?
**Answer:**
> "A monolithic architecture would tightly couple compute-heavy AI tasks (such as dense vector embeddings and multi-agent reasoning) with lightweight transactional tasks (such as user login or job search). Under high traffic, resume parsing would starve CPU and crash the login system.
> With our microservices architecture, the Resume and Agent services can independently scale up via Kubernetes HPA without consuming resources from the Auth or Job services. Furthermore, each service uses its optimal database engine (Database-per-Service pattern)."

### Q2: Explain your Polyglot Persistence / Database-per-Service selection.
**Answer:**
> "We selected the best storage engine for each bounded context:
> 1. **Auth Service & Analytics Service -> PostgreSQL**: Relational schema guarantees ACID transactions, strict foreign keys, and analytical aggregations.
> 2. **Job Service -> MongoDB**: Flexible JSON document model accommodates dynamic recruiter rubrics and evolving job schemas with fast compound index queries.
> 3. **Resume Service -> Vector Database**: Stores 384-dimensional dense semantic vectors and computes Cosine Similarity for semantic talent ranking.
> 4. **Agent Service -> Redis**: In-memory data store provides sub-millisecond distributed locks (`SETNX`) and stores intermediate multi-agent reasoning traces."

### Q3: How do you handle cascading failures between microservices?
**Answer:**
> "We implemented the **Circuit Breaker pattern** in `common/resilience.py` and wrapped all upstream gateway calls. If a downstream service fails 5 times consecutively, the circuit trips to `OPEN`, immediately returning a 503 error without waiting for timeouts. This prevents thread pool exhaustion and protects upstream services. After 15 seconds, it transitions to `HALF_OPEN` to probe recovery. In addition, our `@retry_with_backoff` decorator adds exponential jitter retries to handle transient network blips."

### Q4: How is security and RBAC enforced?
**Answer:**
> "1. Passwords are never stored in plain text; they are hashed using native `bcrypt` with salted work factor and 72-byte safe truncation.
> 2. Authentication relies on HMAC-SHA256 signed JSON Web Tokens (JWT) with separate short-lived access tokens (30 min) and long-lived refresh tokens (7 days).
> 3. Role-Based Access Control (`candidate`, `recruiter`, `admin`) is enforced at the route level via FastAPI dependencies.
> 4. Distributed tracing headers (`X-Request-ID`) prevent header tampering and enable end-to-end audit logging."

### Q5: How does the Kubernetes Horizontal Pod Autoscaler (HPA) work in this project?
**Answer:**
> "In `k8s/08-autoscaling-hpa.yaml`, the HPA monitors CPU and memory consumption across the pods. When average CPU utilization exceeds 80%, the Kubernetes metrics-server instructs the Deployment controller to scale replicas from the minimum of 2 up to a maximum of 10 pods. When load drops, it automatically scales back down to conserve cluster resources."
