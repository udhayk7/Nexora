"""Technology intelligence extractor and evidence strength classifier.

Identifies programming languages, frameworks, cloud platforms, databases,
AI/ML tools, devops tooling, and engineering practices, classifying evidence
into: confirmed, supported, inferred, unknown.
"""

import re
from typing import Any, Optional

TECH_TAXONOMY: list[dict[str, Any]] = [
    # Languages
    {"name": "Python", "category": "languages", "patterns": [r"\bpython\b", r"\bpy3\b"]},
    {"name": "TypeScript", "category": "languages", "patterns": [r"\btypescript\b", r"\bts\b"]},
    {
        "name": "JavaScript",
        "category": "languages",
        "patterns": [r"\bjavascript\b", r"\bjs\b", r"\bes6\b"],
    },
    {"name": "Go", "category": "languages", "patterns": [r"\bgolang\b", r"\bgo\s+language\b"]},
    {"name": "Java", "category": "languages", "patterns": [r"\bjava\b", r"\bjdk\b", r"\bjvm\b"]},
    {"name": "C++", "category": "languages", "patterns": [r"\bc\+\+\b", r"\bcpp\b"]},
    {"name": "C#", "category": "languages", "patterns": [r"\bc#\b", r"\bcsharp\b", r"\b\.net\b"]},
    {"name": "Rust", "category": "languages", "patterns": [r"\brust\b", r"\bcargo\b"]},
    {"name": "Ruby", "category": "languages", "patterns": [r"\bruby\b", r"\bror\b"]},
    {"name": "Kotlin", "category": "languages", "patterns": [r"\bkotlin\b"]},
    {"name": "Swift", "category": "languages", "patterns": [r"\bswift\b"]},
    {
        "name": "SQL",
        "category": "languages",
        "patterns": [r"\bsql\b", r"\bpostgresql\b", r"\bmysql\b"],
    },
    # Frameworks
    {
        "name": "React",
        "category": "frameworks",
        "patterns": [r"\breact\b", r"\breactjs\b", r"\breact\.js\b"],
    },
    {"name": "Next.js", "category": "frameworks", "patterns": [r"\bnext\.?js\b", r"\bnextjs\b"]},
    {"name": "FastAPI", "category": "frameworks", "patterns": [r"\bfastapi\b"]},
    {"name": "Django", "category": "frameworks", "patterns": [r"\bdjango\b"]},
    {"name": "Flask", "category": "frameworks", "patterns": [r"\bflask\b"]},
    {"name": "Node.js", "category": "frameworks", "patterns": [r"\bnode\.?js\b", r"\bnodejs\b"]},
    {
        "name": "Spring Boot",
        "category": "frameworks",
        "patterns": [r"\bspring\s*boot\b", r"\bspring\s+framework\b"],
    },
    {"name": "Vue.js", "category": "frameworks", "patterns": [r"\bvue\.?js\b", r"\bvuejs\b"]},
    {"name": "Angular", "category": "frameworks", "patterns": [r"\bangular\b"]},
    {
        "name": "Express.js",
        "category": "frameworks",
        "patterns": [r"\bexpress\.?js\b", r"\bexpressjs\b"],
    },
    {"name": "GraphQL", "category": "frameworks", "patterns": [r"\bgraphql\b", r"\bapollo\b"]},
    # Cloud & Infrastructure
    {
        "name": "AWS",
        "category": "cloud_platforms",
        "patterns": [r"\baws\b", r"\bamazon web services\b", r"\bec2\b", r"\bs3\b"],
    },
    {
        "name": "Google Cloud",
        "category": "cloud_platforms",
        "patterns": [r"\bgoogle cloud\b", r"\bgcp\b", r"\bbigquery\b"],
    },
    {
        "name": "Azure",
        "category": "cloud_platforms",
        "patterns": [r"\bazure\b", r"\bmicrosoft azure\b"],
    },
    {
        "name": "Kubernetes",
        "category": "cloud_platforms",
        "patterns": [r"\bkubernetes\b", r"\bk8s\b"],
    },
    {
        "name": "Docker",
        "category": "cloud_platforms",
        "patterns": [r"\bdocker\b", r"\bcontainerization\b"],
    },
    {
        "name": "Terraform",
        "category": "cloud_platforms",
        "patterns": [r"\bterraform\b", r"\biac\b"],
    },
    # Databases
    {
        "name": "PostgreSQL",
        "category": "databases",
        "patterns": [r"\bpostgres\b", r"\bpostgresql\b"],
    },
    {"name": "MySQL", "category": "databases", "patterns": [r"\bmysql\b"]},
    {"name": "MongoDB", "category": "databases", "patterns": [r"\bmongodb\b", r"\bmongo\b"]},
    {"name": "Redis", "category": "databases", "patterns": [r"\bredis\b"]},
    {
        "name": "Elasticsearch",
        "category": "databases",
        "patterns": [r"\belasticsearch\b", r"\belastic\b", r"\bopensearch\b"],
    },
    {"name": "Snowflake", "category": "databases", "patterns": [r"\bsnowflake\b"]},
    # AI & ML
    {"name": "PyTorch", "category": "aiml", "patterns": [r"\bpytorch\b"]},
    {"name": "TensorFlow", "category": "aiml", "patterns": [r"\btensorflow\b", r"\btf\b"]},
    {
        "name": "Large Language Models",
        "category": "aiml",
        "patterns": [
            r"\bllm\b",
            r"\bllms\b",
            r"\blarge language models\b",
            r"\bgenerative ai\b",
            r"\bgenai\b",
        ],
    },
    {"name": "LangChain", "category": "aiml", "patterns": [r"\blangchain\b", r"\blanggraph\b"]},
    {
        "name": "Hugging Face",
        "category": "aiml",
        "patterns": [r"\bhugging\s*face\b", r"\btransformers\b"],
    },
    {"name": "scikit-learn", "category": "aiml", "patterns": [r"\bscikit-learn\b", r"\bsklearn\b"]},
    # DevOps & Tools
    {"name": "Git", "category": "devops", "patterns": [r"\bgit\b", r"\bgithub\b", r"\bgitlab\b"]},
    {
        "name": "CI/CD",
        "category": "devops",
        "patterns": [r"\bci/cd\b", r"\bgithub actions\b", r"\bjenkins\b"],
    },
    {"name": "Prometheus", "category": "devops", "patterns": [r"\bprometheus\b", r"\bgrafana\b"]},
    {
        "name": "Kafka",
        "category": "devops",
        "patterns": [r"\bkafka\b", r"\bapache kafka\b", r"\bevent-driven\b"],
    },
    # Engineering Practices
    {
        "name": "Microservices",
        "category": "practices",
        "patterns": [r"\bmicroservices\b", r"\bdistributed systems\b"],
    },
    {
        "name": "Agile / Scrum",
        "category": "practices",
        "patterns": [r"\bagile\b", r"\bscrum\b", r"\bsprint\b"],
    },
    {
        "name": "Test-Driven Development",
        "category": "practices",
        "patterns": [r"\btdd\b", r"\bunit testing\b", r"\bautomated testing\b"],
    },
    {
        "name": "REST APIs",
        "category": "practices",
        "patterns": [r"\brest\b", r"\brestful\b", r"\bapi design\b"],
    },
]


def extract_technologies_with_evidence(
    official_sources_text: str,
    job_descriptions: list[str],
    company_tags: Optional[list[str]] = None,
    unverified_sources_text: str = "",
) -> list[dict[str, Any]]:
    """Analyze company textual assets and job descriptions, classifying evidence strength.

    Classification Rules:
    - 'confirmed': direct mention in verified official company web sources / publications.
    - 'supported': mentioned across 2 or more active job postings.
    - 'inferred': mentioned in 1 job posting, unverified third-party sources, or company tags.
    - 'unknown': not detected with verified evidence.
    """
    official_lower = official_sources_text.lower() if official_sources_text else ""
    unverified_lower = unverified_sources_text.lower() if unverified_sources_text else ""
    job_lowers = [jd.lower() for jd in job_descriptions if jd]
    tags_lower = [t.lower() for t in (company_tags or []) if t]

    results: list[dict[str, Any]] = []

    for item in TECH_TAXONOMY:
        name = item["name"]
        category = item["category"]
        patterns = item["patterns"]

        # 1. Check verified official sources
        official_match = False
        official_context: Optional[str] = None
        for pat in patterns:
            m = re.search(pat, official_lower)
            if m:
                official_match = True
                start = max(0, m.start() - 40)
                end = min(len(official_lower), m.end() + 40)
                official_context = official_lower[start:end].strip()
                break

        # 2. Check unverified third-party sources
        unverified_match = False
        unverified_context: Optional[str] = None
        if not official_match:
            for pat in patterns:
                m = re.search(pat, unverified_lower)
                if m:
                    unverified_match = True
                    start = max(0, m.start() - 40)
                    end = min(len(unverified_lower), m.end() + 40)
                    unverified_context = unverified_lower[start:end].strip()
                    break

        # 3. Count job posting matches
        job_matches_count = 0
        job_context: Optional[str] = None
        for jd in job_lowers:
            for pat in patterns:
                m = re.search(pat, jd)
                if m:
                    job_matches_count += 1
                    if not job_context:
                        start = max(0, m.start() - 40)
                        end = min(len(jd), m.end() + 40)
                        job_context = jd[start:end].strip()
                    break

        # 4. Check tags
        tag_match = any(
            (tag == name.lower() or any(re.search(pat, tag) for pat in patterns))
            for tag in tags_lower
        )

        strength: str = "unknown"
        source: str = ""
        context: Optional[str] = None

        if official_match:
            strength = "confirmed"
            source = "Direct mention in verified official company documentation / web publications"
            context = official_context
        elif job_matches_count >= 2:
            strength = "supported"
            source = f"Mentioned across {job_matches_count} verified job requisitions"
            context = job_context
        elif job_matches_count == 1:
            strength = "inferred"
            source = "Derived from 1 open job requisition"
            context = job_context
        elif unverified_match:
            strength = "inferred"
            source = "Derived from unverified third-party public mention / syndicated feed"
            context = unverified_context
        elif tag_match:
            strength = "inferred"
            source = "Derived from company profile technology tags"
            context = f"Company tagged with {name}"

        if strength in ("confirmed", "supported", "inferred"):
            results.append(
                {
                    "name": name,
                    "category": category,
                    "evidence_strength": strength,
                    "evidence_source": source,
                    "context": context,
                }
            )

    # Sort results: confirmed first, then supported, then inferred, then alphabetical
    priority_order = {"confirmed": 0, "supported": 1, "inferred": 2, "unknown": 3}
    results.sort(
        key=lambda x: (priority_order.get(x["evidence_strength"], 4), x["category"], x["name"])
    )

    return results
