"""
STAR Coach — UI module for practicing behavioral interview answers.

Walks the user through 5 AI-generated STAR questions, grades each answer
with detailed per-component feedback, and renders a final summary.
"""

import html

import streamlit as st

from i18n import prompt_language, t
from progress_utils import run_with_progress
from providers import get_selected_model
from star_coach import generate_questions, grade_answer

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TOTAL_QUESTIONS = 5

_STAR_COMPONENT_KEYS = [
    ("star_situation", "situation_feedback"),
    ("star_task", "task_feedback"),
    ("star_action", "action_feedback"),
    ("star_result", "result_feedback"),
]

_STAR_COMPONENT_COLORS = {
    "situation_feedback": "#3b82f6",  # blue
    "task_feedback": "#8b5cf6",       # purple
    "action_feedback": "#f59e0b",     # amber
    "result_feedback": "#10b981",     # emerald
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_provider_and_model() -> tuple[str, str]:
    """Read the current provider and model from session state."""
    provider = st.session_state.get("provider_select", "opencode_zen")
    model = get_selected_model()
    return provider, model


def _render_feedback_block(label_key: str, text: str, color: str) -> None:
    """Render a single STAR component feedback block with a colored accent."""
    safe_label = html.escape(str(t(label_key)), quote=False)
    safe_text = html.escape(str(text), quote=False)
    st.markdown(
        f"""
        <div style="border-left: 4px solid {color}; padding: 0.4rem 0.8rem;
                    margin-bottom: 0.5rem; background: rgba(255,255,255,0.03);
                    border-radius: 0 6px 6px 0;">
            <strong>{safe_label}</strong><br/>
            {safe_text}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _score_badge_color(score: int) -> str:
    """Return the Streamlit color name for a given score."""
    if score >= 8:
        return "green"
    if score >= 5:
        return "orange"
    return "red"


def _render_question_feedback(result: dict) -> None:
    """Render full STAR feedback for a single graded question."""
    score = result.get("score", 0)

    st.markdown(
        f"**:thinking_face: {t('star_score')}: "
        f":{_score_badge_color(score)}[{score}/10]**"
    )

    for label_key, result_key in _STAR_COMPONENT_KEYS:
        text = result.get(result_key, "")
        if text:
            _render_feedback_block(label_key, text, _STAR_COMPONENT_COLORS[result_key])

    overall = result.get("overall_feedback", "")
    if overall:
        st.info(f"**{t('star_overall')}:** {overall}")

    improved = result.get("improved_answer_suggestion", "")
    if improved:
        with st.expander(t("star_improved"), expanded=False):
            st.markdown(improved)


# ---------------------------------------------------------------------------
# Public render function — called by app.py
# ---------------------------------------------------------------------------

def render_star_page() -> None:
    """Render the full STAR Coach page."""
    st.header(t("star_header"))
    st.caption(t("star_caption"))

    # --- Source JD --------------------------------------------------------
    jd = st.session_state.get("last_jd", "") or st.session_state.get("_last_jd", "")
    if not jd:
        jd = st.text_area(
            t("job_description_label"),
            placeholder=t("job_description_placeholder"),
            key="star_jd_fallback",
            height=120,
        )

    # --- Session state ----------------------------------------------------
    questions = st.session_state.get("star_questions")
    idx = st.session_state.get("star_idx", 0)

    if questions is None:
        # Session not started yet — show start button
        if st.button(t("star_start"), type="primary", use_container_width=True, key="star_start_btn"):
            if not jd or not jd.strip():
                st.warning(t("star_jd_empty"))
                return

            provider, model = _get_provider_and_model()
            lang = prompt_language()

            generated = run_with_progress(
                lambda: generate_questions(provider, model, jd.strip(), lang),
                stages=[t("star_spinner_questions")],
                initial_label=t("star_spinner_questions"),
            )

            st.session_state["star_questions"] = generated
            st.session_state["star_idx"] = 0
            st.session_state["star_results"] = []
            st.rerun()
        return

    # --- Training flow ----------------------------------------------------
    if idx < _TOTAL_QUESTIONS:
        _render_active_session()
    else:
        _render_final_summary()


# ---------------------------------------------------------------------------
# Active training session
# ---------------------------------------------------------------------------

def _render_active_session() -> None:
    """Render the current question, answer input, and past feedback."""
    questions: list[str] = st.session_state["star_questions"]
    results: list[dict] = st.session_state.get("star_results", [])
    idx: int = st.session_state["star_idx"]

    st.progress(
        len(results) / _TOTAL_QUESTIONS,
        text=f"{t('star_progress')}: {len(results)}/{_TOTAL_QUESTIONS}",
    )

    # --- Feedback for already-answered questions --------------------------
    for i, res in enumerate(results):
        with st.expander(
            f":white_check_mark: {t('star_question_label')} {i + 1}",
            expanded=False,
        ):
            st.markdown(f"*{questions[i]}*")
            _render_question_feedback(res)

    # --- Current question -------------------------------------------------
    st.divider()
    st.subheader(f"{t('star_question_label')} {idx + 1}/{_TOTAL_QUESTIONS}")
    st.markdown(f"**{questions[idx]}**")

    answer = st.text_area(
        t("star_answer_label"),
        key=f"star_answer_{idx}",
        height=200,
        placeholder=t("star_answer_label"),
    )

    if st.button(
        t("star_submit"),
        type="primary",
        use_container_width=True,
        key=f"star_submit_{idx}",
    ):
        if not answer.strip():
            st.warning(t("star_answer_empty"))
            return

        provider, model = _get_provider_and_model()
        lang = prompt_language()

        grade_result = run_with_progress(
            lambda: grade_answer(provider, model, questions[idx], answer.strip(), lang),
            stages=[t("star_spinner_grading")],
            initial_label=t("star_spinner_grading"),
        )

        results.append(grade_result)
        st.session_state["star_results"] = results
        st.session_state["star_idx"] = idx + 1

        # Show the feedback immediately so it is never lost.
        st.divider()
        _render_question_feedback(grade_result)

        # Next button to proceed to the following question.
        if st.button(
            t("star_next"),
            type="primary",
            key=f"star_next_{idx}",
            use_container_width=True,
        ):
            st.rerun()


# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------

def _render_final_summary() -> None:
    """Render the final score summary after all questions are answered."""
    questions: list[str] = st.session_state.get("star_questions", [])
    results: list[dict] = st.session_state.get("star_results", [])

    valid_scores = [r.get("score", 0) for r in results if r.get("score", 0) > 0]
    avg_score = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 0

    st.balloons()
    st.subheader(t("star_done"))
    st.metric(label=t("star_final_score"), value=f"{avg_score}/10")

    # --- Per-question recap -----------------------------------------------
    st.subheader(t("star_summary"))
    for i, res in enumerate(results):
        score = res.get("score", 0)
        with st.expander(
            f"{t('star_question_label')} {i + 1} — "
            f":{_score_badge_color(score)}[{score}/10]",
            expanded=False,
        ):
            st.markdown(f"*{questions[i]}*")
            _render_question_feedback(res)

    # --- Start over -------------------------------------------------------
    st.divider()
    if st.button(
        t("star_start"),
        type="primary",
        use_container_width=True,
        key="star_restart_btn",
    ):
        for key in ["star_questions", "star_idx", "star_results"]:
            st.session_state.pop(key, None)
        st.rerun()