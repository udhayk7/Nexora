import email.utils
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.discovery.adapters.base import BaseSourceAdapter, DiscoveredJob
from app.services.discovery.normalizer import JobNormalizer


class RSSFeedAdapter(BaseSourceAdapter):
    """Source adapter for permitted public RSS 2.0 and Atom XML career feeds."""

    adapter_name = "rss_feed"
    display_name = "RSS / Atom Job Feed"

    def fetch_jobs(
        self,
        source_url: Optional[str] = None,
        board_token: Optional[str] = None,
        **kwargs: Any,
    ) -> list[DiscoveredJob]:
        """Fetch and parse jobs from an RSS or Atom XML feed."""
        url = (source_url or board_token or "").strip()
        if not url:
            raise ValueError("Feed URL is required for RSS adapter")

        resp = self.safe_get(url)
        content = resp.content

        try:
            # Parse XML tree
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            raise ValueError(f"Malformed XML response from feed: {exc}") from exc

        discovered: list[DiscoveredJob] = []

        # 1. RSS 2.0 channel -> item
        channel = root.find("channel")
        if channel is not None:
            items = channel.findall("item")
            for idx, item in enumerate(items):
                title_elem = item.find("title")
                title = (
                    title_elem.text if title_elem is not None and title_elem.text else ""
                ).strip()
                if not title:
                    continue

                link_elem = item.find("link")
                link = (link_elem.text if link_elem is not None and link_elem.text else "").strip()
                if not link:
                    link = url

                desc_elem = item.find("description")
                raw_desc = desc_elem.text if desc_elem is not None and desc_elem.text else ""
                clean_desc = self.clean_html(raw_desc)

                guid_elem = item.find("guid")
                guid = (
                    guid_elem.text if guid_elem is not None and guid_elem.text else f"item-{idx}"
                ).strip()

                pub_elem = item.find("pubDate")
                pub_date = None
                if pub_elem is not None and pub_elem.text:
                    try:
                        parsed_tuple = email.utils.parsedate_to_datetime(pub_elem.text)
                        if parsed_tuple:
                            pub_date = parsed_tuple.astimezone(timezone.utc)
                    except Exception:
                        pub_date = datetime.now(timezone.utc)

                role_family = JobNormalizer.classify_role_family(title, clean_desc)
                seniority, _ = JobNormalizer.classify_seniority(title, clean_desc)
                work_arr = JobNormalizer.classify_work_arrangement("", clean_desc)
                emp_type = JobNormalizer.classify_employment_type(text=clean_desc)
                skills = JobNormalizer.extract_skills(f"{title} {clean_desc}")
                s_min, s_max, s_curr, s_per = JobNormalizer.parse_explicit_salary(clean_desc)

                discovered.append(
                    DiscoveredJob(
                        title=title,
                        job_url=link,
                        application_url=link,
                        external_source_id=f"rss:{guid}",
                        description=clean_desc,
                        employment_type=emp_type,
                        seniority_level=seniority,
                        work_arrangement=work_arr,
                        skills_tags=skills,
                        role_family=role_family,
                        salary_min=s_min,
                        salary_max=s_max,
                        salary_currency=s_curr,
                        salary_period=s_per,
                        source_published_at=pub_date,
                        raw_metadata={"adapter": self.adapter_name, "guid": guid},
                    )
                )

        # 2. Atom feed -> entry (namespace agnostic)
        entries = root.findall("{http://www.w3.org/2005/Atom}entry") or root.findall("entry")
        for idx, entry in enumerate(entries):
            title_node = entry.find("{http://www.w3.org/2005/Atom}title") or entry.find("title")
            title = (title_node.text if title_node is not None and title_node.text else "").strip()
            if not title:
                continue

            link_node = entry.find("{http://www.w3.org/2005/Atom}link") or entry.find("link")
            link = url
            if link_node is not None:
                link = link_node.attrib.get("href") or (link_node.text or url)

            summary_node = (
                entry.find("{http://www.w3.org/2005/Atom}content")
                or entry.find("{http://www.w3.org/2005/Atom}summary")
                or entry.find("content")
                or entry.find("summary")
            )
            raw_desc = summary_node.text if summary_node is not None and summary_node.text else ""
            clean_desc = self.clean_html(raw_desc)

            id_node = entry.find("{http://www.w3.org/2005/Atom}id") or entry.find("id")
            entry_id = (
                id_node.text if id_node is not None and id_node.text else f"entry-{idx}"
            ).strip()

            role_family = JobNormalizer.classify_role_family(title, clean_desc)
            seniority, _ = JobNormalizer.classify_seniority(title, clean_desc)
            work_arr = JobNormalizer.classify_work_arrangement("", clean_desc)
            emp_type = JobNormalizer.classify_employment_type(text=clean_desc)
            skills = JobNormalizer.extract_skills(f"{title} {clean_desc}")
            s_min, s_max, s_curr, s_per = JobNormalizer.parse_explicit_salary(clean_desc)

            discovered.append(
                DiscoveredJob(
                    title=title,
                    job_url=link,
                    application_url=link,
                    external_source_id=f"atom:{entry_id}",
                    description=clean_desc,
                    employment_type=emp_type,
                    seniority_level=seniority,
                    work_arrangement=work_arr,
                    skills_tags=skills,
                    role_family=role_family,
                    salary_min=s_min,
                    salary_max=s_max,
                    salary_currency=s_curr,
                    salary_period=s_per,
                    source_published_at=datetime.now(timezone.utc),
                    raw_metadata={"adapter": self.adapter_name, "entry_id": entry_id},
                )
            )

        return discovered

    def test_connection(
        self,
        source_url: Optional[str] = None,
        board_token: Optional[str] = None,
    ) -> tuple[bool, str, int]:
        """Test RSS/Atom feed connectivity and count available items."""
        try:
            url = (source_url or board_token or "").strip()
            if not url:
                return False, "Feed URL is required.", 0
            jobs = self.fetch_jobs(source_url=url)
            return True, f"Successfully parsed RSS feed ({len(jobs)} items found).", len(jobs)
        except Exception as exc:
            return False, f"RSS feed connection failed: {exc}", 0
