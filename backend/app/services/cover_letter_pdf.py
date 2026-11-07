import io
import re
from datetime import datetime, timezone
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer


def compile_cover_letter_to_pdf(
    candidate_name: str,
    candidate_email: str,
    company_name: str,
    role_title: str,
    content: str,
    date_str: Optional[str] = None,
) -> tuple[bytes, int]:
    """Compile a professional, clean A4 PDF for a cover letter using ReportLab.

    Returns: (pdf_bytes, page_count)
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    header_name_style = ParagraphStyle(
        "CLHeaderName",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),  # slate-900
    )

    header_contact_style = ParagraphStyle(
        "CLHeaderContact",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),  # slate-600
    )

    date_style = ParagraphStyle(
        "CLDate",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
    )

    recipient_style = ParagraphStyle(
        "CLRecipient",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor("#1e293b"),
    )

    body_style = ParagraphStyle(
        "CLBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=12,
    )

    story = []

    # 1. Candidate Header
    story.append(Paragraph(candidate_name, header_name_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(candidate_email, header_contact_style))
    story.append(Spacer(1, 10))
    story.append(
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=colors.HexColor("#cbd5e1"),
            spaceBefore=0,
            spaceAfter=14,
        )
    )

    # 2. Date
    d_text = date_str or datetime.now(timezone.utc).strftime("%B %d, %Y")
    story.append(Paragraph(d_text, date_style))
    story.append(Spacer(1, 12))

    # 3. Recipient
    recip_text = f"Hiring Team<br/><b>{company_name}</b><br/>Re: Application for {role_title}"
    story.append(Paragraph(recip_text, recipient_style))
    story.append(Spacer(1, 16))

    # 4. Body Content (split by double newline or single newline paragraphs)
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]

    for para in paragraphs:
        # Sanitize HTML tags for ReportLab Paragraph
        safe_para = (
            para.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
        )
        story.append(Paragraph(safe_para, body_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    page_count = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes)) or 1
    return pdf_bytes, page_count

