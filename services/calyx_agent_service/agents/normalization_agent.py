# ==============================================================================
# CALYX AGENT 1: EXTRACTION & NORMALIZATION AGENT
# ==============================================================================
# Concept Explanation for Beginners:
# What does the Normalization Agent do?
# Resumes are messy! One engineer writes "Built K8s clusters on AWS", another writes
# "Managed Elastic Kubernetes Service nodes", and a third writes "EKS administration".
# A human knows these are all the same thing, but naive software gets confused.
# The Normalization Agent acts as a linguistic translator: it cleans the text,
# resolves abbreviations into standard engineering taxonomy, and extracts structured
# competencies so downstream agents can evaluate with precision.
# ==============================================================================

import re
from typing import Dict, Any, List


class NormalizationAgent:
    """
    Autonomous agent responsible for cleaning, standardizing, and resolving
    domain-specific jargon into canonical technical competencies.
    """

    NAME = "Extraction & Normalization Agent"

    # Canonical mapping of colloquialisms and abbreviations to standard concepts
    TERM_SYNONYMS = {
        "k8s": "Kubernetes",
        "eks": "AWS Elastic Kubernetes Service",
        "gke": "Google Kubernetes Engine",
        "aks": "Azure Kubernetes Service",
        "postgres": "PostgreSQL",
        "mongo": "MongoDB",
        "golang": "Go",
        "py": "Python",
        "ts": "TypeScript",
        "js": "JavaScript",
        "tf": "Terraform",
        "hpa": "Horizontal Pod Autoscaler",
        "vpa": "Vertical Pod Autoscaler",
        "ci": "Continuous Integration",
        "cd": "Continuous Deployment"
    }

    @classmethod
    def run(cls, candidate_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes normalization workflow on candidate profile.
        Returns cleaned competencies, normalized titles, and standardized taxonomy.
        """
        raw_skills = candidate_profile.get("skills", [])
        raw_text = candidate_profile.get("raw_text_preview", "")
        
        # Step 1: Normalize skill strings
        canonical_skills = set()
        for skill in raw_skills:
            lower = skill.lower().strip()
            if lower in cls.TERM_SYNONYMS:
                canonical_skills.add(cls.TERM_SYNONYMS[lower])
            else:
                canonical_skills.add(skill.strip().title())

        # Step 2: Extract technical competencies from unstructured resume text
        lower_text = raw_text.lower()
        for term, standard in cls.TERM_SYNONYMS.items():
            if re.search(r"\b" + re.escape(term) + r"\b", lower_text):
                canonical_skills.add(standard)

        # Step 3: Determine primary engineering specialty
        specialty = "Full Stack Engineer"
        cloud_keywords = {"Kubernetes", "Docker", "Terraform", "Prometheus", "Aws Elastic Kubernetes Service", "Horizontal Pod Autoscaler"}
        ml_keywords = {"Pytorch", "Tensorflow", "Scikit-Learn", "Transformers", "Machine Learning"}
        
        cloud_overlap = len(canonical_skills.intersection(cloud_keywords))
        ml_overlap = len(canonical_skills.intersection(ml_keywords))

        if cloud_overlap > ml_overlap and cloud_overlap >= 2:
            specialty = "Cloud Infrastructure & DevOps Engineer"
        elif ml_overlap > cloud_overlap and ml_overlap >= 2:
            specialty = "Machine Learning / AI Engineer"

        return {
            "agent": cls.NAME,
            "status": "COMPLETED",
            "detected_specialty": specialty,
            "normalized_skills": sorted(list(canonical_skills)),
            "experience_years": candidate_profile.get("experience_years", 0),
            "summary": f"Identified {len(canonical_skills)} canonical skills. Primary specialty classified as '{specialty}'."
        }
