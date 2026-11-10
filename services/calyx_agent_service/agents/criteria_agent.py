# ==============================================================================
# CALYX AGENT 2: CRITERIA & RUBRIC MATCHING AGENT
# ==============================================================================
# Concept Explanation for Beginners:
# What does the Criteria Matching Agent do?
# Instead of giving a single black-box score ("Candidate is 82%"), this agent breaks
# down the candidate against the recruiter's exact hiring rubric.
# For example, if the job has:
# - System Architecture (weight 40%)
# - Container Orchestration (weight 40%)
# - Communication & Leadership (weight 20%)
# This agent evaluates each category individually, calculates weighted mathematical
# contributions, and provides transparent explanations for every single grade.
# ==============================================================================

from typing import Dict, Any, List


class CriteriaMatchingAgent:
    """
    Autonomous agent responsible for evaluating candidates against structured
    hiring rubrics and computing weighted scoring distributions.
    """

    NAME = "Criteria & Rubric Matching Agent"

    @classmethod
    def run(
        cls,
        normalized_data: Dict[str, Any],
        job_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluates candidate against job requirements and custom rubrics.
        """
        candidate_skills = set([s.lower() for s in normalized_data.get("normalized_skills", [])])
        candidate_exp = normalized_data.get("experience_years", 0)
        
        required_skills = job_requirements.get("required_skills", [])
        rubric_criteria = job_requirements.get("rubric_criteria", [])
        min_years = job_requirements.get("min_years_exp", 0)

        # ----------------------------------------------------------------------
        # 1. Required Skills Evaluation
        # ----------------------------------------------------------------------
        matched_required = []
        missing_required = []
        skill_score_sum = 0.0
        total_weight_sum = 0.0

        for req in required_skills:
            # req can be dict with 'name' and 'weight'
            name = req.get("name", "").lower() if isinstance(req, dict) else str(req).lower()
            weight = req.get("weight", 1.0) if isinstance(req, dict) else 1.0
            total_weight_sum += weight

            # Check if candidate has skill
            if any(name in cand_s or cand_s in name for cand_s in candidate_skills):
                matched_required.append(name.title())
                skill_score_sum += weight
            else:
                missing_required.append(name.title())

        skill_match_ratio = (skill_score_sum / total_weight_sum) if total_weight_sum > 0 else 1.0

        # ----------------------------------------------------------------------
        # 2. Experience Tenure Score
        # ----------------------------------------------------------------------
        if candidate_exp >= min_years:
            exp_score = 1.0
        elif candidate_exp > 0:
            exp_score = candidate_exp / max(1, min_years)
        else:
            exp_score = 0.5

        # ----------------------------------------------------------------------
        # 3. Rubric Breakdown Evaluation
        # ----------------------------------------------------------------------
        category_breakdowns = []
        rubric_total_score = 0.0

        if not rubric_criteria:
            # Fallback standard rubric if recruiter did not provide custom criteria
            rubric_criteria = [
                {"category": "Core Technical Competency", "weight": 0.6, "description": "Hands-on tools and technical languages"},
                {"category": "Domain Experience & Seniority", "weight": 0.4, "description": "Years of experience and architecture depth"}
            ]

        for crit in rubric_criteria:
            cat_name = crit.get("category", "General")
            cat_weight = crit.get("weight", 0.5)

            # Heuristic category scoring based on skill presence and experience
            if "Container" in cat_name or "Cloud" in cat_name or "DevOps" in cat_name:
                has_cloud = any(k in candidate_skills for k in ["kubernetes", "docker", "aws", "gcp", "terraform"])
                grade = 95.0 if has_cloud else 40.0
            elif "System" in cat_name or "Architecture" in cat_name or "Distributed" in cat_name:
                has_arch = any(k in candidate_skills for k in ["microservices", "postgresql", "redis", "concurrency", "python"])
                grade = 90.0 if has_arch else 50.0
            else:
                grade = round(min(100.0, (skill_match_ratio * 60.0) + (exp_score * 40.0)), 1)

            weighted_contribution = round(grade * cat_weight, 2)
            rubric_total_score += weighted_contribution

            category_breakdowns.append({
                "category": cat_name,
                "weight": cat_weight,
                "score": grade,
                "weighted_score": weighted_contribution,
                "justification": f"Candidate demonstrated {len(matched_required)} relevant skills with {candidate_exp} years tenure."
            })

        # Calculate final composite score (0 to 100)
        final_score = round(min(100.0, rubric_total_score), 1)

        return {
            "agent": cls.NAME,
            "status": "COMPLETED",
            "overall_match_score": final_score,
            "skill_match_ratio": round(skill_match_ratio * 100.0, 1),
            "matched_required_skills": matched_required,
            "missing_required_skills": missing_required,
            "rubric_breakdowns": category_breakdowns,
            "summary": f"Calculated composite score of {final_score}% across {len(category_breakdowns)} rubric dimensions."
        }
