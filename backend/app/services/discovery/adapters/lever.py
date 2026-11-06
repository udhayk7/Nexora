from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from app.services.discovery.adapters.base import BaseSourceAdapter, DiscoveredJob
from app.services.discovery.normalizer import JobNormalizer


class LeverAdapter(BaseSourceAdapter):
    """Source adapter for Lever public job postings API."""

    adapter_name = "lever"
    display_name = "Lever Job Postings"

    BASE_API_URL = "https://api.lever.co/v0/postings/{site}?mode=json"

    @classmethod
    def extract_site_name(cls, source_url: Optional[str], board_token: Optional[str]) -> str:
        """Extract or validate the Lever company site slug."""
        if board_token and board_token.strip():
            return board_token.strip().lower()

        if source_url and source_url.strip():
            url = source_url.strip()
            # Support URLs like https://jobs.lever.co/netflix or https://api.lever.co/v0/postings/netflix
            parsed = urlparse(url)
            path_segments = [s for s in parsed.path.split("/") if s]
            if "postings" in path_segments:
                idx = path_segments.index("postings")
                if idx + 1 < len(path_segments):
                    return path_segments[idx + 1].lower()
            if path_segments:
                return path_segments[0].lower()

        raise ValueError("Lever site name is required (e.g. 'netflix' or jobs.lever.co URL)")

    def fetch_jobs(
        self,
        source_url: Optional[str] = None,
        board_token: Optional[str] = None,
        **kwargs: Any,
    ) -> list[DiscoveredJob]:
        """Fetch all public job postings from Lever."""
        site = self.extract_site_name(source_url, board_token)
        api_url = self.BASE_API_URL.format(site=site)

        resp = self.safe_get(api_url)
        postings = resp.json()
        if not isinstance(postings, list):
            return []

        discovered: list[DiscoveredJob] = []

        for item in postings:
            raw_id = str(item.get("id"))
            title = (item.get("text") or "").strip()
            if not title:
                continue

            hosted_url = item.get("hostedUrl") or f"https://jobs.lever.co/{site}/{raw_id}"
            apply_url = item.get("applyUrl") or f"{hosted_url}/apply"

            # Combine description and lists (responsibilities, requirements)
            desc_parts: list[str] = []
            if item.get("descriptionPlain"):
                desc_parts.append(item["descriptionPlain"])
            elif item.get("description"):
                desc_parts.append(self.clean_html(item["description"]))

            for lst in item.get("lists", []):
                list_title = lst.get("text", "")
                list_content = self.clean_html(lst.get("content", ""))
                if list_title:
                    desc_parts.append(f"\n{list_title}:\n{list_content}")
                else:
                    desc_parts.append(list_content)

            if item.get("additionalPlain"):
                desc_parts.append(f"\n{item['additionalPlain']}")
            elif item.get("additional"):
                desc_parts.append(self.clean_html(item["additional"]))

            full_desc = "\n\n".join(desc_parts).strip()

            # Categories metadata
            cats = item.get("categories") or {}
            commitment = cats.get("commitment")
            location_text = cats.get("location")
            department = cats.get("department")

            # Publication timestamp
            published_at = None
            created_at_ms = item.get("createdAt")
            if created_at_ms:
                try:
                    published_at = datetime.fromtimestamp(created_at_ms / 1000.0, tz=timezone.utc)
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

            # Normalizer heuristics
            role_family = JobNormalizer.classify_role_family(title, full_desc)
            seniority, _ = JobNormalizer.classify_seniority(title, full_desc)
            work_arr = JobNormalizer.classify_work_arrangement(location_text or "", full_desc)
            emp_type = JobNormalizer.classify_employment_type(commitment, full_desc)
            skills = JobNormalizer.extract_skills(f"{title} {full_desc}")
            s_min, s_max, s_curr, s_per = JobNormalizer.parse_explicit_salary(full_desc)

            discovered.append(
                DiscoveredJob(
                    title=title,
                    job_url=hosted_url,
                    application_url=apply_url,
                    external_source_id=f"lever:{site}:{raw_id}",
                    description=full_desc,
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
                        "lever_site": site,
                        "lever_id": raw_id,
                        "department": department,
                        "team": cats.get("team"),
                    },
                )
            )

        return discovered

    def test_connection(
        self,
        source_url: Optional[str] = None,
        board_token: Optional[str] = None,
    ) -> tuple[bool, str, int]:
        """Test Lever site connectivity and count active postings."""
        try:
            site = self.extract_site_name(source_url, board_token)
            api_url = self.BASE_API_URL.format(site=site)
            resp = self.safe_get(api_url)
            data = resp.json()
            count = len(data) if isinstance(data, list) else 0
            return True, f"Successfully connected to Lever board '{site}'.", count
        except Exception as exc:
            return False, f"Lever connection failed: {exc}", 0
