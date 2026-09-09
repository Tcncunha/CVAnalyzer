"""
Text extraction from uploaded files (PDF or the CV Builder's HTML download).

The CV Builder offers a "cv.html" download; accepting both formats makes the
generated CV re-usable across tabs (Analyzer, Auto Match, CV Builder).
"""

import os
import tempfile

from bs4 import BeautifulSoup
from pypdf import PdfReader


def extract_text_from_pdf(uploaded_file) -> str:
    """Extract all text from an uploaded PDF file-like object."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        reader = PdfReader(tmp_path)
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(pages).strip()

        os.unlink(tmp_path)
        return text
    except Exception as exc:
        raise RuntimeError(f"Erro ao extrair texto do PDF: {exc}") from exc


def extract_text_from_html(uploaded_file) -> str:
    """Extract readable text from an uploaded HTML file (e.g. cv.html)."""
    try:
        raw = uploaded_file.read()
        if isinstance(raw, bytes):
            soup = BeautifulSoup(raw, "html.parser")
        else:
            soup = BeautifulSoup(str(raw), "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text("\n")
        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]
        return "\n".join(lines)
    except Exception as exc:
        raise RuntimeError(f"Erro ao extrair texto do HTML: {exc}") from exc


def _looks_like_html(uploaded_file) -> bool:
    """Guess whether the uploaded file is HTML by name or content."""
    name = (getattr(uploaded_file, "name", "") or "").lower()
    if name.endswith((".html", ".htm")):
        return True
    try:
        head = uploaded_file.read(512)
        uploaded_file.seek(0)
        head = head.lstrip()
        return head.startswith(b"<!doctype") or head.startswith(b"<html") or head.startswith(b"<?xml")
    except (OSError, TypeError):
        return False


def extract_text_from_upload(uploaded_file, filename: str | None = None) -> str:
    """Extract text from a PDF or HTML upload, dispatching by file type.

    Falls back to HTML when the file name or content indicates HTML,
    otherwise treats the file as a PDF.
    """
    if filename is None:
        filename = getattr(uploaded_file, "name", "") or ""
    if filename.lower().endswith((".html", ".htm")) or _looks_like_html(uploaded_file):
        return extract_text_from_html(uploaded_file)
    return extract_text_from_pdf(uploaded_file)