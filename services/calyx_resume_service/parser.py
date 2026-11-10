# ==============================================================================
# CALYX RESUME SERVICE: DOCUMENT INGESTION & ENTITY EXTRACTION
# ==============================================================================
# Concept Explanation for Beginners:
# 1. Optical & Document Text Extraction:
#    Resumes arrive in diverse file formats: PDF binary streams, Microsoft Word (.docx),
#    or plain text. The parser converts bytes into clean UTF-8 strings.
#
# 2. Entity Extraction & Skill Taxonomy:
#    Rather than dumb string matching, we match candidate text against a structured
#    taxonomy of hundreds of modern engineering technologies, programming languages,
#    cloud platforms, and architectures.
#
# 3. Regular Expressions (RegEx):
#    Mathematical pattern matching used to reliably extract emails, phone numbers,
#    and tenure date ranges (e.g. "2020 - 2024", "5+ years of experience").
# ==============================================================================

import re
import io
from typing import List, Dict, Any, Optional, Set
import pypdf
import docx

# Extensive taxonomy of technical skills for automated entity tagging
SKILLS_TAXONOMY: Set[str] = {
    # Cloud & DevOps
    "kubernetes", "k8s", "docker", "helm", "terraform", "ansible", "jenkins", "gitlab ci",
    "github actions", "argo cd", "prometheus", "grafana", "aws", "amazon web services",
    "gcp", "google cloud", "azure", "linux", "nginx", "istio", "envoy", "cloud native",

    # Programming Languages
    "python", "go", "golang", "java", "typescript", "javascript", "c++", "c#", "rust",
    "ruby", "scala", "kotlin", "bash", "sql", "html", "css",

    # Frameworks & Libraries
    "fastapi", "flask", "django", "spring boot", "react", "next.js", "angular", "vue",
    "express", "node.js", "pytorch", "tensorflow", "scikit-learn", "langchain", "celery",

    # Databases & Storage
    "postgresql", "postgres", "mongodb", "redis", "mysql", "cassandra", "dynamodb",
    "qdrant", "chromadb", "elasticsearch", "kafka", "rabbitmq",

    # Architecture & Concepts
    "microservices", "rest api", "graphql", "grpc", "event-driven", "system design",
    "distributed systems", "ci/cd", "agile", "tdd", "object oriented programming", "oop",
    "concurrency", "horizontal pod autoscaler", "hpa", "load balancing"
}

# Common education degree patterns
DEGREE_PATTERNS = [
    r"\b(?:b\.?tech|b\.?e\.?|bachelor(?:'s)?(?:\s+of\s+science)?|b\.?s\.?)\b",
    r"\b(?:m\.?tech|m\.?e\.?|master(?:'s)?(?:\s+of\s+science)?|m\.?s\.?|m\.?b\.?a\.?)\b",
    r"\b(?:ph\.?d\.?|doctorate)\b"
]


class ResumeParser:
    """
    Parser that extracts raw text and structured entities from uploaded resumes.
    """

    @classmethod
    def extract_text_from_bytes(cls, file_bytes: bytes, filename: str) -> str:
        """
        Extracts raw textual content from PDF, DOCX, or plain text bytes.
        """
        lower_name = filename.lower()
        extracted_text = ""

        if lower_name.endswith(".pdf"):
            # Use pypdf to read PDF pages
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                page_text = page.extract_text() or ""
                extracted_text += page_text + "\n"

        elif lower_name.endswith(".docx"):
            # Use python-docx to read Word document paragraphs and tables
            doc = docx.Document(io.BytesIO(file_bytes))
            for para in doc.paragraphs:
                extracted_text += para.text + "\n"
            for table in doc.tables:
                for row in table.rows:
                    row_text = " ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                    extracted_text += row_text + "\n"

        else:
            # Assume plain text / UTF-8 string
            try:
                extracted_text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                extracted_text = file_bytes.decode("latin-1", errors="ignore")

        return extracted_text.strip()

    @classmethod
    def extract_skills(cls, text: str) -> List[str]:
        """
        Scans resume text against SKILLS_TAXONOMY and returns detected unique skills.
        """
        lower_text = text.lower()
        detected_skills: Set[str] = set()

        for skill in SKILLS_TAXONOMY:
            # Word boundary regex pattern ensures 'go' doesn't match 'good'
            pattern = r"(?:^|[\s,.;:/\(\)\[\]])" + re.escape(skill) + r"(?:$|[\s,.;:/\(\)\[\]])"
            if re.search(pattern, lower_text):
                # Standardize acronyms (e.g. k8s -> Kubernetes)
                if skill == "k8s":
                    detected_skills.add("Kubernetes")
                elif skill == "postgres":
                    detected_skills.add("PostgreSQL")
                elif skill == "golang":
                    detected_skills.add("Go")
                else:
                    detected_skills.add(skill.title())

        return sorted(list(detected_skills))

    @classmethod
    def extract_email(cls, text: str) -> Optional[str]:
        """
        Extracts the first valid email address from the resume text using regex.
        """
        match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
        return match.group(0).lower() if match else None

    @classmethod
    def extract_phone(cls, text: str) -> Optional[str]:
        """
        Extracts phone numbers matching common international or domestic formats.
        """
        match = re.search(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}", text)
        return match.group(0) if match else None

    @classmethod
    def estimate_experience_years(cls, text: str) -> int:
        """
        Estimates total years of professional experience using tenure phrases and date spans.
        """
        lower_text = text.lower()
        
        # 1. Check for explicit phrases like "5+ years", "6 years of experience"
        phrase_matches = re.findall(r"(\d{1,2})\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience", lower_text)
        if phrase_matches:
            numbers = [int(m) for m in phrase_matches if 0 < int(m) <= 40]
            if numbers:
                return max(numbers)

        # 2. Check for 4-digit years (e.g. 2018 - 2024)
        year_matches = re.findall(r"\b(20[0-2][0-9]|199[0-9])\b", text)
        if len(year_matches) >= 2:
            years = sorted([int(y) for y in year_matches])
            span = years[-1] - years[0]
            if 0 < span <= 35:
                return span

        # Default fallback estimate
        return 2

    @classmethod
    def extract_education(cls, text: str) -> List[str]:
        """
        Detects educational credentials mentioned in the document.
        """
        degrees_found = set()
        lower_text = text.lower()
        for pattern in DEGREE_PATTERNS:
            matches = re.findall(pattern, lower_text)
            for m in matches:
                degrees_found.add(m.upper().replace(".", ""))
        return sorted(list(degrees_found))

    @classmethod
    def parse_full_resume(cls, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Orchestrates full parsing pipeline: extracts raw text, contacts, skills,
        experience duration, and education.
        """
        raw_text = cls.extract_text_from_bytes(file_bytes, filename)
        skills = cls.extract_skills(raw_text)
        email = cls.extract_email(raw_text)
        phone = cls.extract_phone(raw_text)
        exp_years = cls.estimate_experience_years(raw_text)
        education = cls.extract_education(raw_text)

        # Extract first line or clean title as candidate name heuristic
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        candidate_name = lines[0] if lines else "Candidate"
        if len(candidate_name) > 60:
            candidate_name = candidate_name[:60]

        return {
            "file_name": filename,
            "raw_text": raw_text,
            "candidate_name": candidate_name,
            "email": email,
            "phone": phone,
            "skills": skills,
            "experience_years": exp_years,
            "education": education,
            "character_count": len(raw_text),
            "word_count": len(raw_text.split())
        }
