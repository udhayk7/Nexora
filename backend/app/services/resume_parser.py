import io
import re
from typing import Any, Optional

from app.core.logging import logger

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
URL_REGEX = re.compile(
    r"(?:https?://[^\s]+|linkedin\.com/in/[\w-]+|github\.com/[\w-]+)",
    re.IGNORECASE,
)
DATE_RANGE_REGEX = re.compile(
    r"(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+)?\d{4}\s*(?:-|–|—|to)\s*(?:(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+)?\d{4}|present|current)",
    re.IGNORECASE,
)

SECTION_PATTERNS = {
    "summary": re.compile(
        r"^(?:professional\s+)?(?:summary|profile|about(?:\s+me)?|objective)\s*[:\-]?$",
        re.IGNORECASE,
    ),
    "experience": re.compile(
        r"^(?:work\s+|professional\s+)?(?:experience|employment|work\s+history|career\s+history)\s*[:\-]?$",
        re.IGNORECASE,
    ),
    "education": re.compile(
        r"^(?:education|academic\s+background|academic\s+credentials|qualifications)\s*[:\-]?$",
        re.IGNORECASE,
    ),
    "skills": re.compile(
        r"^(?:technical\s+|core\s+|key\s+)?(?:skills|competencies|technologies|tools|expertise)\s*[:\-]?$",
        re.IGNORECASE,
    ),
    "projects": re.compile(
        r"^(?:key\s+|personal\s+|technical\s+)?(?:projects|portfolio)\s*[:\-]?$",
        re.IGNORECASE,
    ),
    "certifications": re.compile(
        r"^(?:certifications?|certificates?|licenses?|credentials)\s*[:\-]?$",
        re.IGNORECASE,
    ),
}


class ResumeParserService:
    """Deterministic extractor and parser for resume documents."""

    def extract_text_from_pdf(self, content: bytes) -> str:
        """Extract plain text from PDF bytes."""
        try:
            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(content))
            pages_text: list[str] = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages_text.append(page_text)
            return "\n\n".join(pages_text)
        except Exception as exc:
            logger.warning(f"pypdf extraction failed: {exc}")
            raise ValueError(f"Unable to parse PDF content: {exc}") from exc

    def extract_text_from_docx(self, content: bytes) -> str:
        """Extract plain text from DOCX bytes."""
        try:
            import docx

            doc = docx.Document(io.BytesIO(content))
            lines: list[str] = []
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    lines.append(text)

            for table in doc.tables:
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_cells:
                        lines.append(" | ".join(row_cells))

            return "\n".join(lines)
        except Exception as exc:
            logger.warning(f"docx extraction failed: {exc}")
            raise ValueError(f"Unable to parse DOCX content: {exc}") from exc

    def extract_contact_info(self, text: str) -> dict[str, Any]:
        """Extract contact info (name, email, phone, links) deterministically."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        emails = EMAIL_REGEX.findall(text)
        email = emails[0] if emails else None

        phones = PHONE_REGEX.findall(text)
        phone = phones[0] if phones else None

        links = list(set(URL_REGEX.findall(text)))

        # Candidate name heuristic: inspect the first few lines
        candidate_name: Optional[str] = None
        for line in lines[:5]:
            # Skip lines with email or phone or URLs
            if EMAIL_REGEX.search(line) or PHONE_REGEX.search(line) or URL_REGEX.search(line):
                continue
            cleaned = re.sub(r"[^a-zA-Z\s\.\-]", "", line).strip()
            words = cleaned.split()
            # Most names are 2 to 4 words and under 40 characters
            if 2 <= len(words) <= 4 and len(cleaned) <= 40:
                candidate_name = cleaned
                break

        return {
            "name": candidate_name,
            "email": email,
            "phone": phone,
            "location": None,
            "links": links,
        }

    def partition_sections(self, text: str) -> dict[str, list[str]]:
        """Partition raw text into standard resume sections."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        sections: dict[str, list[str]] = {
            "header": [],
            "summary": [],
            "skills": [],
            "experience": [],
            "education": [],
            "projects": [],
            "certifications": [],
            "other": [],
        }

        current_section = "header"

        for line in lines:
            # Check if line matches a known section header
            matched_section = None
            for sec_name, pattern in SECTION_PATTERNS.items():
                if pattern.match(line):
                    matched_section = sec_name
                    break

            if matched_section:
                current_section = matched_section
            else:
                sections[current_section].append(line)

        return sections

    def parse_skills(self, skill_lines: list[str]) -> list[str]:
        """Parse skills from section lines into deduplicated tags."""
        skills: list[str] = []
        for line in skill_lines:
            # Clean category prefixes like "Programming Languages: Python, Go"
            if ":" in line:
                parts = line.split(":", 1)
                line = parts[1]

            # Split by comma, bullet, pipe, or semicolon
            tokens = re.split(r"[,•|;·\n]+", line)
            for token in tokens:
                cleaned = token.strip().rstrip(".")
                is_valid = cleaned and len(cleaned) <= 50 and not cleaned.startswith("http")
                if is_valid and cleaned not in skills:
                    skills.append(cleaned)
        return skills

    def parse_experience(self, exp_lines: list[str]) -> list[dict[str, Any]]:
        """Parse work experience lines into structured entries."""
        items: list[dict[str, Any]] = []
        current_entry: Optional[dict[str, Any]] = None

        for line in exp_lines:
            date_match = DATE_RANGE_REGEX.search(line)
            # A line with a date range likely indicates a role header
            if date_match:
                if current_entry:
                    items.append(current_entry)
                date_str = date_match.group(0).strip()
                title_company = line[: date_match.start()] + line[date_match.end() :]
                title_company = title_company.strip().strip("-|,")

                title = title_company
                company = None
                if " at " in title_company:
                    parts = title_company.split(" at ", 1)
                    title = parts[0].strip()
                    company = parts[1].strip()
                elif "|" in title_company:
                    parts = title_company.split("|", 1)
                    title = parts[0].strip()
                    company = parts[1].strip()
                elif " - " in title_company:
                    parts = title_company.split(" - ", 1)
                    title = parts[0].strip()
                    company = parts[1].strip()

                current_entry = {
                    "title": title or "Role",
                    "company": company,
                    "date_range": date_str,
                    "bullets": [],
                }
            elif current_entry is not None:
                # Add as bullet or detail
                cleaned_line = line.lstrip("•-* ").strip()
                if cleaned_line:
                    current_entry["bullets"].append(cleaned_line)
            else:
                # Pre-date text or loose entry
                if line:
                    current_entry = {
                        "title": line,
                        "company": None,
                        "date_range": None,
                        "bullets": [],
                    }

        if current_entry:
            items.append(current_entry)

        return items

    def parse_education(self, edu_lines: list[str]) -> list[dict[str, Any]]:
        """Parse education lines into structured degrees/institutions."""
        items: list[dict[str, Any]] = []
        degree_keywords = [
            "bachelor",
            "master",
            "phd",
            "doctorate",
            "associate",
            "b.s.",
            "b.a.",
            "m.s.",
            "m.a.",
            "btech",
            "mtech",
            "degree",
            "diploma",
        ]

        current_item: Optional[dict[str, Any]] = None

        for line in edu_lines:
            lower = line.lower()
            is_degree_line = any(kw in lower for kw in degree_keywords)
            date_match = re.search(r"\b(19\d\d|20\d\d)\b", line)

            if is_degree_line or (date_match and current_item is None):
                if current_item:
                    items.append(current_item)
                current_item = {
                    "institution": None,
                    "degree": line,
                    "year": date_match.group(0) if date_match else None,
                    "details": [],
                }
            elif current_item:
                if not current_item["institution"]:
                    current_item["institution"] = line
                else:
                    current_item["details"].append(line)
            else:
                current_item = {
                    "institution": line,
                    "degree": None,
                    "year": date_match.group(0) if date_match else None,
                    "details": [],
                }

        if current_item:
            items.append(current_item)

        return items

    def parse_document(
        self,
        content: bytes,
        file_type: str,
    ) -> tuple[str, dict[str, Any], str, Optional[str]]:
        """
        Extract text and parse structured data from PDF or DOCX bytes.

        Returns:
            (raw_text, parsed_content, parsing_status, error_summary)
        """
        docx_mime = "vnd.openxmlformats-officedocument.wordprocessingml.document"
        normalized_type = file_type.lower().strip(".").replace(docx_mime, "docx")

        raw_text = ""
        try:
            if "pdf" in normalized_type:
                raw_text = self.extract_text_from_pdf(content)
            elif "docx" in normalized_type or "word" in normalized_type:
                raw_text = self.extract_text_from_docx(content)
            else:
                return (
                    "",
                    {},
                    "failed",
                    f"Unsupported format '{file_type}'. Only PDF and DOCX files are supported.",
                )
        except Exception as exc:
            return (
                "",
                {},
                "failed",
                f"Failed to read file contents: {str(exc)[:100]}",
            )

        if not raw_text or not raw_text.strip():
            return (
                "",
                {},
                "failed",
                (
                    "No readable text found. If this is a scanned image, "
                    "please upload a text-based PDF or DOCX."
                ),
            )

        # Parse text into structured sections
        sections = self.partition_sections(raw_text)
        contact = self.extract_contact_info(raw_text)

        summary_text = " ".join(sections.get("summary", [])).strip() or None
        skills = self.parse_skills(sections.get("skills", []))
        experience = self.parse_experience(sections.get("experience", []))
        education = self.parse_education(sections.get("education", []))

        projects = [
            line.lstrip("•-* ").strip() for line in sections.get("projects", []) if line.strip()
        ]
        certifications = [
            line.lstrip("•-* ").strip()
            for line in sections.get("certifications", [])
            if line.strip()
        ]

        parsed_content = {
            "contact": contact,
            "summary": summary_text,
            "skills": skills,
            "experience": experience,
            "education": education,
            "projects": projects,
            "certifications": certifications,
        }

        return (raw_text, parsed_content, "parsed", None)


# Global parser service instance
resume_parser = ResumeParserService()
