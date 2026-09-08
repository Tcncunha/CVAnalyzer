"""
STAR interview coach — business logic for generating behavioral interview
questions and grading candidate answers using the STAR methodology.

Leverages `analyze_profile` from providers.py for AI calls. No UI here.
"""

from config import STAR_GRADING_PROMPT, STAR_QUESTIONS_PROMPT
from i18n import STRINGS
from providers import analyze_profile

_LANG_CODE = {"Portuguese (Brazil)": "pt", "English": "en", "Spanish": "es"}

DEFAULT_QUESTIONS = [
    "Tell me about a time you faced a significant technical challenge at work. What was the situation, what did you do, and what was the result?",
    "Describe a situation where you had to collaborate with a difficult teammate or stakeholder. How did you handle it?",
    "Give me an example of a time you took initiative on a project that was not explicitly assigned to you. What motivated you?",
    "Tell me about a time you made a mistake at work. How did you recover and what did you learn?",
    "Describe a situation where you had to prioritize competing demands under pressure. What was the outcome?",
]


def _default_questions(language: str) -> list[str]:
    """Localized fallback questions for the current UI language."""
    code = _LANG_CODE.get(language, "en")
    bucket = STRINGS.get(code, STRINGS["en"])
    return [
        bucket.get(f"star_default_q{i}", DEFAULT_QUESTIONS[i - 1])
        for i in range(1, 6)
    ]

DEFAULT_GRADE = {
    "score": 0,
    "situation_feedback": "",
    "task_feedback": "",
    "action_feedback": "",
    "result_feedback": "",
    "overall_feedback": "",
    "improved_answer_suggestion": "",
}


def generate_questions(provider: str, model: str, job_description: str, language: str) -> list[str]:
    """Generate 5 behavioral interview questions tailored to the job description."""
    try:
        result = analyze_profile(
            "",
            job_description,
            provider,
            model,
            STAR_QUESTIONS_PROMPT,
            language,
        )
        questions = result.get("questions", [])
        if isinstance(questions, list) and len(questions) == 5 and all(isinstance(q, str) for q in questions):
            return questions
        return _default_questions(language)
    except Exception:
        return _default_questions(language)


def grade_answer(provider: str, model: str, question: str, answer: str, language: str) -> dict:
    """Grade a candidate STAR answer and return feedback with defaults for robustness."""
    try:
        result = analyze_profile(
            "",
            question,
            provider,
            model,
            STAR_GRADING_PROMPT,
            language,
            answer=answer,
        )
        if not isinstance(result, dict):
            return dict(DEFAULT_GRADE)
        try:
            score = int(float(result.get("score", 0)))
        except (TypeError, ValueError):
            score = 0
        if not 1 <= score <= 10:
            score = 0
        return {
            "score": score,
            "situation_feedback": str(result.get("situation_feedback", "")),
            "task_feedback": str(result.get("task_feedback", "")),
            "action_feedback": str(result.get("action_feedback", "")),
            "result_feedback": str(result.get("result_feedback", "")),
            "overall_feedback": str(result.get("overall_feedback", "")),
            "improved_answer_suggestion": str(result.get("improved_answer_suggestion", "")),
        }
    except Exception:
        return dict(DEFAULT_GRADE)
