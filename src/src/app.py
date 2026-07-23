"""
CV Analyzer — AI-Driven Career Assistant
=========================================
Entry point. Run with:  streamlit run src/app.py
"""

import json

import streamlit as st

import i18n
from analyzer import analyze_profile
from config import APP_ICON
from profile_manager import save_profile
from ui import render_input_columns, render_results, render_sidebar


def render_header() -> None:
    """Render the title/caption alongside a language switcher (EN/PT)."""
    title_col, lang_col = st.columns([5, 1], vertical_alignment="bottom")

    with lang_col:
        lang_keys = list(i18n.LANGUAGES.keys())
        choice = st.selectbox(
            "🌐",
            options=lang_keys,
            index=lang_keys.index(i18n.get_lang()),
            format_func=lambda k: f"{i18n.LANGUAGES[k]['flag']} {i18n.LANGUAGES[k]['label']}",
            key="lang_select",
            label_visibility="collapsed",
        )
        i18n.set_lang(choice)

    with title_col:
        st.title(f"{APP_ICON} {i18n.t('app_title')}")

    st.caption(i18n.t("app_caption"))


def main():
    # Read the persisted language (if any) before rendering anything so that
    # the page title/icon are already in the right language on load.
    st.set_page_config(
        page_title=i18n.t("app_title"), page_icon=APP_ICON, layout="wide"
    )

    render_header()

    if "_save_requested" not in st.session_state:
        st.session_state["_save_requested"] = False

    # Sidebar — provider, model, and profile management
    identifier, loaded_data, selected_provider, selected_model = render_sidebar()

    # Pre-fill fields from loaded profile
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
        if identifier.strip():
            payload = {
                "identifier": identifier.strip(),
                "profile_text": profile_text,
                "job_description": job_description,
                "job_url": job_url,
            }
            path = save_profile(identifier.strip(), payload)
            st.sidebar.success(i18n.t("profile_saved_success", name=path.name))
            st.rerun()

    # Analyze button
    st.divider()
    analyze_clicked = st.button(
        i18n.t("analyze_button"), type="primary", use_container_width=True
    )

    if analyze_clicked:
        if not profile_text.strip():
            st.error(i18n.t("error_profile_empty"))
            return
        if not job_description.strip():
            st.error(i18n.t("error_jd_empty"))
            return

        try:
            with st.spinner(i18n.t("spinner_analyzing")):
                results = analyze_profile(
                    profile_text,
                    job_description,
                    selected_provider,
                    selected_model,
                    i18n.prompt_language(),
                )
            render_results(results, job_url)
        except EnvironmentError as exc:
            st.error(str(exc))
        except json.JSONDecodeError:
            st.error(i18n.t("error_json_invalid"))
        except Exception as exc:
            st.error(i18n.t("error_unexpected", error=exc))


if __name__ == "__main__":
    main()
