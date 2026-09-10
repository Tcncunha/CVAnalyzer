import json

import pytest

from cv_utils import ensure_cv_structure, parse_json_from_text


@pytest.mark.parametrize(
    "text",
    [
        '{"name": "Joao", "skills": []}',
        '```json\n{"name": "Joao"}\n```',
        'prefix {"name": "Joao"} suffix',
    ],
)
def test_parse_json_from_text_handles_fences_and_noise(text):
    assert parse_json_from_text(text)["name"] == "Joao"


def test_parse_json_from_text_raises_when_no_json():
    with pytest.raises(json.JSONDecodeError):
        parse_json_from_text("no json here")


def test_ensure_cv_structure_fills_scalars_and_lists():
    raw = {"name": "Joao", "skills": "Python, C++"}
    cv = ensure_cv_structure(raw)
    assert cv["name"] == "Joao"
    assert cv["skills"] == ["Python, C++"]
    assert cv["email"] == ""
    assert cv["experience"] == []
    assert cv["certifications"] == []


def test_ensure_cv_structure_keeps_valid_lists_and_keeps_none_as_empty():
    raw = {"experience": [{"role": "Dev"}], "summary": None, "languages": []}
    cv = ensure_cv_structure(raw)
    assert cv["experience"] == [{"role": "Dev"}]
    assert cv["summary"] == ""
    assert cv["languages"] == []


def test_ensure_cv_structure_preserves_all_keys():
    cv = ensure_cv_structure({})
    expected_keys = {
        "name", "title", "email", "phone", "location", "linkedin",
        "summary", "skills", "experience", "education", "languages",
        "certifications",
    }
    assert set(cv) == expected_keys