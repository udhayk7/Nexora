from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from app.services.discovery.adapters.base import BaseSourceAdapter, DiscoveredJob
from app.services.discovery.normalizer import JobNormalizer


class AshbyAdapter(BaseSourceAdapter):
    """Source adapter for Ashby public job board API."""

    adapter_name = "ashby"
    display_name = "Ashby Job Board"

    BASE_API_URL = "https://api.ashbyhq.com/posting-api/job-board/{board_name}"

    @classmethod
    def extract_board_name(cls, source_url: Optional[str], board_token: Optional[str]) -> str:
        """Extract or validate the Ashby job board name/slug."""
        if board_token and board_token.strip():
            return board_token.strip().lower()

        if source_url and source_url.strip():
            url = source_url.strip()
            # Support URLs like https://jobs.ashbyhq.com/linear or https://api.ashbyhq.com/posting-api/job-board/linear
            parsed = urlparse(url)
            path_segments = [s for s in parsed.path.split("/") if s]
            if "job-board" in path_segments:
                idx = path_segments.index("job-board")
                if idx + 1 < len(path_segments):
                    return path_segments[idx + 1].lower()
            if path_segments:
                return path_segments[0].lower()

        raise ValueError("Ashby board name is required (e.g. 'linear' or jobs.ashbyhq.com URL)")

    def fetch_jobs(
        self,
        source_url: Optional[str] = None,
        board_token: Optional[str] = None,
        **kwargs: Any,
    ) -> list[DiscoveredJob]:
        """Fetch all public job postings from Ashby."""
        board_name = self.extract_board_name(source_url, board_token)
        api_url = self.BASE_API_URL.format(board_name=board_name)

        resp = self.safe_get(api_url)
        data = resp.json()
        jobs_list = data.get("jobs", []) if isinstance(data, dict) else []

        discovered: list[DiscoveredJob] = []

        for item in jobs_list:
            raw_id = str(item.get("id"))
            title = (item.get("title") or "").strip()
            if not title:
                continue

            job_url = item.get("jobUrl") or f"https://jobs.ashbyhq.com/{board_name}/{raw_id}"
            apply_url = item.get("applyUrl") or f"{job_url}/application"

            # Plain text description
            clean_desc = item.get("descriptionPlain")
            if not clean_desc and item.get("descriptionHtml"):
                clean_desc = self.clean_html(item["descriptionHtml"])
            clean_desc = (clean_desc or "").strip()

            location_text = item.get("location")
            department = item.get("department")
            employment_type = item.get("employmentType")
            is_remote = bool(item.get("isRemote"))

            # Published date
            published_at = None
            pub_str = item.get("publishedAt")
            if pub_str:
                try:
                    published_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                except Exception:
                    published_at = datetime.now(timezone.utc)

            # Location parsing
            city = None
            country = None
            if location_text:
                parts = [p.strip() for p in location_text.split(",") if p.strip()]
                if len(parts) >= 2:
                    city = parts[0]
                    country = parts[-1]
                elif len(parts) == 1:
                    city = parts[0]

            # Work arrangement
            if is_remote:
                work_arr = "remote"
            else:
                work_arr = JobNormalizer.classify_work_arrangement(location_text or "", clean_desc)

            # Normalizer heuristics
            role_family = JobNormalizer.classify_role_family(title, clean_desc)
            seniority, _ = JobNormalizer.classify_seniority(title, clean_desc)
            emp_type = JobNormalizer.classify_employment_type(employment_type, clean_desc)
            skills = JobNormalizer.extract_skills(f"{title} {clean_desc}")

            # Salary parsing
            comp_info = item.get("compensation") or {}
            comp_tier = comp_info.get("compensationTierSummary") or ""
            s_min, s_max, s_curr, s_per = JobNormalizer.parse_explicit_salary(
                f"{comp_tier} {clean_desc}"
            )

            discovered.append(
                DiscoveredJob(
                    title=title,
                    job_url=job_url,
                    application_url=apply_url,
                    external_source_id=f"ashby:{board_name}:{raw_id}",
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
                        "ashby_board": board_name,
                        "ashby_id": raw_id,
                        "department": department,
                        "compensation": comp_info,
                    },
                )
            )

        return discovered

    def test_connection(
        self,
        source_url: Optional[str] = None,
        board_token: Optional[str] = None,
    ) -> tuple[bool, str, int]:
        """Test Ashby board connectivity and count open opportunities."""
        try:
            board_name = self.extract_board_name(source_url, board_token)
            api_url = self.BASE_API_URL.format(board_name=board_name)
            resp = self.safe_get(api_url)
            data = resp.json()
            jobs_count = len(data.get("jobs", [])) if isinstance(data, dict) else 0
            return True, f"Successfully connected to Ashby board '{board_name}'.", jobs_count
        except Exception as exc:
            return False, f"Ashby connection failed: {exc}", 0
