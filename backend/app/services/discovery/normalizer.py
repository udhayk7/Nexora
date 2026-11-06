import re
from typing import Optional

from app.services.matching_engine import normalize_skill_name

# Nexora Technical Role Family Definitions
ROLE_FAMILY_PATTERNS: list[tuple[str, list[str]]] = [
    (
        "Generative AI / LLM Engineer",
        [
            r"\b(generative ai|genai|llm|llms|rag|prompt engineer)\b",
            r"\b(diffusion model|langchain|llamaindex|agentic ai)\b",
            r"\b(large language model|fine-tuning llm)\b",
        ],
    ),
    (
        "AI Engineer",
        [
            r"\b(ai engineer|artificial intelligence engineer|ai developer)\b",
            r"\b(applied ai|deep learning|computer vision engineer|nlp engineer)\b",
        ],
    ),
    (
        "Machine Learning Engineer",
        [
            r"\b(machine learning engineer|ml engineer|ml developer|ml ops|mlops)\b",
            r"\b(machine learning scientist|applied scientist|model training)\b",
        ],
    ),
    (
        "Python Backend Developer",
        [
            r"\b(python backend|python developer|python engineer)\b",
            r"\b(django developer|fastapi developer|flask developer)\b",
            r"\b(backend engineer|backend developer|server-side engineer)\b.*?\b(python)\b",
            r"\b(python)\b.*?\b(backend engineer|backend developer|server engineer)\b",
        ],
    ),
    (
        "Frontend Developer",
        [
            r"\b(frontend|front-end|front end|ui developer|ui engineer)\b",
            r"\b(react developer|vue developer|angular developer|web frontend)\b",
        ],
    ),
    (
        "Full Stack Developer",
        [
            r"\b(full stack|fullstack|full-stack|full stack engineer|full stack developer)\b",
        ],
    ),
    (
        "Data Engineer",
        [
            r"\b(data engineer|data platform engineer|big data engineer)\b",
            r"\b(data pipeline|etl developer|analytics engineer)\b",
        ],
    ),
    (
        "Data Analyst",
        [
            r"\b(data analyst|business intelligence analyst|bi analyst)\b",
            r"\b(bi developer|reporting analyst|insights analyst)\b",
        ],
    ),
    (
        "Automation Engineer",
        [
            r"\b(automation engineer|qa automation|sdet|test automation)\b",
            r"\b(software development engineer in test|qa engineer)\b",
        ],
    ),
    (
        "Software Development Engineer",
        [
            r"\b(software development engineer|software engineer|sde|sde-1|sde 1)\b",
            r"\b(software developer|graduate software|associate software engineer)\b",
        ],
    ),
]

# Keywords that signal early-career / fresher / graduate positions
EARLY_CAREER_PATTERNS = [
    r"\b(fresher|freshers|graduate|graduates|new grad|new graduate|recent graduate)\b",
    r"\b(campus hire|trainee|apprentice|apprenticeship|intern|internship|co-op)\b",
    r"\b(entry level|entry-level|junior|jr\.|associate|level 1|l1|sde 1|sde-1)\b",
    r"\b(0-1 year|0-2 years|0 to 1 year|0 to 2 years|no prior experience required)\b",
]

# Senior / management signals that contradict early career
SENIOR_PATTERNS = [
    r"\b(senior|sr\.|lead|principal|staff|director|head of|vp|manager|architect)\b",
    r"\b(5\+ years|6\+ years|7\+ years|8\+ years|10\+ years)\b",
]

# Comprehensive Tech Stack Skill Dictionary
KNOWN_SKILLS: list[str] = [
    "python",
    "javascript",
    "typescript",
    "go",
    "golang",
    "rust",
    "java",
    "c++",
    "c#",
    "ruby",
    "php",
    "swift",
    "kotlin",
    "react",
    "next.js",
    "vue",
    "angular",
    "svelte",
    "html",
    "css",
    "tailwind",
    "node.js",
    "fastapi",
    "django",
    "flask",
    "express",
    "spring boot",
    ".net",
    "postgresql",
    "mysql",
    "sqlite",
    "mongodb",
    "redis",
    "elasticsearch",
    "cassandra",
    "docker",
    "kubernetes",
    "aws",
    "gcp",
    "azure",
    "ci/cd",
    "git",
    "terraform",
    "linux",
    "pytorch",
    "tensorflow",
    "keras",
    "scikit-learn",
    "pandas",
    "numpy",
    "opencv",
    "huggingface",
    "langchain",
    "llamaindex",
    "spark",
    "kafka",
    "airflow",
    "hadoop",
    "dbt",
    "snowflake",
    "bigquery",
    "tableau",
    "power bi",
    "sql",
    "graphql",
    "rest",
    "selenium",
    "playwright",
    "cypress",
    "pytest",
    "jest",
]


class JobNormalizer:
    """Deterministic normalization engine for job titles, classifications, and requirements."""

    @classmethod
    def classify_role_family(cls, title: str, description: str = "") -> Optional[str]:
        """Classify a job into one of the 10 approved Nexora role families."""
        combined_text = f"{title}\n{description}".lower()

        title_lower = title.lower()
        for role_family, patterns in ROLE_FAMILY_PATTERNS:
            for pat in patterns:
                if re.search(pat, title_lower, re.IGNORECASE):
                    return role_family

        for role_family, patterns in ROLE_FAMILY_PATTERNS:
            for pat in patterns:
                if re.search(pat, combined_text, re.IGNORECASE):
                    return role_family

        return None

    @classmethod
    def classify_seniority(cls, title: str, description: str = "") -> tuple[str, bool]:
        """Determine seniority level and whether job is relevant for early-career candidates."""
        combined = f"{title}\n{description}".lower()
        title_lower = title.lower()

        # Check for internship
        if re.search(r"\b(intern|internship|co-op|coop|apprentice|trainee)\b", title_lower):
            return "internship", True

        # Check for senior indicators first to avoid false positives
        is_senior = any(re.search(pat, title_lower) for pat in SENIOR_PATTERNS)
        if is_senior:
            return "senior", False

        # Check for explicit early-career indicators in title or description
        is_early_career = any(re.search(pat, combined) for pat in EARLY_CAREER_PATTERNS)

        if is_early_career:
            if re.search(r"\b(intern|internship|trainee|apprentice)\b", combined):
                return "internship", True
            if re.search(r"\b(junior|jr\.)\b", title_lower):
                return "junior", True
            return "entry_level", True

        # Default fallback
        if re.search(r"\b(mid|intermediate|experienced|2-4 years|3-5 years)\b", combined):
            return "mid_level", False

        # If title doesn't specify senior, treat unannotated roles as early-career candidate
        return "entry_level", True

    @classmethod
    def classify_work_arrangement(cls, location_text: str = "", description: str = "") -> str:
        """Classify work arrangement as 'remote', 'hybrid', 'onsite', or 'unspecified'."""
        text = f"{location_text} {description[:500]}".lower()

        if re.search(
            r"\b(remote|work from home|wfh|anywhere|telecommute|distributed team)\b", text
        ):
            if re.search(r"\b(hybrid|partially remote|flexible office)\b", text):
                return "hybrid"
            return "remote"

        if re.search(r"\b(hybrid|flexible location|partial remote)\b", text):
            return "hybrid"

        if re.search(r"\b(on-site|onsite|in-office|office based|in person)\b", text):
            return "onsite"

        return "unspecified"

    @classmethod
    def classify_employment_type(cls, raw_type: Optional[str] = None, text: str = "") -> str:
        """Normalize employment type to full_time, internship, contract, or part_time."""
        check = f"{raw_type or ''} {text[:300]}".lower()

        if re.search(r"\b(intern|internship|trainee|co-op)\b", check):
            return "internship"
        if re.search(r"\b(contract|contractor|temporary|freelance)\b", check):
            return "contract"
        if re.search(r"\b(part-time|part time)\b", check):
            return "part_time"

        return "full_time"

    @classmethod
    def extract_skills(cls, text: str) -> list[str]:
        """Extract and normalize technical skills from job title and description."""
        if not text:
            return []

        text_lower = text.lower()
        found: set[str] = set()

        for skill in KNOWN_SKILLS:
            escaped = re.escape(skill)
            if re.search(rf"(?<!\w){escaped}(?!\w)", text_lower):
                canonical = normalize_skill_name(skill)
                found.add(canonical)

        return sorted(found)

    @classmethod
    def extract_structured_sections(cls, text: str) -> dict[str, list[str]]:
        """Extract structured sections such as responsibilities and qualifications."""
        sections: dict[str, list[str]] = {
            "responsibilities": [],
            "required_qualifications": [],
            "preferred_qualifications": [],
        }
        if not text:
            return sections

        lines = text.split("\n")
        current_section: Optional[str] = None

        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                continue

            lower_line = trimmed.lower()
            if re.match(
                r"^(responsibilities|what you('ll| will) do|key duties|the role):?$",
                lower_line,
            ):
                current_section = "responsibilities"
                continue
            elif re.match(
                r"^(requirements|what you need|qualifications|basic qualifications|must have):?$",
                lower_line,
            ):
                current_section = "required_qualifications"
                continue
            elif re.match(
                r"^(nice to have|preferred qualifications|bonus points|good to have):?$",
                lower_line,
            ):
                current_section = "preferred_qualifications"
                continue

            if current_section and (
                trimmed.startswith(("-", "•", "*", "–")) or re.match(r"^\d+\.", trimmed)
            ):
                clean_item = re.sub(r"^[-•*–\d\.\s]+", "", trimmed).strip()
                if len(clean_item) > 5:
                    sections[current_section].append(clean_item)

        return sections

    @classmethod
    def parse_explicit_salary(
        cls, text: str
    ) -> tuple[Optional[float], Optional[float], Optional[str], Optional[str]]:
        """Extract explicitly stated salary range from text. NEVER estimates or fabricates figures.

        Returns:
            (salary_min, salary_max, currency, period)
        """
        if not text:
            return None, None, None, None

        # Explicit INR formats (e.g. 6 - 12 LPA)
        lpa_match = re.search(
            r"(?:inr|rs\.?|₹)?\s*(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*"
            r"(?:lpa|lakhs?|lac|lacs?)\b",
            text,
            re.IGNORECASE,
        )
        if lpa_match:
            min_val = float(lpa_match.group(1)) * 100000.0
            max_val = float(lpa_match.group(2)) * 100000.0
            return min_val, max_val, "INR", "annual"

        currency_map = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR"}
        range_match = re.search(
            r"([$€£₹])\s*(\d[\d,]*)(?:k)?\s*(?:-|to)\s*([$€£₹])?\s*"
            r"(\d[\d,]*)(k)?\s*"
            r"(?:per\s+(year|month|hr|hour)|/(?:yr|year|mo|month|hr|hour)|annually)?",
            text,
            re.IGNORECASE,
        )
        if range_match:
            curr_sym = range_match.group(1)
            raw_min = range_match.group(2).replace(",", "")
            raw_max = range_match.group(4).replace(",", "")
            is_k = bool(range_match.group(5)) or ("k" in text.lower())
            period_token = range_match.group(6) or ""

            try:
                val_min = float(raw_min) * (1000.0 if (is_k and float(raw_min) < 1000) else 1.0)
                val_max = float(raw_max) * (1000.0 if (is_k and float(raw_max) < 1000) else 1.0)
            except ValueError:
                return None, None, None, None

            period = "annual"
            if "month" in period_token.lower() or "mo" in period_token.lower():
                period = "monthly"
            elif "hr" in period_token.lower() or "hour" in period_token.lower():
                period = "hourly"

            return val_min, val_max, currency_map.get(curr_sym, "USD"), period

        return None, None, None, None
