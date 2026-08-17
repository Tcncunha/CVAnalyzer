"""
CV Analyzer -- AI-Driven Career Assistant
=========================================
Entry point. Run with:  streamlit run src/app.py
"""

import json
import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parent)
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import streamlit as st
import openai

from config import APP_ICON, ANALYSIS_PROMPT
from cv_builder import (
    CV_TAILOR_PROMPT,
    _ensure_structure,
    render_cv_builder,
    render_cv_preview,
)
from i18n import prompt_language, t
from job_fetcher import fetch_job_description
from profile_manager import save_profile
from progress_utils import run_with_progress
from providers import analyze_profile, get_api_key
from ui import render_header, render_input_columns, render_job_search, render_results, render_sidebar, render_footer


def _format_insights(results: dict) -> str:
    """Format the analysis results into plain text to guide the tailored CV."""
    lines = []
    if results.get("pontos_fortes"):
        lines.append(
            "STRENGTHS:\n- " + "\n- ".join(str(x) for x in results["pontos_fortes"])
        )
    if results.get("lacunas"):
        lines.append(
            "GAPS:\n- " + "\n- ".join(str(x) for x in results["lacunas"])
        )
    if results.get("sugestoes_melhoria"):
        lines.append(
            "SUGGESTIONS:\n- "
            + "\n- ".join(str(x) for x in results["sugestoes_melhoria"])
        )
    return "\n\n".join(lines)


def _render_tailored_cv_offer() -> None:
    """Offer to generate a CV tailored to the vacancy after a successful analysis."""
    profile_text = st.session_state.get("_last_profile", "")
    jd = st.session_state.get("_last_jd", "")
    results = st.session_state.get("_last_results", {})
    if not profile_text or not jd:
        return

    st.divider()
    st.subheader(t("tailored_cv_header"))
    st.caption(t("tailored_cv_caption"))

    # Optional photo (Advanced layout) -- picked before generating the CV.
    photo_file = None
    if st.session_state.get("cv_layout", "advanced") == "advanced":
        photo_file = st.file_uploader(
            t("cv_photo_label"),
            type=["jpg", "jpeg", "png"],
            help=t("cv_photo_help"),
            key="cv_photo_analyzer",
        )

    if st.button(
        t("tailored_cv_button"), type="primary", use_container_width=True,
        key="tailored_cv_btn",
    ):
        provider = st.session_state.get("provider_select", "opencode_zen")
        model = st.session_state.get("model_select", "big-pickle")
        try:
            # Capture the key in the main thread (see run_with_progress).
            api_key = get_api_key(provider)
            lang = prompt_language()  # evaluated in the main thread
            raw = run_with_progress(
                lambda: analyze_profile(
                    profile_text,
                    jd,
                    provider,
                    model,
                    CV_TAILOR_PROMPT,
                    lang,
                    analysis_insights=_format_insights(results),
                    api_key=api_key,
                ),
                stages=[
                    t("progress_cv_tailoring"),
                    t("progress_cv_writing"),
                ],
                initial_label=t("tailored_cv_spinner"),
            )
            st.session_state["cv_data"] = _ensure_structure(raw)
            st.session_state["cv_built"] = True
            st.session_state["_tailored_cv_generated"] = True
            st.success(t("tailored_cv_success"))
        except openai.RateLimitError:
            st.error(t("error_rate_limit"))
        except Exception as exc:
            st.error(t("error_unexpected", error=exc))
            return

    if st.session_state.get("_tailored_cv_generated"):
        render_cv_preview(photo_file, key_prefix="analyzer")


def render_analyzer():
    """Render the CV Analyzer tab."""
    if "_save_requested" not in st.session_state:
        st.session_state["_save_requested"] = False

    # Pre-fill fields from loaded profile
    loaded_data = st.session_state.get("_sidebar_loaded_data")
    if loaded_data:
        if not st.session_state.get("_loaded_from_disk"):
            st.session_state["profile_text_area"] = loaded_data.get("profile_text", "")
            st.session_state["jd_text_area"] = loaded_data.get("job_description", "")
            st.session_state["job_url_input"] = loaded_data.get("job_url", "")
            st.session_state["_loaded_from_disk"] = True
    else:
        st.session_state["_loaded_from_disk"] = False

    # Main input area
    profile_text, job_description, job_url = render_input_columns()

    # Handle save request from sidebar
    if st.session_state["_save_requested"]:
        st.session_state["_save_requested"] = False
        identifier = st.session_state.get("_sidebar_identifier", "")
        if identifier.strip():
            payload = {
                "identifier": identifier.strip(),
                "profile_text": profile_text,
                "job_description": job_description,
                "job_url": job_url,
            }
            path = save_profile(identifier.strip(), payload)
            st.sidebar.success(t("profile_saved_success", name=path.name))
            st.rerun()

    # Analyze button
    st.divider()
    analyze_clicked = st.button(
        t("analyze_button"), type="primary", use_container_width=True
    )

    if analyze_clicked:
        if not profile_text.strip():
            st.error(t("error_profile_empty"))
            return

        jd = job_description.strip()

        # Auto-fetch the job description from the URL when nothing was pasted
        if not jd and job_url.strip():
            with st.spinner(t("spinner_fetching_job")):
                try:
                    jd = fetch_job_description(job_url.strip())
                except Exception:
                    jd = ""
            if jd:
                st.success(t("job_fetch_success", chars=len(jd)))
            else:
                st.error(t("job_fetch_failed"))

        if not jd:
            st.error(t("error_jd_empty"))
            return

        selected_provider = st.session_state.get("provider_select", "opencode_zen")
        selected_model = st.session_state.get("model_select", "big-pickle")

        try:
            # Capture the key in the main thread (the progress worker
            # thread must not touch Streamlit session state).
            api_key = get_api_key(selected_provider)
            lang = prompt_language()  # evaluated in the main thread
            results = run_with_progress(
                lambda: analyze_profile(
                    profile_text,
                    jd,
                    selected_provider,
                    selected_model,
                    ANALYSIS_PROMPT,
                    lang,
                    api_key=api_key,
                ),
                stages=[
                    t("progress_send"),
                    t("progress_analyzing"),
                    t("progress_parsing"),
                ],
                initial_label=t("spinner_analyzing"),
            )
            st.session_state["_last_results"] = results
            st.session_state["_last_job_url"] = job_url
            st.session_state["_last_profile"] = profile_text
            st.session_state["_last_jd"] = jd
            st.session_state["_tailored_cv_generated"] = False
        except ValueError as exc:
            st.error(str(exc))
        except json.JSONDecodeError:
            st.error(t("error_json_invalid"))
        except openai.RateLimitError:
            st.error(t("error_rate_limit"))
        except Exception as exc:
            st.error(t("error_unexpected", error=exc))

    # Keep the last analysis results visible across reruns (the widget
    # rerun caused by any click would otherwise clear them).
    if st.session_state.get("_last_results"):
        render_results(
            st.session_state["_last_results"],
            st.session_state.get("_last_job_url", ""),
        )

    # Always render the tailored-CV offer so the button keeps working
    # on subsequent reruns (it cannot live inside the analyze block).
    _render_tailored_cv_offer()


def main():
    st.set_page_config(page_title=t("app_title"), page_icon=APP_ICON, layout="wide")

    render_header()

    # Sidebar is always visible (shared across tabs)
    identifier, loaded_data, selected_provider, selected_model = render_sidebar()
    st.session_state["_sidebar_identifier"] = identifier
    st.session_state["_sidebar_loaded_data"] = loaded_data

    # --- Tabs: Analyzer | CV Builder | Job Search ---
    tab_analyzer, tab_builder, tab_job_search = st.tabs(
        [t("tab_analyzer"), t("tab_builder"), t("tab_job_search")]
    )

    with tab_analyzer:
        render_analyzer()

    with tab_builder:
        render_cv_builder()

    with tab_job_search:
        render_job_search()

    render_footer()


if __name__ == "__main__":
    main()
