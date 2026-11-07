"""
Portfolio Export Service.
Generates standalone static HTML portfolio packages and recruiter-ready PDF documents.
Uses ReportLab for PDF compilation and responsive embedded CSS for HTML export.
"""

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from app.models.portfolio import Portfolio


class PortfolioExportService:
    """Handles PDF and standalone static HTML compilation for candidate portfolios."""

    @classmethod
    def generate_html_export(cls, portfolio: Portfolio) -> str:
        """
        Generate a self-contained responsive HTML portfolio document.
        Does not require external dependencies or external CDNs.
        """
        profile = portfolio.profile_data or {}
        theme = portfolio.theme_config or {}
        accent_color = theme.get("accent_color", "#3B82F6")
        font_family = theme.get("font_family", "system")
        sans_stack = (
            "ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "
            "'Segoe UI', Roboto, sans-serif"
        )
        mono_stack = "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
        font_stack = sans_stack if font_family != "mono" else mono_stack

        full_name = profile.get("full_name") or "Candidate Portfolio"
        headline = profile.get("headline") or portfolio.headline or ""
        summary = profile.get("summary") or ""
        location = profile.get("location") or ""
        contact_email = profile.get("contact_email") or ""
        github_url = profile.get("github_url") or ""
        linkedin_url = profile.get("linkedin_url") or ""
        website_url = profile.get("website_url") or ""

        # Filter visible projects and visible sections
        visible_sections = {s.section_type: s for s in portfolio.sections if s.is_visible}
        visible_projects = [p for p in portfolio.projects if p.is_visible]

        skills_list = profile.get("technical_skills") or []
        experience_list = profile.get("work_experience") or []
        education_list = profile.get("education") or []

        # Skills HTML
        skills_html = "".join(f'<span class="skill-tag">{skill}</span>' for skill in skills_list)

        # Projects HTML
        projects_html = ""
        for p in visible_projects:
            tech_badges = "".join(
                f'<span class="tech-badge">{t}</span>' for t in (p.tech_stack or [])
            )
            features_html = ""
            if p.key_features:
                items = "".join(f"<li>{f}</li>" for f in p.key_features)
                features_html = f'<ul class="feature-list">{items}</ul>'

            links_html = ""
            if p.repository_url:
                links_html += (
                    f'<a href="{p.repository_url}" target="_blank" class="proj-link">'
                    f"Repository &rarr;</a> "
                )
            if p.live_demo_url:
                links_html += (
                    f'<a href="{p.live_demo_url}" target="_blank" class="proj-link">'
                    f"Live Demo &rarr;</a>"
                )

            arch_html = (
                f'<p class="proj-arch"><strong>Architecture:</strong> {p.architecture_overview}</p>'
                if p.architecture_overview
                else ""
            )
            outcomes_html = (
                f'<p class="proj-outcomes"><strong>Outcomes:</strong> {p.outcomes}</p>'
                if p.outcomes
                else ""
            )

            projects_html += f"""
            <div class="project-card">
              <div class="project-header">
                <h3 class="project-title">{p.title}</h3>
                <span class="status-badge status-{p.status}">{p.status}</span>
              </div>
              <p class="project-desc">{p.description}</p>
              {arch_html}
              {features_html}
              {outcomes_html}
              <div class="tech-stack-row">{tech_badges}</div>
              <div class="project-links">{links_html}</div>
            </div>
            """

        # Experience HTML
        experience_html = ""
        for exp in experience_list:
            dates = (
                f"{exp.get('start_date', '')} - "
                f"{'Present' if exp.get('is_current') else exp.get('end_date', '')}"
            )
            bullets = "".join(f"<li>{b}</li>" for b in exp.get("bullet_points", []))
            loc_span = (
                f"<span class='timeline-loc'> &bull; {exp.get('location')}</span>"
                if exp.get("location")
                else ""
            )
            desc_p = (
                f"<p class='timeline-desc'>{exp.get('description')}</p>"
                if exp.get("description")
                else ""
            )
            bullets_ul = f"<ul class='bullet-list'>{bullets}</ul>" if bullets else ""
            experience_html += f"""
            <div class="timeline-item">
              <div class="timeline-header">
                <div>
                  <h4 class="timeline-role">{exp.get("role", "")}</h4>
                  <span class="timeline-company">{exp.get("company", "")}</span>
                  {loc_span}
                </div>
                <span class="timeline-dates">{dates}</span>
              </div>
              {desc_p}
              {bullets_ul}
            </div>
            """

        # Education HTML
        education_html = ""
        for edu in education_list:
            years = (
                f"{edu.get('start_year', '')} - {edu.get('end_year', '')}"
                if edu.get("start_year") or edu.get("end_year")
                else ""
            )
            highlights = "".join(f"<li>{h}</li>" for h in edu.get("highlights", []))
            field_info = (
                f"<span> &bull; {edu.get('field_of_study')}</span>"
                if edu.get("field_of_study")
                else ""
            )
            education_html += f"""
            <div class="timeline-item">
              <div class="timeline-header">
                <div>
                  <h4 class="timeline-role">{edu.get("degree", "")}</h4>
                  <span class="timeline-company">{edu.get("institution", "")}</span>
                  {field_info}
                </div>
                <span class="timeline-dates">{years}</span>
              </div>
              {f"<ul class='bullet-list'>{highlights}</ul>" if highlights else ""}
            </div>
            """

        # Contact Links
        contact_items = []
        if contact_email:
            contact_items.append(f'<a href="mailto:{contact_email}" class="contact-pill">Email</a>')
        if github_url:
            contact_items.append(
                f'<a href="{github_url}" target="_blank" class="contact-pill">GitHub</a>'
            )
        if linkedin_url:
            contact_items.append(
                f'<a href="{linkedin_url}" target="_blank" class="contact-pill">LinkedIn</a>'
            )
        if website_url:
            contact_items.append(
                f'<a href="{website_url}" target="_blank" class="contact-pill">Website</a>'
            )
        contacts_html = " ".join(contact_items)

        # Assemble standalone HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{full_name} &mdash; Portfolio</title>
  <style>
    :root {{
      --primary: {accent_color};
      --bg: #0F172A;
      --card-bg: #1E293B;
      --card-border: #334155;
      --text-main: #F8FAFC;
      --text-muted: #94A3B8;
      --tag-bg: rgba(59, 130, 246, 0.12);
      --tag-text: #93C5FD;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: {font_stack};
      background: var(--bg);
      color: var(--text-main);
      line-height: 1.6;
      padding: 2rem 1rem;
    }}
    .container {{
      max-width: 900px;
      margin: 0 auto;
    }}
    header {{
      padding-bottom: 2rem;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 2.5rem;
    }}
    h1 {{ font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em; color: #FFFFFF; }}
    .headline {{ font-size: 1.1rem; color: var(--text-muted); margin-top: 0.5rem; }}
    .loc {{ font-size: 0.9rem; color: var(--text-muted); margin-top: 0.25rem; }}
    .contacts-row {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 1rem; }}
    .contact-pill {{
      display: inline-block;
      padding: 0.35rem 0.85rem;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      color: var(--text-main);
      text-decoration: none;
      border-radius: 9999px;
      font-size: 0.85rem;
      transition: all 0.2s;
    }}
    .contact-pill:hover {{ border-color: var(--primary); color: var(--primary); }}
    section {{ margin-bottom: 3rem; }}
    h2 {{
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--primary);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 1.25rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .summary-text {{
      font-size: 1rem;
      color: #E2E8F0;
      line-height: 1.7;
    }}
    .skills-grid {{ display: flex; flex-wrap: wrap; gap: 0.5rem; }}
    .skill-tag {{
      background: var(--tag-bg);
      color: var(--tag-text);
      padding: 0.35rem 0.75rem;
      border-radius: 0.375rem;
      font-size: 0.85rem;
      font-weight: 500;
      border: 1px solid rgba(59, 130, 246, 0.25);
    }}
    .project-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 0.75rem;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }}
    .project-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 0.75rem;
    }}
    .project-title {{ font-size: 1.15rem; font-weight: 700; color: #FFFFFF; }}
    .status-badge {{
      font-size: 0.7rem;
      text-transform: uppercase;
      padding: 0.2rem 0.5rem;
      border-radius: 9999px;
      font-weight: 700;
    }}
    .status-completed {{ background: rgba(16, 185, 129, 0.15); color: #34D399; }}
    .status-in_progress {{ background: rgba(59, 130, 246, 0.15); color: #60A5FA; }}
    .project-desc {{ font-size: 0.95rem; color: #CBD5E1; margin-bottom: 0.75rem; }}
    .proj-arch {{ font-size: 0.88rem; color: #94A3B8; margin-bottom: 0.5rem; }}
    .proj-outcomes {{ font-size: 0.88rem; color: #34D399; margin-bottom: 0.5rem; }}
    .feature-list {{
      margin-left: 1.25rem; font-size: 0.88rem; color: #94A3B8; margin-bottom: 0.75rem;
    }}
    .tech-stack-row {{ display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 1rem; }}
    .tech-badge {{
      font-size: 0.75rem;
      background: rgba(255, 255, 255, 0.06);
      padding: 0.2rem 0.5rem;
      border-radius: 0.25rem;
      color: #CBD5E1;
      font-family: monospace;
    }}
    .project-links {{
      margin-top: 1rem; padding-top: 0.75rem; border-top: 1px solid rgba(255, 255, 255, 0.08);
    }}
    .proj-link {{
      color: var(--primary); text-decoration: none; font-size: 0.9rem;
      font-weight: 600; margin-right: 1.25rem;
    }}
    .proj-link:hover {{ text-decoration: underline; }}
    .timeline-item {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 0.75rem;
      padding: 1.25rem;
      margin-bottom: 1rem;
    }}
    .timeline-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 0.5rem;
    }}
    .timeline-role {{ font-size: 1rem; font-weight: 700; color: #FFFFFF; }}
    .timeline-company {{ font-size: 0.9rem; color: var(--primary); font-weight: 600; }}
    .timeline-loc {{ font-size: 0.85rem; color: var(--text-muted); }}
    .timeline-dates {{ font-size: 0.82rem; color: var(--text-muted); font-family: monospace; }}
    .timeline-desc {{ font-size: 0.9rem; color: #CBD5E1; margin-top: 0.5rem; }}
    .bullet-list {{ margin-left: 1.25rem; font-size: 0.88rem; color: #94A3B8; margin-top: 0.5rem; }}
    footer {{
      margin-top: 4rem;
      padding-top: 2rem;
      border-top: 1px solid var(--card-border);
      text-align: center;
      font-size: 0.8rem;
      color: var(--text-muted);
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>{full_name}</h1>
      {f'<p class="headline">{headline}</p>' if headline else ""}
      {f'<p class="loc">{location}</p>' if location else ""}
      <div class="contacts-row">{contacts_html}</div>
    </header>

    {
            f"<section><h2>About</h2><p class='summary-text'>{summary}</p></section>"
            if summary and "about" in visible_sections
            else ""
        }

    {
            (
                f"<section><h2>Technical Skills</h2>"
                f"<div class='skills-grid'>{skills_html}</div></section>"
            )
            if skills_list and "skills" in visible_sections
            else ""
        }

    {
            f"<section><h2>Featured Projects</h2>{projects_html}</section>"
            if projects_html and "projects" in visible_sections
            else ""
        }

    {
            f"<section><h2>Work Experience</h2>{experience_html}</section>"
            if experience_html and "experience" in visible_sections
            else ""
        }

    {
            f"<section><h2>Education</h2>{education_html}</section>"
            if education_html and "education" in visible_sections
            else ""
        }

    <footer>
      <p>Exported from Nexora Portfolio Studio &bull; Recruiter-Ready Career Profile</p>
    </footer>
  </div>
</body>
</html>
"""
        return html

    @classmethod
    def generate_pdf_export(cls, portfolio: Portfolio) -> bytes:
        """
        Generate a professional recruiter-ready PDF document using ReportLab.
        Returns the raw PDF byte stream.
        """
        profile = portfolio.profile_data or {}
        full_name = profile.get("full_name") or "Candidate Portfolio"
        headline = profile.get("headline") or portfolio.headline or ""
        summary = profile.get("summary") or ""
        location = profile.get("location") or ""
        contact_email = profile.get("contact_email") or ""
        github_url = profile.get("github_url") or ""
        linkedin_url = profile.get("linkedin_url") or ""

        visible_sections = {s.section_type: s for s in portfolio.sections if s.is_visible}
        visible_projects = [p for p in portfolio.projects if p.is_visible]
        skills_list = profile.get("technical_skills") or []
        experience_list = profile.get("work_experience") or []
        education_list = profile.get("education") or []

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
        )

        styles = getSampleStyleSheet()

        # Custom typography styles
        name_style = ParagraphStyle(
            "NameStyle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=3,
        )
        headline_style = ParagraphStyle(
            "HeadlineStyle",
            parent=styles["Normal"],
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#475569"),
            spaceAfter=4,
        )
        contact_style = ParagraphStyle(
            "ContactStyle",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#2563EB"),
            spaceAfter=10,
        )
        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#1E3A8A"),
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True,
        )
        body_style = ParagraphStyle(
            "BodyStyle",
            parent=styles["Normal"],
            fontSize=9,
            leading=12.5,
            textColor=colors.HexColor("#1E293B"),
            spaceAfter=6,
        )
        sub_heading = ParagraphStyle(
            "SubHeading",
            parent=styles["Normal"],
            fontSize=10,
            leading=13,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#0F172A"),
        )
        meta_style = ParagraphStyle(
            "MetaStyle",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=11,
            fontName="Helvetica-Oblique",
            textColor=colors.HexColor("#64748B"),
        )

        story: list[Any] = []

        # 1. Header
        story.append(Paragraph(full_name, name_style))
        if headline:
            story.append(Paragraph(headline, headline_style))

        contact_parts = []
        if location:
            contact_parts.append(location)
        if contact_email:
            contact_parts.append(contact_email)
        if github_url:
            contact_parts.append(f"GitHub: {github_url}")
        if linkedin_url:
            contact_parts.append(f"LinkedIn: {linkedin_url}")

        if contact_parts:
            story.append(Paragraph(" &bull; ".join(contact_parts), contact_style))

        story.append(
            HRFlowable(
                width="100%",
                thickness=1,
                color=colors.HexColor("#CBD5E1"),
                spaceAfter=8,
            )
        )

        # 2. Professional Summary
        if summary and "about" in visible_sections:
            story.append(Paragraph("PROFESSIONAL SUMMARY", section_heading))
            story.append(Paragraph(summary, body_style))
            story.append(Spacer(1, 4))

        # 3. Technical Skills
        if skills_list and "skills" in visible_sections:
            story.append(Paragraph("TECHNICAL SKILLS", section_heading))
            skills_str = ", ".join(skills_list)
            story.append(Paragraph(skills_str, body_style))
            story.append(Spacer(1, 4))

        # 4. Featured Projects
        if visible_projects and "projects" in visible_sections:
            story.append(Paragraph("FEATURED PROJECTS", section_heading))
            for p in visible_projects:
                tech_str = f"[{', '.join(p.tech_stack)}]" if p.tech_stack else ""
                story.append(Paragraph(f"<b>{p.title}</b> &nbsp; {tech_str}", sub_heading))
                story.append(Paragraph(p.description, body_style))
                if p.architecture_overview:
                    story.append(
                        Paragraph(
                            f"<i>Architecture:</i> {p.architecture_overview}",
                            meta_style,
                        )
                    )
                if p.repository_url or p.live_demo_url:
                    links = []
                    if p.repository_url:
                        links.append(f"Code: {p.repository_url}")
                    if p.live_demo_url:
                        links.append(f"Demo: {p.live_demo_url}")
                    story.append(Paragraph(" | ".join(links), meta_style))
                story.append(Spacer(1, 4))

        # 5. Work Experience
        if experience_list and "experience" in visible_sections:
            story.append(Paragraph("WORK EXPERIENCE", section_heading))
            for exp in experience_list:
                dates = (
                    f"{exp.get('start_date', '')} - "
                    f"{'Present' if exp.get('is_current') else exp.get('end_date', '')}"
                )
                header_text = f"<b>{exp.get('role', '')}</b> &mdash; {exp.get('company', '')}"
                story.append(Paragraph(f"{header_text} &nbsp; ({dates})", sub_heading))
                if exp.get("description"):
                    story.append(Paragraph(exp.get("description"), body_style))
                for bullet in exp.get("bullet_points", []):
                    story.append(Paragraph(f"&bull; {bullet}", body_style))
                story.append(Spacer(1, 4))

        # 6. Education
        if education_list and "education" in visible_sections:
            story.append(Paragraph("EDUCATION", section_heading))
            for edu in education_list:
                years = (
                    f"({edu.get('start_year', '')} - {edu.get('end_year', '')})"
                    if edu.get("start_year") or edu.get("end_year")
                    else ""
                )
                edu_line = f"<b>{edu.get('degree', '')}</b>, {edu.get('institution', '')} {years}"
                story.append(Paragraph(edu_line, sub_heading))
                for hl in edu.get("highlights", []):
                    story.append(Paragraph(f"&bull; {hl}", body_style))
                story.append(Spacer(1, 4))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
