"""
CV Analyzer -- AI-Driven Career Assistant
=========================================
Entry point. Run with:  streamlit run src/app.py
"""

import json

import streamlit as st

from config import APP_ICON, ANALYSIS_PROMPT
from cv_builder import render_cv_builder
from i18n import prompt_language, t
from profile_manager import save_profile
from providers import analyze_profile
from ui import render_header, render_input_columns, render_results, render_sidebar, render_footer


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
        if not job_description.strip():
            st.error(t("error_jd_empty"))
            return

        selected_provider = st.session_state.get("provider_select", "opencode_zen")
        selected_model = st.session_state.get("model_select", "big-pickle")

        try:
            with st.spinner(t("spinner_analyzing")):
                results = analyze_profile(
                    profile_text,
                    job_description,
                    selected_provider,
                    selected_model,
                    ANALYSIS_PROMPT,
                    prompt_language(),
                )
            render_results(results, job_url)
        except ValueError as exc:
            st.error(str(exc))
        except json.JSONDecodeError:
            st.error(t("error_json_invalid"))
        except Exception as exc:
            st.error(t("error_unexpected", error=exc))


def main():
    st.set_page_config(page_title=t("app_title"), page_icon=APP_ICON, layout="wide")

    render_header()

    # Sidebar is always visible (shared across tabs)
    identifier, loaded_data, selected_provider, selected_model = render_sidebar()
    st.session_state["_sidebar_identifier"] = identifier
    st.session_state["_sidebar_loaded_data"] = loaded_data

    # --- Tabs: Analyzer | CV Builder ---
    tab_analyzer, tab_builder = st.tabs([t("tab_analyzer"), t("tab_builder")])

    with tab_analyzer:
        render_analyzer()

    with tab_builder:
        render_cv_builder()

    render_footer()


if __name__ == "__main__":
    main()
