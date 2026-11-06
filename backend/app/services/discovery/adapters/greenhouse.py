from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from app.services.discovery.adapters.base import BaseSourceAdapter, DiscoveredJob
from app.services.discovery.normalizer import JobNormalizer


class GreenhouseAdapter(BaseSourceAdapter):
    """Source adapter for Greenhouse public job boards API."""

    adapter_name = "greenhouse"
    display_name = "Greenhouse Job Board"

    BASE_API_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"

    @classmethod
    def extract_board_token(cls, source_url: Optional[str], board_token: Optional[str]) -> str:
        """Extract or validate the Greenhouse board token/slug."""
        if board_token and board_token.strip():
            return board_token.strip().lower()

        if source_url and source_url.strip():
            url = source_url.strip()
            # Support URLs like https://boards.greenhouse.io/stripe or https://boards-api.greenhouse.io/v1/boards/stripe
            parsed = urlparse(url)
            path_segments = [s for s in parsed.path.split("/") if s]
            if "boards" in path_segments:
                idx = path_segments.index("boards")
                if idx + 1 < len(path_segments):
                    token = path_segments[idx + 1]
                    if token != "v1":
                        return token.lower()
            if path_segments:
                return path_segments[0].lower()

        raise ValueError("Greenhouse board token is required (e.g. 'stripe' or board URL)")

    def fetch_jobs(
        self,
        source_url: Optional[str] = None,
        board_token: Optional[str] = None,
        **kwargs: Any,
    ) -> list[DiscoveredJob]:
        """Fetch all public job postings with full description content from Greenhouse."""
        token = self.extract_board_token(source_url, board_token)
        api_url = self.BASE_API_URL.format(token=token)

        # content=true includes full HTML descriptions for all jobs
        resp = self.safe_get(api_url, params={"content": "true"})
        data = resp.json()

        jobs_list = data.get("jobs", [])
        discovered: list[DiscoveredJob] = []

        for item in jobs_list:
            raw_id = str(item.get("id"))
            title = (item.get("title") or "").strip()
            if not title:
                continue

            absolute_url = (
                item.get("absolute_url") or f"https://boards.greenhouse.io/{token}/jobs/{raw_id}"
            )
            raw_html = item.get("content") or ""
            clean_desc = self.clean_html(raw_html)

            # Location extraction
            loc_data = item.get("location") or {}
            location_text = loc_data.get("name") or None
            city = None
            country = None
            if location_text:
                parts = [p.strip() for p in location_text.split(",") if p.strip()]
                if len(parts) >= 2:
                    city = parts[0]
                    country = parts[-1]
                elif len(parts) == 1:
                    city = parts[0]

            # Date parsing
            published_at = None
            updated_str = item.get("updated_at")
            if updated_str:
                try:
                    published_at = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
                except Exception:
                    published_at = datetime.now(timezone.utc)

            # Classifications via Normalizer
            role_family = JobNormalizer.classify_role_family(title, clean_desc)
            seniority, _ = JobNormalizer.classify_seniority(title, clean_desc)
            work_arr = JobNormalizer.classify_work_arrangement(location_text or "", clean_desc)
            emp_type = JobNormalizer.classify_employment_type(text=clean_desc)
            skills = JobNormalizer.extract_skills(f"{title} {clean_desc}")
            s_min, s_max, s_curr, s_per = JobNormalizer.parse_explicit_salary(clean_desc)

            discovered.append(
                DiscoveredJob(
                    title=title,
                    job_url=absolute_url,
                    application_url=f"{absolute_url}#app",
                    external_source_id=f"greenhouse:{token}:{raw_id}",
                    description=clean_desc,
                    employment_type=emp_type,
                    seniority_level=seniority,
                    work_arrangement=work_arr,
                    location_text=location_text,
                    city=city,
                    country=country,
                    skills_tags=skills,
                    role_family=role_family,
                    salary_min=s_min,
                    salary_max=s_max,
                    salary_currency=s_curr,
                    salary_period=s_per,
                    source_published_at=published_at,
                    raw_metadata={
                        "adapter": self.adapter_name,
                        "board_token": token,
                        "greenhouse_id": raw_id,
                        "departments": item.get("departments", []),
                        "offices": item.get("offices", []),
                    },
                )
            )

        return discovered

    def test_connection(
        self,
        source_url: Optional[str] = None,
        board_token: Optional[str] = None,
    ) -> tuple[bool, str, int]:
        """Test Greenhouse board connectivity and count available opportunities."""
        try:
            token = self.extract_board_token(source_url, board_token)
            api_url = self.BASE_API_URL.format(token=token)
            resp = self.safe_get(api_url)
            data = resp.json()
            jobs_count = len(data.get("jobs", []))
            return True, f"Successfully connected to Greenhouse board '{token}'.", jobs_count
        except Exception as exc:
            return False, f"Greenhouse connection failed: {exc}", 0
