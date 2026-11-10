# ==============================================================================
# CALYX AGENT SERVICE: MULTI-AGENT STATE MACHINE & ORCHESTRATOR
# ==============================================================================
# Concept Explanation for Beginners:
# 1. Multi-Agent Orchestration:
#    Rather than having one generalist prompt, CALYX employs a "Society of Agents".
#    The Orchestrator coordinates the workflow:
#      Step 1: Normalization Agent structures the raw candidate text.
#      Step 2: Criteria Matching Agent scores against the recruiter's rubric.
#      Step 3: Bias Audit Agent inspects the evaluation for ethical fairness.
#      Step 4: Interview Agent crafts personalized follow-up technical questions.
#      Step 5: Consensus Synthesis compiles the final report and updates Redis!
#
# 2. Redis State Machine:
#    Every thought, decision, and intermediate output is logged chronologically to
#    Redis. If any sub-agent fails, the orchestrator can retry or recover without
#    losing state.
# ==============================================================================

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from common.logging_config import configure_logger
from services.calyx_agent_service.config import agent_settings
from services.calyx_agent_service.state_store import AgentStateStore
from services.calyx_agent_service.agents.normalization_agent import NormalizationAgent
from services.calyx_agent_service.agents.criteria_agent import CriteriaMatchingAgent
from services.calyx_agent_service.agents.bias_agent import BiasAuditAgent
from services.calyx_agent_service.agents.interview_agent import TechnicalInterviewAgent

logger = configure_logger(agent_settings.SERVICE_NAME, agent_settings.LOG_LEVEL)


class AgentOrchestrator:
    """
    Coordinates the multi-agent consensus workflow and maintains state in Redis.
    """

    @classmethod
    def evaluate_candidate(
        cls,
        state_store: AgentStateStore,
        application_id: str,
        candidate_profile: Dict[str, Any],
        job_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes the 4-agent consensus loop for a candidate application.
        """
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        now_str = datetime.now(timezone.utc).isoformat()
        lock_name = f"eval_{application_id}"

        # ----------------------------------------------------------------------
        # Step 0: Acquire Distributed Lock in Redis to prevent race conditions
        # ----------------------------------------------------------------------
        if not state_store.acquire_lock(lock_name, expire_seconds=120):
            logger.warning(f"Evaluation already in progress for application: {application_id}")
            return {
                "task_id": task_id,
                "status": "IN_PROGRESS",
                "message": "Evaluation currently in progress by another agent worker."
            }

        try:
            # Initialize task record in Redis
            initial_state = {
                "task_id": task_id,
                "application_id": application_id,
                "candidate_id": candidate_profile.get("candidate_id"),
                "status": "PROCESSING",
                "current_step": "NORMALIZATION",
                "started_at": now_str
            }
            state_store.save_task_state(task_id, initial_state)

            # ------------------------------------------------------------------
            # Step 1: Execute Normalization Agent
            # ------------------------------------------------------------------
            logger.info(f"[{task_id}] Step 1: Invoking Normalization Agent...")
            norm_result = NormalizationAgent.run(candidate_profile)
            state_store.append_trace_step(
                task_id=task_id,
                agent_name=NormalizationAgent.NAME,
                thought="Standardizing colloquial technical terms and resolving synonyms into canonical skills.",
                action="NORMALIZE_SKILLS_AND_SPECIALTY",
                output=norm_result
            )

            # ------------------------------------------------------------------
            # Step 2: Execute Criteria & Rubric Matching Agent
            # ------------------------------------------------------------------
            logger.info(f"[{task_id}] Step 2: Invoking Criteria Matching Agent...")
            criteria_result = CriteriaMatchingAgent.run(
                normalized_data=norm_result,
                job_requirements=job_requirements
            )
            state_store.append_trace_step(
                task_id=task_id,
                agent_name=CriteriaMatchingAgent.NAME,
                thought="Evaluating candidate depth against each weighted rubric category and calculating composite score.",
                action="SCORE_RUBRICS",
                output=criteria_result
            )

            # ------------------------------------------------------------------
            # Step 3: Execute Fairness & Bias Audit Agent
            # ------------------------------------------------------------------
            logger.info(f"[{task_id}] Step 3: Invoking Bias & Fairness Audit Agent...")
            bias_result = BiasAuditAgent.run(
                candidate_profile=candidate_profile,
                criteria_evaluation=criteria_result
            )
            state_store.append_trace_step(
                task_id=task_id,
                agent_name=BiasAuditAgent.NAME,
                thought="Auditing scoring integrity: scrubbing demographic signals and verifying merit-only score basis.",
                action="AUDIT_FAIRNESS",
                output=bias_result
            )

            # ------------------------------------------------------------------
            # Step 4: Execute Dynamic Technical Interview Synthesizer Agent
            # ------------------------------------------------------------------
            logger.info(f"[{task_id}] Step 4: Invoking Technical Interview Synthesizer...")
            interview_result = TechnicalInterviewAgent.run(
                normalized_data=norm_result,
                criteria_evaluation=criteria_result
            )
            state_store.append_trace_step(
                task_id=task_id,
                agent_name=TechnicalInterviewAgent.NAME,
                thought="Synthesizing high-signal technical questions targeting resume claims and potential blindspots.",
                action="GENERATE_QUESTIONS_AND_ANSWER_KEYS",
                output=interview_result
            )

            # ------------------------------------------------------------------
            # Step 5: Multi-Agent Consensus Synthesis
            # ------------------------------------------------------------------
            final_score = criteria_result.get("overall_match_score", 0.0)
            specialty = norm_result.get("detected_specialty", "Software Engineer")
            audit_pass = bias_result.get("audit_passed", False)
            
            synthesis_summary = (
                f"Multi-Agent Evaluation Consensus: Candidate classified as '{specialty}' with a composite "
                f"rubric score of {final_score}%. Fairness Audit: {'PASSED' if audit_pass else 'FLAGGED'}. "
                f"Generated {interview_result.get('total_questions_synthesized', 0)} personalized technical interview questions."
            )

            completed_state = {
                "task_id": task_id,
                "application_id": application_id,
                "candidate_id": candidate_profile.get("candidate_id"),
                "status": "COMPLETED",
                "final_score": final_score,
                "detected_specialty": specialty,
                "fairness_audit": bias_result,
                "rubric_breakdown": criteria_result.get("rubric_breakdowns", []),
                "interview_questionnaire": interview_result.get("questions", []),
                "executive_summary": synthesis_summary,
                "completed_at": datetime.now(timezone.utc).isoformat()
            }
            state_store.save_task_state(task_id, completed_state)
            logger.info(f"[{task_id}] Multi-agent consensus reached successfully. Score: {final_score}%")

            return completed_state

        finally:
            # Guarantee lock release in Redis
            state_store.release_lock(lock_name)
