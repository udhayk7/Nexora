import io
import re
import shutil
import subprocess
import tempfile
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from app.core.errors import BadRequestError
from app.core.logging import logger

# Strictly forbidden LaTeX command tokens to prevent shell injection or arbitrary filesystem access
FORBIDDEN_LATEX_PATTERNS = [
    r"\\write18",
    r"\\immediate\s*\\write18",
    r"\\sys_exec",
    r"\\openin",
    r"\\openout",
    r"\\newwrite",
    r"\\directlua",
    r"\\input\{",
    r"\\include\{",
    r"\\catcode",
    r"\\csname",
    r"\\special",
]


def validate_latex_security(latex_content: str) -> None:
    """
    Validate LaTeX source against dangerous command execution primitives.
    Enforces strict zero-shell-escape sandbox constraints.
    """
    for pattern in FORBIDDEN_LATEX_PATTERNS:
        if re.search(pattern, latex_content, re.IGNORECASE):
            clean_token = pattern.replace(r"\\", "\\").replace(r"\{", "")
            raise BadRequestError(
                f"Security violation: Prohibited LaTeX directive '{clean_token}' "
                "is disabled in the secure sandbox."
            )


def compile_with_pdflatex(latex_content: str, timeout_seconds: int = 8) -> tuple[bytes, int]:
    """
    Execute sandboxed pdflatex in an isolated temporary directory.
    Enforces -no-shell-escape, halts on error, and isolates filesystem access.
    """
    pdflatex_path = shutil.which("pdflatex")
    if not pdflatex_path:
        raise RuntimeError("pdflatex binary is not available in the host environment.")

    validate_latex_security(latex_content)

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = f"{tmpdir}/document.tex"
        pdf_path = f"{tmpdir}/document.pdf"
        log_path = f"{tmpdir}/document.log"

        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_content)

        cmd = [
            pdflatex_path,
            "-no-shell-escape",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={tmpdir}",
            tex_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise BadRequestError(
                f"LaTeX compilation timed out after {timeout_seconds} seconds."
            ) from exc

        if result.returncode != 0:
            error_details = "Compilation failed."
            try:
                with open(log_path, encoding="utf-8", errors="ignore") as lf:
                    lines = lf.readlines()
                    error_lines = [ln.strip() for ln in lines if ln.startswith("!")]
                    if error_lines:
                        error_details = "\n".join(error_lines[:5])
                    else:
                        error_details = "\n".join(lines[-15:])
            except Exception:
                pass
            raise BadRequestError(f"LaTeX Compilation Error:\n{error_details}")

        try:
            with open(pdf_path, "rb") as pf:
                pdf_bytes = pf.read()
        except FileNotFoundError as exc:
            raise BadRequestError("pdflatex finished but no PDF output was produced.") from exc

        # Estimate page count from PDF binary
        page_count = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes)) or 1
        return pdf_bytes, page_count


def compile_with_reportlab(
    parsed_content: Optional[dict[str, Any]] = None,
    tailored_summary: Optional[str] = None,
    tailored_skills: Optional[list[str]] = None,
    tailored_experience: Optional[list[dict[str, Any]]] = None,
    tailored_projects: Optional[list[dict[str, Any]]] = None,
) -> tuple[bytes, int]:
    """
    High-fidelity PDF renderer using ReportLab to produce standard A4 resumes.
    Always available, deterministic, and 100% sandboxed (pure Python, zero shell invocation).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom Typography
    title_style = ParagraphStyle(
        "ResumeTitle",
        parent=styles["Normal"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        alignment=1,  # Center
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )

    contact_style = ParagraphStyle(
        "ResumeContact",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#475569"),
        alignment=1,
        spaceAfter=12,
    )

    section_heading = ParagraphStyle(
        "ResumeSectionHeading",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
        fontName="Helvetica-Bold",
        spaceBefore=8,
        spaceAfter=3,
        textTransform="uppercase",
    )

    body_style = ParagraphStyle(
        "ResumeBody",
        parent=styles["Normal"],
        fontSize=9,
        leading=12.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=4,
    )

    item_title_style = ParagraphStyle(
        "ResumeItemTitle",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#0f172a"),
        fontName="Helvetica-Bold",
    )

    bullet_style = ParagraphStyle(
        "ResumeBullet",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=2,
    )

    content = parsed_content or {}
    contact = content.get("contact") or {}

    name = contact.get("name") or "Candidate Name"
    email = contact.get("email") or ""
    phone = contact.get("phone") or ""
    location = contact.get("location") or ""
    links = contact.get("links") or []

    contact_bits = [b for b in [email, phone, location] + links[:2] if b]
    contact_line = " &bull; ".join(contact_bits)

    story: list[Any] = []

    # 1. Header
    story.append(Paragraph(f"<b>{name}</b>", title_style))
    if contact_line:
        story.append(Paragraph(contact_line, contact_style))

    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor("#cbd5e1"),
            spaceBefore=0,
            spaceAfter=8,
        )
    )

    # 2. Professional Summary
    summary = tailored_summary or content.get("summary")
    if summary:
        story.append(Paragraph("<b>Professional Summary</b>", section_heading))
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.5,
                color=colors.HexColor("#e2e8f0"),
                spaceBefore=1,
                spaceAfter=4,
            )
        )
        story.append(Paragraph(summary, body_style))
        story.append(Spacer(1, 4))

    # 3. Technical Skills
    skills = tailored_skills or content.get("skills") or []
    if skills:
        story.append(Paragraph("<b>Technical Skills</b>", section_heading))
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.5,
                color=colors.HexColor("#e2e8f0"),
                spaceBefore=1,
                spaceAfter=4,
            )
        )
        skills_text = f"<b>Core Competencies:</b> {', '.join(skills)}"
        story.append(Paragraph(skills_text, body_style))
        story.append(Spacer(1, 4))

    # 4. Experience
    experience = tailored_experience or content.get("experience") or []
    if experience:
        story.append(Paragraph("<b>Experience</b>", section_heading))
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.5,
                color=colors.HexColor("#e2e8f0"),
                spaceBefore=1,
                spaceAfter=4,
            )
        )
        for exp in experience:
            if isinstance(exp, dict):
                title = exp.get("title") or "Role"
                company = exp.get("company") or "Organization"
                dr = exp.get("date_range") or ""
                header_text = f"<b>{title}</b> &mdash; <i>{company}</i>"
                if dr:
                    header_text += f" <font color='#64748b' size='8'>({dr})</font>"
                story.append(Paragraph(header_text, item_title_style))

                for b in exp.get("bullets") or []:
                    story.append(Paragraph(f"&bull;&nbsp;&nbsp;{b}", bullet_style))
                story.append(Spacer(1, 3))
            elif isinstance(exp, str) and exp.strip():
                story.append(Paragraph(f"&bull;&nbsp;&nbsp;{exp}", bullet_style))
        story.append(Spacer(1, 4))

    # 5. Projects
    projects = tailored_projects or content.get("projects") or []
    if projects:
        story.append(Paragraph("<b>Projects</b>", section_heading))
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.5,
                color=colors.HexColor("#e2e8f0"),
                spaceBefore=1,
                spaceAfter=4,
            )
        )
        for proj in projects:
            if isinstance(proj, dict):
                p_title = proj.get("title") or "Project"
                story.append(Paragraph(f"<b>{p_title}</b>", item_title_style))
                for b in proj.get("bullets") or []:
                    story.append(Paragraph(f"&bull;&nbsp;&nbsp;{b}", bullet_style))
                story.append(Spacer(1, 3))
            elif isinstance(proj, str) and proj.strip():
                story.append(Paragraph(f"&bull;&nbsp;&nbsp;{proj}", bullet_style))
        story.append(Spacer(1, 4))

    # 6. Education
    education = content.get("education") or []
    if education:
        story.append(Paragraph("<b>Education</b>", section_heading))
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.5,
                color=colors.HexColor("#e2e8f0"),
                spaceBefore=1,
                spaceAfter=4,
            )
        )
        for edu in education:
            if isinstance(edu, dict):
                degree = edu.get("degree") or "Degree"
                inst = edu.get("institution") or "University"
                yr = edu.get("year") or ""
                edu_text = f"<b>{degree}</b> &mdash; <i>{inst}</i>"
                if yr:
                    edu_text += f" <font color='#64748b' size='8'>({yr})</font>"
                story.append(Paragraph(edu_text, item_title_style))
                for d in edu.get("details") or []:
                    story.append(Paragraph(f"&bull;&nbsp;&nbsp;{d}", bullet_style))
                story.append(Spacer(1, 2))
            elif isinstance(edu, str) and edu.strip():
                story.append(Paragraph(f"&bull;&nbsp;&nbsp;{edu}", bullet_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    page_count = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes)) or 1
    return pdf_bytes, page_count


def compile_resume_to_pdf(
    latex_content: Optional[str] = None,
    parsed_content: Optional[dict[str, Any]] = None,
    parsed_fallback: Optional[dict[str, Any]] = None,
    tailored_summary: Optional[str] = None,
    tailored_skills: Optional[list[str]] = None,
    tailored_experience: Optional[list[dict[str, Any]]] = None,
    tailored_projects: Optional[list[dict[str, Any]]] = None,
) -> tuple[bytes, int, str]:
    """
    Primary entry point for compiling a resume into a standard PDF.
    Attempts sandboxed pdflatex first if binary is installed and valid.
    Falls back to high-fidelity ReportLab standard A4 renderer.
    """
    effective_parsed = parsed_content or parsed_fallback
    if latex_content and shutil.which("pdflatex"):
        try:
            pdf_bytes, page_count = compile_with_pdflatex(latex_content)
            return pdf_bytes, page_count, "pdflatex"
        except Exception as e:
            logger.warning(
                "pdflatex compilation failed, falling back to structured layout renderer: %s",
                e,
            )

    # High-fidelity ReportLab renderer fallback
    pdf_bytes, page_count = compile_with_reportlab(
        parsed_content=effective_parsed,
        tailored_summary=tailored_summary,
        tailored_skills=tailored_skills,
        tailored_experience=tailored_experience,
        tailored_projects=tailored_projects,
    )
    return pdf_bytes, page_count, "structured_layout_renderer"
