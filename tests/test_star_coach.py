import pytest

import star_coach
from star_coach import DEFAULT_GRADE, _default_questions, generate_questions, grade_answer


@pytest.mark.parametrize(
    "lang,expected",
    [
        ("Portuguese (Brazil)", "star_default_q1_pt"),
        ("English", "star_default_q1_en"),
        ("Spanish", "star_default_q1_es"),
    ],
)
def test_default_questions_are_localized(lang, expected):
    questions = _default_questions(lang)
    assert len(questions) == 5
    assert all(isinstance(q, str) and q.strip() for q in questions)


def test_default_questions_fallback_on_unknown_language():
    questions = _default_questions("Klingon")
    assert len(questions) == 5


def test_generate_questions_falls_back_when_provider_fails(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(star_coach, "analyze_profile", boom)
    result = generate_questions("gemini", "m", "a job desc", "English")
    assert len(result) == 5


def test_generate_questions_validates_wrong_shape(monkeypatch):
    def wrong(*args, **kwargs):
        return {"questions": ["only-one"]}

    monkeypatch.setattr(star_coach, "analyze_profile", wrong)
    result = generate_questions("gemini", "m", "a job desc", "English")
    assert len(result) == 5


def test_grade_answer_defaults_on_failure(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(star_coach, "analyze_profile", boom)
    assert grade_answer("gemini", "m", "Q", "A", "English") == DEFAULT_GRADE


@pytest.mark.parametrize("raw_score,expected", [("8.5", 8), (8, 8), ("abc", 0), (None, 0), ("12", 0)])
def test_grade_answer_parses_score_robustly(monkeypatch, raw_score, expected):
    def ok(*args, **kwargs):
        return {"score": raw_score, "situation_feedback": "S"}

    monkeypatch.setattr(star_coach, "analyze_profile", ok)
    result = grade_answer("gemini", "m", "Q", "A", "English")
    assert result["score"] == expected
    assert set(result) == set(DEFAULT_GRADE)