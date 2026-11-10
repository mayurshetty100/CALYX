# ==============================================================================
# CALYX AGENT 4: DYNAMIC TECHNICAL INTERVIEW SYNTHESIZER AGENT
# ==============================================================================
# Concept Explanation for Beginners:
# What does the Technical Interview Synthesizer Agent do?
# Generic interview questions ("Tell me about a time you had a bug") are boring
# and ineffective.
# This agent acts as a Principal Architect: it inspects the candidate's resume,
# finds the exact technologies they claimed to use, identifies any missing gaps
# or ambiguities, and autonomously writes 3 to 5 customized technical interview
# questions!
# Crucially, it also writes the "Expected Answer Key", so interviewers know
# exactly what technical indicators distinguish an average candidate from a top 1% hire!
# ==============================================================================

from typing import Dict, Any, List


class TechnicalInterviewAgent:
    """
    Autonomous agent that analyzes candidate resume claims and synthesizes
    targeted, high-signal technical interview questionnaires.
    """

    NAME = "Dynamic Technical Interview Synthesizer Agent"

    @classmethod
    def run(
        cls,
        normalized_data: Dict[str, Any],
        criteria_evaluation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synthesizes personalized technical interview questions and grading keys.
        """
        candidate_skills = normalized_data.get("normalized_skills", [])
        missing_skills = criteria_evaluation.get("missing_required_skills", [])
        specialty = normalized_data.get("detected_specialty", "Software Engineering")
        questions: List[Dict[str, Any]] = []

        # ----------------------------------------------------------------------
        # Question 1: Deep Verification of Primary Specialty
        # ----------------------------------------------------------------------
        if "Kubernetes" in candidate_skills or "Cloud" in specialty:
            questions.append({
                "question_id": "tech_q1",
                "focus_area": "Kubernetes Autoscaling & Rolling Updates",
                "question_prompt": (
                    "When configuring Horizontal Pod Autoscaling (HPA) in production, how do you prevent "
                    "'flapping' (rapid scaling up and down)? How do you tune the downscale stabilization "
                    "window and terminationGracePeriodSeconds to ensure zero dropped HTTP requests?"
                ),
                "rationale": "Candidate claims production Kubernetes experience; verifying hands-on HPA tuning expertise.",
                "ideal_response_key": (
                    "Strong candidate should mention setting behavior.scaleDown.stabilizationWindowSeconds (e.g. 300s), "
                    "readiness probes, preStop lifecycle hooks with a sleep period before SIGTERM, and PodDisruptionBudgets (PDB)."
                ),
                "follow_up_probe": "What custom metrics (beyond CPU and memory) would you expose via Prometheus for HPA?"
            })
        elif "Pytorch" in candidate_skills or "AI" in specialty:
            questions.append({
                "question_id": "tech_q1",
                "focus_area": "Deep Learning Training & Memory Optimization",
                "question_prompt": (
                    "When training large Transformer models that exceed single-GPU VRAM limits, what techniques "
                    "do you employ? Compare Gradient Accumulation, Activation Checkpointing, and PyTorch FSDP (Fully Sharded Data Parallel)."
                ),
                "rationale": "Verifying practical knowledge of distributed PyTorch workflows and GPU memory management.",
                "ideal_response_key": (
                    "Candidate should explain trading compute for memory (checkpointing), virtual batch sizes (accumulation), "
                    "and ZeRO-style parameter/gradient sharding (FSDP)."
                ),
                "follow_up_probe": "How do you handle mixed-precision (FP16/BF16) numerical stability and loss scaling?"
            })
        else:
            questions.append({
                "question_id": "tech_q1",
                "focus_area": "Distributed Systems Architecture",
                "question_prompt": (
                    "In a microservices architecture, how do you manage transactions that span multiple independent databases "
                    "without using distributed two-phase locking (2PC)? Explain the Saga Pattern with compensation transactions."
                ),
                "rationale": "Assessing core distributed systems and microservice data consistency fundamentals.",
                "ideal_response_key": (
                    "Candidate should contrast Choreography (event-driven) vs Orchestration (central coordinator), "
                    "and explain how compensating transactions roll back partial failures."
                ),
                "follow_up_probe": "How do you handle idempotent retries if a compensating transaction fails midway?"
            })

        # ----------------------------------------------------------------------
        # Question 2: Testing Missing or Borderline Requirements
        # ----------------------------------------------------------------------
        if missing_skills:
            target_missing = missing_skills[0]
            questions.append({
                "question_id": "tech_q2",
                "focus_area": f"Adaptability: {target_missing}",
                "question_prompt": (
                    f"Our infrastructure stack relies heavily on {target_missing}. While your resume highlights related tools, "
                    f"how would you approach onboarding and migrating our workloads to {target_missing}? What analogous patterns have you used?"
                ),
                "rationale": f"Candidate lacked direct {target_missing} experience; testing engineering adaptability.",
                "ideal_response_key": (
                    "Candidate should draw direct analogies from tools they already know and articulate a methodical "
                    "proof-of-concept testing strategy."
                ),
                "follow_up_probe": f"What are common performance pitfalls you would anticipate when adopting {target_missing}?"
            })
        else:
            questions.append({
                "question_id": "tech_q2",
                "focus_area": "Database Concurrency & Polyglot Persistence",
                "question_prompt": (
                    "When designing high-throughput services, when would you choose an in-memory key-value store like Redis "
                    "versus a document store like MongoDB or relational PostgreSQL? How do you prevent cache stampedes?"
                ),
                "rationale": "Verifying deep polyglot persistence design acumen.",
                "ideal_response_key": (
                    "Should articulate trade-offs: relational ACID for transactions, documents for flexible hierarchies, "
                    "Redis for ephemeral caching and distributed locks with probabilistic early expiration (XFetch)."
                ),
                "follow_up_probe": "How do you implement distributed locking in Redis safely across cluster failovers?"
            })

        # ----------------------------------------------------------------------
        # Question 3: Production Incident & Debugging Scenario
        # ----------------------------------------------------------------------
        questions.append({
            "question_id": "tech_q3",
            "focus_area": "Root Cause Analysis & Incident Remediation",
            "question_prompt": (
                "Scenario: A critical microservice in production experiences an unexpected p99 latency spike from 40ms to 4500ms "
                "under normal request volume. Walk me through your step-by-step diagnostic checklist from metrics to code."
            ),
            "rationale": "Evaluates practical debugging methodology and production telemetry familiarity.",
            "ideal_response_key": (
                "Candidate should inspect APM traces (spans), database slow query logs, connection pool starvation, "
                "garbage collection pauses, thread contention, and network saturation before blindly restarting pods."
            ),
            "follow_up_probe": "How would you automate a circuit breaker to protect upstream services during this degradation?"
        })

        return {
            "agent": cls.NAME,
            "status": "COMPLETED",
            "total_questions_synthesized": len(questions),
            "questions": questions,
            "summary": f"Generated {len(questions)} high-signal technical interview questions tailored to candidate profile."
        }
