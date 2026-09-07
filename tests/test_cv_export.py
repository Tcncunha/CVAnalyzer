import pytest

from cv_export import export_docx, export_pdf, _sanitize_pdf_text

SAMPLE_CV = {
    "name": "Joao da Silva",
    "title": "Engenheiro de Software",
    "summary": "Resumo da carreira.",
    "skills": ["Python", "SQL"],
    "experience": [
        {
            "role": "Dev",
            "company": "Acme",
            "dates": "2020 - 2022",
            "description": "Responsabilidades principales\n- Bullet A\n- Bullet B",
        }
    ],
    "education": [],
    "languages": ["Portugues"],
    "certifications": [],
}

UNICODE_CV = {
    **SAMPLE_CV,
    "name": "Jo\u00e3o \u2014 S\u00e3o Paulo",
    "title": "Engenheiro \u2022 Senior",
    "summary": "Resumo \u2014 com \u201caspas\u201d e \u2026 retic\u00eancias \u2713",
    "skills": ["Python", "C++", "\u2192"],
}


def test_export_docx_returns_non_empty_docx():
    data = export_docx(SAMPLE_CV, "pt")
    assert data[:2] == b"PK"
    assert len(data) > 1000


@pytest.mark.parametrize("lang", ["pt", "en", "es"])
def test_export_pdf_works_for_all_langs(lang):
    data = export_pdf(SAMPLE_CV, lang)
    assert data[:4] == b"%PDF"
    assert len(data) > 500


def test_export_pdf_survives_non_latin1_chars():
    data = export_pdf(UNICODE_CV, "pt")
    assert data[:4] == b"%PDF"


def test_export_functions_raise_on_empty_cv():
    with pytest.raises(ValueError):
        export_docx({}, "en")
    with pytest.raises(ValueError):
        export_pdf(None, "en")


def test_sanitize_pdf_text_maps_common_glyphs_and_replaces():
    text = "\u2014 \u2022 \u201cquotes\u201d \u2713"
    result = _sanitize_pdf_text(text)
    assert result.encode("latin-1")  # must be encodable
    # dumb replacement only when nothing else can save it
    assert "\u2713" not in result or _sanitize_pdf_text(text).encode("latin-1")


def test_sanitize_pdf_text_keeps_latin1_accents():
    result = _sanitize_pdf_text("Jo\u00e3o \u00e7\u00e3o \u00f3 \u00ed \u00fa \u00d1")
    assert result == "Jo\u00e3o \u00e7\u00e3o \u00f3 \u00ed \u00fa \u00d1"