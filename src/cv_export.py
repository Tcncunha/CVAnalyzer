"""
CV export utilities — ATS-friendly DOCX and PDF generation.

Single-column layout, no tables, no images. Designed for maximum
compatibility with Applicant Tracking Systems.
"""

import os
import sys
from io import BytesIO

from cv_utils import ensure_cv_structure

# Characters commonly produced by resumes/CVs that live outside latin-1
# (the encoding used by fpdf2 core fonts). Mapped to ATS-safe ASCII equals.
_PDF_ASCII_MAP = {
    "\u2014": "-", "\u2013": "-", "\u2010": "-", "\u2043": "-",
    "\u2022": "-", "\u2219": "-", "\u00b7": "-",
    "\u2026": "...",
    "\u201c": '"', "\u201d": '"', "\u00ab": '"', "\u00bb": '"',
    "\u2018": "'", "\u2019": "'", "\u00b4": "'",
    "\u00a0": " ", "\u2009": " ", "\u202f": " ", "\t": " ",
    "\u00d7": "x", "\u00f7": "/", "\u00b1": "+/-", "\u00b0": " deg",
    "\u2192": "->", "\u2190": "<-", "\u21d2": "=>",
    "\u2713": "OK", "\u2714": "OK", "\u2605": "*",
}


def _sanitize_pdf_text(text: str) -> str:
    """Force text into a latin-1-encodable string (fpdf2 core-font safe)."""
    if not text:
        return text
    text = "".join(_PDF_ASCII_MAP.get(c, c) for c in str(text))
    return text.encode("latin-1", errors="replace").decode("latin-1")

from docx import Document
from docx.shared import Pt
from fpdf import FPDF


# ---------------------------------------------------------------------------
# Section headings (ATS-friendly, language-aware)
# ---------------------------------------------------------------------------

_SECTION_HEADINGS = {
    "pt": {
        "contact": "Contato",
        "summary": "Resumo Profissional",
        "skills": "Habilidades",
        "experience": "Experiencia Profissional",
        "education": "Formacao Academica",
        "languages": "Idiomas",
        "certifications": "Certificacoes",
    },
    "en": {
        "contact": "Contact",
        "summary": "Professional Summary",
        "skills": "Skills",
        "experience": "Professional Experience",
        "education": "Education",
        "languages": "Languages",
        "certifications": "Certifications",
    },
    "es": {
        "contact": "Contacto",
        "summary": "Resumen Profesional",
        "skills": "Habilidades",
        "experience": "Experiencia Profesional",
        "education": "Formacion Academica",
        "languages": "Idiomas",
        "certifications": "Certificaciones",
    },
}


def _section_headings(lang: str) -> dict:
    return _SECTION_HEADINGS.get(lang, _SECTION_HEADINGS["en"])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_cv_data(cv_data: dict) -> dict:
    if not cv_data:
        raise ValueError("cv_data is empty. Provide a valid CV data dictionary.")
    return ensure_cv_structure(cv_data)


def _contact_line(cv: dict) -> str:
    parts = [p for p in (cv.get("phone"), cv.get("email"), cv.get("location"), cv.get("linkedin")) if p]
    return " | ".join(parts)


def _bullets_from_description(description: str) -> list[str]:
    raw = description.replace("\\n", "\n")
    return [b.strip("- \t") for b in raw.split("\n") if b.strip("- \t")]


# ---------------------------------------------------------------------------
# DOCX export
# ---------------------------------------------------------------------------

def export_docx(cv_data: dict, lang: str) -> bytes:
    cv = _validate_cv_data(cv_data)
    headings = _section_headings(lang)
    doc = Document()

    # -- Default font --
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Calibri"
    font.size = Pt(11)

    # -- Name --
    if cv.get("name"):
        p = doc.add_paragraph()
        run = p.add_run(cv["name"])
        run.bold = True
        run.font.size = Pt(18)
        run.font.name = "Calibri"

    # -- Title --
    if cv.get("title"):
        p = doc.add_paragraph()
        run = p.add_run(cv["title"])
        run.font.size = Pt(12)
        run.font.name = "Calibri"
        run.font.color.rgb = None  # default color

    # -- Contact --
    contact = _contact_line(cv)
    if contact:
        p = doc.add_paragraph()
        run = p.add_run(contact)
        run.font.size = Pt(10)
        run.font.name = "Calibri"

    # -- Summary --
    if cv.get("summary"):
        doc.add_heading(headings["summary"], level=2)
        doc.add_paragraph(cv["summary"])

    # -- Skills --
    if cv.get("skills"):
        doc.add_heading(headings["skills"], level=2)
        doc.add_paragraph(", ".join(cv["skills"]))

    # -- Experience --
    if cv.get("experience"):
        doc.add_heading(headings["experience"], level=2)
        for exp in cv["experience"]:
            header_parts = [exp.get("role", "")]
            if exp.get("company"):
                header_parts.append(f" -- {exp['company']}")
            if exp.get("dates"):
                header_parts.append(f" ({exp['dates']})")
            p = doc.add_paragraph()
            run = p.add_run("".join(header_parts))
            run.bold = True
            run.font.size = Pt(11)
            run.font.name = "Calibri"
            for bullet in _bullets_from_description(exp.get("description", "")):
                doc.add_paragraph(bullet, style="List Bullet")

    # -- Education --
    if cv.get("education"):
        doc.add_heading(headings["education"], level=2)
        for edu in cv["education"]:
            parts = [edu.get("degree", "")]
            if edu.get("school"):
                parts.append(f" -- {edu['school']}")
            if edu.get("dates"):
                parts.append(f" ({edu['dates']})")
            doc.add_paragraph("".join(parts))

    # -- Languages --
    if cv.get("languages"):
        doc.add_heading(headings["languages"], level=2)
        doc.add_paragraph(", ".join(cv["languages"]))

    # -- Certifications --
    if cv.get("certifications"):
        doc.add_heading(headings["certifications"], level=2)
        doc.add_paragraph(", ".join(cv["certifications"]))

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------

def _find_dejavu_font() -> str | None:
    search_dirs = []
    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", "C:\\Windows")
        search_dirs.append(os.path.join(windir, "Fonts"))
    elif sys.platform == "darwin":
        search_dirs.extend([
            "/Library/Fonts",
            "/System/Library/Fonts",
            os.path.expanduser("~/Library/Fonts"),
        ])
    else:
        search_dirs.extend([
            "/usr/share/fonts/truetype/dejavu",
            "/usr/share/fonts/TTF",
            "/usr/share/fonts",
        ])
    for d in search_dirs:
        path = os.path.join(d, "DejaVuSans.ttf")
        if os.path.isfile(path):
            return path
    return None


def _create_pdf() -> tuple[FPDF, str]:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(20, 15, 20)

    dejavu_path = _find_dejavu_font()
    font_family = "Helvetica"
    if dejavu_path:
        try:
            pdf.add_font("DejaVu", "", dejavu_path)
            bold_path = dejavu_path.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
            if os.path.isfile(bold_path):
                pdf.add_font("DejaVu", "B", bold_path)
            font_family = "DejaVu"
        except Exception:
            pass

    return pdf, font_family


def _pdf_section_heading(pdf: FPDF, text: str, font_family: str) -> None:
    pdf.ln(4)
    pdf.set_font(font_family, "B", 11)
    pdf.cell(0, 7, _sanitize_pdf_text(text), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(180, 180, 180)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2)


def _pdf_body(pdf: FPDF, text: str, font_family: str, size: int = 10) -> None:
    pdf.set_font(font_family, "", size)
    pdf.multi_cell(0, 5, _sanitize_pdf_text(text), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def export_pdf(cv_data: dict, lang: str) -> bytes:
    cv = _validate_cv_data(cv_data)
    headings = _section_headings(lang)
    pdf, font_family = _create_pdf()
    pdf.add_page()

    # -- Name --
    if cv.get("name"):
        pdf.set_font(font_family, "B", 14)
        pdf.cell(0, 8, _sanitize_pdf_text(cv["name"]), new_x="LMARGIN", new_y="NEXT")

    # -- Title --
    if cv.get("title"):
        pdf.set_font(font_family, "", 11)
        pdf.cell(0, 6, _sanitize_pdf_text(cv["title"]), new_x="LMARGIN", new_y="NEXT")

    # -- Contact --
    contact = _contact_line(cv)
    if contact:
        pdf.set_font(font_family, "", 9)
        pdf.cell(0, 5, _sanitize_pdf_text(contact), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)

    # -- Summary --
    if cv.get("summary"):
        _pdf_section_heading(pdf, headings["summary"], font_family)
        _pdf_body(pdf, cv["summary"], font_family)

    # -- Skills --
    if cv.get("skills"):
        _pdf_section_heading(pdf, headings["skills"], font_family)
        _pdf_body(pdf, ", ".join(cv["skills"]), font_family)

    # -- Experience --
    if cv.get("experience"):
        _pdf_section_heading(pdf, headings["experience"], font_family)
        for exp in cv["experience"]:
            header_parts = [exp.get("role", "")]
            if exp.get("company"):
                header_parts.append(f" -- {exp['company']}")
            if exp.get("dates"):
                header_parts.append(f" ({exp['dates']})")
            pdf.set_font(font_family, "B", 10)
            pdf.multi_cell(0, 5, _sanitize_pdf_text("".join(header_parts)), new_x="LMARGIN", new_y="NEXT")
            for bullet in _bullets_from_description(exp.get("description", "")):
                pdf.set_font(font_family, "", 9)
                pdf.multi_cell(0, 5, _sanitize_pdf_text(f"  - {bullet}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

    # -- Education --
    if cv.get("education"):
        _pdf_section_heading(pdf, headings["education"], font_family)
        for edu in cv["education"]:
            parts = [edu.get("degree", "")]
            if edu.get("school"):
                parts.append(f" -- {edu['school']}")
            if edu.get("dates"):
                parts.append(f" ({edu['dates']})")
            _pdf_body(pdf, "".join(parts), font_family, 10)

    # -- Languages --
    if cv.get("languages"):
        _pdf_section_heading(pdf, headings["languages"], font_family)
        _pdf_body(pdf, ", ".join(cv["languages"]), font_family)

    # -- Certifications --
    if cv.get("certifications"):
        _pdf_section_heading(pdf, headings["certifications"], font_family)
        _pdf_body(pdf, ", ".join(cv["certifications"]), font_family)

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()
