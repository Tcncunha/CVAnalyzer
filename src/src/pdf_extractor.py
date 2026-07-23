"""
PDF text extraction using pypdf.
"""

import os
import tempfile

from pypdf import PdfReader

import i18n


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
        raise RuntimeError(i18n.t("pdf_extract_error", error=exc)) from exc
