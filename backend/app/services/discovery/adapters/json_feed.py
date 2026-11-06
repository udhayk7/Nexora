from datetime import datetime, timezone
from typing import Any, Optional

from app.services.discovery.adapters.base import BaseSourceAdapter, DiscoveredJob
from app.services.discovery.normalizer import JobNormalizer


class JSONFeedAdapter(BaseSourceAdapter):
    """Source adapter for permitted custom JSON job feeds and career APIs."""

    adapter_name = "json_feed"
    display_name = "Custom JSON Job Feed"

    def fetch_jobs(
        self,
        source_url: Optional[str] = None,
        board_token: Optional[str] = None,
        **kwargs: Any,
    ) -> list[DiscoveredJob]:
        """Fetch and normalize jobs from a JSON feed endpoint."""
        url = (source_url or board_token or "").strip()
        if not url:
            raise ValueError("Endpoint URL is required for JSON Feed adapter")

        resp = self.safe_get(url)
        data = resp.json()

        # Find the jobs list
        items: list[dict[str, Any]] = []
        if isinstance(data, list):
            items = [i for i in data if isinstance(i, dict)]
        elif isinstance(data, dict):
            for key in ["jobs", "postings", "items", "data", "listings", "positions"]:
                if key in data and isinstance(data[key], list):
                    items = [i for i in data[key] if isinstance(i, dict)]
                    break

        discovered: list[DiscoveredJob] = []

        for idx, item in enumerate(items):
            # Title
            title = (
                item.get("title")
                or item.get("job_title")
                or item.get("name")
                or item.get("position")
                or ""
            ).strip()
            if not title:
                continue

            # URL
            job_url = (
                item.get("job_url")
                or item.get("url")
                or item.get("link")
                or item.get("apply_url")
                or url
            ).strip()
            app_url = item.get("application_url") or item.get("apply_url") or job_url

            # ID
            raw_id = str(item.get("id") or item.get("job_id") or item.get("external_id") or idx)

            # Description
            raw_desc = (
                item.get("description")
                or item.get("content")
                or item.get("summary")
                or item.get("details")
                or ""
            )
            clean_desc = self.clean_html(str(raw_desc))

            # Location
            loc_val = item.get("location") or item.get("location_name") or item.get("city")
            location_text = None
            if isinstance(loc_val, dict):
                location_text = loc_val.get("name") or loc_val.get("city")
            elif isinstance(loc_val, str):
                location_text = loc_val

            city = item.get("city")
            country = item.get("country")
            if not city and location_text:
                parts = [p.strip() for p in location_text.split(",") if p.strip()]
                if len(parts) >= 2:
                    city = parts[0]
                    country = parts[-1]
                elif len(parts) == 1:
                    city = parts[0]

            # Timestamp
            published_at = None
            for date_key in ["published_at", "posted_at", "created_at", "date", "updated_at"]:
                if date_key in item and item[date_key]:
                    try:
                        d_str = str(item[date_key])
                        published_at = datetime.fromisoformat(d_str.replace("Z", "+00:00"))
                        break
                    except Exception:
                        pass
            if not published_at:
                published_at = datetime.now(timezone.utc)

            # Classifications via Normalizer
            role_family = item.get("role_family") or JobNormalizer.classify_role_family(
                title, clean_desc
            )
            seniority = item.get("seniority_level")
            if not seniority:
                seniority, _ = JobNormalizer.classify_seniority(title, clean_desc)
            work_arr = item.get("work_arrangement") or JobNormalizer.classify_work_arrangement(
                location_text or "", clean_desc
            )
            emp_type = item.get("employment_type") or JobNormalizer.classify_employment_type(
                text=clean_desc
            )
            skills = item.get("skills_tags") or JobNormalizer.extract_skills(
                f"{title} {clean_desc}"
            )

            s_min = item.get("salary_min")
            s_max = item.get("salary_max")
            s_curr = item.get("salary_currency")
            s_per = item.get("salary_period")
            if s_min is None and s_max is None:
                s_min, s_max, s_curr, s_per = JobNormalizer.parse_explicit_salary(clean_desc)

            discovered.append(
                DiscoveredJob(
                    title=title,
                    job_url=job_url,
                    application_url=app_url,
                    external_source_id=f"json:{raw_id}",
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
                    raw_metadata={"adapter": self.adapter_name, "raw_id": raw_id},
                )
            )

        return discovered

    def test_connection(
        self,
        source_url: Optional[str] = None,
        board_token: Optional[str] = None,
    ) -> tuple[bool, str, int]:
        """Test JSON feed connectivity and count available items."""
        try:
            url = (source_url or board_token or "").strip()
            if not url:
                return False, "Feed URL is required.", 0
            jobs = self.fetch_jobs(source_url=url)
            return True, f"Successfully parsed JSON feed ({len(jobs)} items found).", len(jobs)
        except Exception as exc:
            return False, f"JSON feed connection failed: {exc}", 0
