import re
from typing import Any, Optional


def escape_latex(text: Optional[str]) -> str:
    """Escape special LaTeX characters to prevent syntax breakages or injection."""
    if not text:
        return ""

    # Replace backslash first
    s = str(text).replace("\\", "\\textbackslash{}")
    # Replace other special characters
    replacements = [
        ("&", "\\&"),
        ("%", "\\%"),
        ("$", "\\$"),
        ("#", "\\#"),
        ("_", "\\_"),
        ("{", "\\{"),
        ("}", "\\}"),
        ("~", "\\textasciitilde{}"),
        ("^", "\\textasciicircum{}"),
    ]
    for char, rep in replacements:
        s = s.replace(char, rep)

    # Clean redundant whitespaces
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def generate_latex_resume(
    parsed_content: Optional[dict[str, Any]] = None,
    tailored_summary: Optional[str] = None,
    tailored_skills: Optional[list[str]] = None,
    tailored_experience: Optional[list[dict[str, Any]]] = None,
    tailored_projects: Optional[list[dict[str, Any]]] = None,
    job_title: Optional[str] = None,
    company_name: Optional[str] = None,
) -> str:
    """
    Generate professional, modern A4 LaTeX resume source.
    Preserves document structure and escapes all dynamic fields.
    """
    content = parsed_content or {}
    contact = content.get("contact") or {}

    name = escape_latex(contact.get("name") or "Candidate Name")
    email = escape_latex(contact.get("email") or "")
    phone = escape_latex(contact.get("phone") or "")
    location = escape_latex(contact.get("location") or "")
    links = [escape_latex(link) for link in (contact.get("links") or []) if link]

    summary = escape_latex(tailored_summary or content.get("summary") or "")
    job_sub = ""
    if job_title:
        escaped_title = escape_latex(job_title)
        if company_name:
            job_sub = f"{escaped_title} --- {escape_latex(company_name)}"
        else:
            job_sub = escaped_title

    # Skills
    skills_list = tailored_skills or content.get("skills") or []
    escaped_skills = [escape_latex(s) for s in skills_list if s]

    # Experience
    experience_list = tailored_experience or content.get("experience") or []

    # Projects
    projects_list = tailored_projects or content.get("projects") or []

    # Education
    education_list = content.get("education") or []

    # Build Header Links Line
    contact_parts: list[str] = []
    if email:
        contact_parts.append(f"\\href{{mailto:{email}}}{{{email}}}")
    if phone:
        contact_parts.append(phone)
    if location:
        contact_parts.append(location)
    for lk in links[:2]:
        contact_parts.append(f"\\href{{{lk}}}{{{lk}}}")
    contact_line = " $\\vert$ ".join(contact_parts) if contact_parts else ""

    latex = [
        r"%--------------------------------------------------------------------------------",
        r"% Nexora Professional Tailored Resume Template (A4 Standard)",
        r"%--------------------------------------------------------------------------------",
        r"\documentclass[a4paper,10pt]{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[margin=0.75in]{geometry}",
        r"\usepackage{hyperref}",
        r"\usepackage{enumitem}",
        r"\usepackage{titlesec}",
        r"\usepackage{color}",
        r"",
        r"% Hyperlink setup",
        r"\hypersetup{colorlinks=true, linkcolor=blue, urlcolor=blue}",
        r"",
        r"% Section title formatting",
        r"\titleformat{\section}{\large\bfseries\uppercase}{}{0em}{}[\titlerule]",
        r"\titlespacing*{\section}{0pt}{1.0ex}{0.8ex}",
        r"",
        r"% List formatting",
        r"\setlist[itemize]{noitemsep, topsep=0pt, leftmargin=1.5em}",
        r"",
        r"\begin{document}",
        r"\pagestyle{empty}",
        r"",
        r"% Header",
        r"\begin{center}",
        f"    {{\\LARGE \\textbf{{{name}}}}} \\\\[0.4em]",
        f"    {{\\small {contact_line}}} \\\\[0.2em]" if contact_line else "",
        f"    {{\\footnotesize \\textit{{{job_sub}}}}} \\\\[0.2em]" if job_sub else "",
        r"\end{center}",
        r"\vspace{0.5em}",
    ]

    # Professional Summary Section
    if summary:
        latex.extend([
            r"\section{Professional Summary}",
            f"{summary}\\\\",
            r"",
        ])

    # Technical Skills Section
    if escaped_skills:
        skills_str = ", ".join(escaped_skills)
        latex.extend([
            r"\section{Technical Skills}",
            r"\begin{itemize}",
            f"    \\item \\textbf{{Core Competencies:}} {skills_str}",
            r"\end{itemize}",
            r"",
        ])

    # Experience Section
    if experience_list:
        latex.extend([r"\section{Experience}"])
        for exp in experience_list:
            if isinstance(exp, dict):
                title = escape_latex(exp.get("title") or "Role")
                company = escape_latex(exp.get("company") or "Organization")
                date_range = escape_latex(exp.get("date_range") or "")
                bullets = exp.get("bullets") or []

                header_line = (
                    f"\\textbf{{{title}}} -- \\textit{{{company}}} "
                    f"\\hfill {{\\small {date_range}}}\\\\"
                )
                latex.extend([
                    r"\noindent",
                    header_line,
                ])
                if bullets:
                    latex.append(r"\begin{itemize}")
                    for b in bullets:
                        latex.append(f"    \\item {escape_latex(str(b))}")
                    latex.append(r"\end{itemize}")
                latex.append(r"\vspace{0.4em}")
            elif isinstance(exp, str) and exp.strip():
                latex.extend([
                    r"\begin{itemize}",
                    f"    \\item {escape_latex(exp)}",
                    r"\end{itemize}",
                ])
        latex.append("")

    # Projects Section
    if projects_list:
        latex.extend([r"\section{Projects}"])
        for proj in projects_list:
            if isinstance(proj, dict):
                p_title = escape_latex(proj.get("title") or "Project")
                p_bullets = proj.get("bullets") or []
                latex.extend([
                    r"\noindent",
                    f"\\textbf{{{p_title}}}\\\\",
                ])
                if p_bullets:
                    latex.append(r"\begin{itemize}")
                    for b in p_bullets:
                        latex.append(f"    \\item {escape_latex(str(b))}")
                    latex.append(r"\end{itemize}")
                latex.append(r"\vspace{0.4em}")
            elif isinstance(proj, str) and proj.strip():
                latex.extend([
                    r"\begin{itemize}",
                    f"    \\item {escape_latex(proj)}",
                    r"\end{itemize}",
                ])
        latex.append("")

    # Education Section
    if education_list:
        latex.extend([r"\section{Education}"])
        for edu in education_list:
            if isinstance(edu, dict):
                inst = escape_latex(edu.get("institution") or "")
                degree = escape_latex(edu.get("degree") or "")
                year = escape_latex(edu.get("year") or "")
                details = edu.get("details") or []

                latex.extend([
                    r"\noindent",
                    f"\\textbf{{{degree}}} -- \\textit{{{inst}}} \\hfill {{\\small {year}}}\\\\",
                ])
                if details:
                    latex.append(r"\begin{itemize}")
                    for d in details:
                        latex.append(f"    \\item {escape_latex(str(d))}")
                    latex.append(r"\end{itemize}")
                latex.append(r"\vspace{0.4em}")
            elif isinstance(edu, str) and edu.strip():
                latex.extend([
                    r"\begin{itemize}",
                    f"    \\item {escape_latex(edu)}",
                    r"\end{itemize}",
                ])
        latex.append("")

    latex.extend([
        r"\end{document}",
        "",
    ])

    return "\n".join(latex)
