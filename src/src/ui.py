"""
Streamlit UI components — sidebar, input columns, and result rendering.
"""

import streamlit as st

import i18n
from config import DEFAULT_MODEL, DEFAULT_PROVIDER, MODELS, PROVIDERS
from pdf_extractor import extract_text_from_pdf
from profile_manager import list_saved_profiles, load_profile, save_profile


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar() -> tuple[str, dict | None, str, str]:
    """Render sidebar controls and return (identifier, loaded_data, provider, model)."""
    with st.sidebar:
        st.header(i18n.t("sidebar_settings_header"))

        # --- Provider ---
        provider_keys = list(PROVIDERS.keys())
        default_prov_idx = provider_keys.index(DEFAULT_PROVIDER)

        selected_provider = st.selectbox(
            i18n.t("provider_label"),
            options=provider_keys,
            format_func=lambda k: PROVIDERS[k]["name"],
            index=default_prov_idx,
            key="provider_select",
        )

        # --- Model (dynamic based on provider) ---
        model_dict = MODELS.get(selected_provider, {})
        model_keys = list(model_dict.keys())
        default_model_idx = (
            model_keys.index(DEFAULT_MODEL) if DEFAULT_MODEL in model_keys else 0
        )

        selected_model = st.selectbox(
            i18n.t("model_label"),
            options=model_keys,
            format_func=lambda k: model_dict[k],
            index=default_model_idx,
            key="model_select",
        )

        st.divider()
        st.header(i18n.t("profile_mgmt_header"))

        saved = list_saved_profiles()
        options = [None] + saved

        selected = st.selectbox(
            i18n.t("saved_profiles_label"),
            options=options,
            format_func=lambda x: i18n.t("new_profile_label") if x is None else x,
            index=0,
            key="saved_profile_select",
        )

        loaded_data = None
        if selected is not None:
            loaded_data = load_profile(selected)
            if loaded_data:
                st.success(i18n.t("profile_loaded", name=selected))

        identifier = st.text_input(
            i18n.t("candidate_identifier_label"),
            value="" if selected is None else selected,
            placeholder=i18n.t("candidate_identifier_placeholder"),
        )

        save_clicked = st.button(
            i18n.t("save_profile_button"), use_container_width=True
        )

        if save_clicked:
            if not identifier.strip():
                st.warning(i18n.t("save_identifier_warning"))
            else:
                st.session_state["_save_requested"] = True

    return identifier, loaded_data, selected_provider, selected_model


# ---------------------------------------------------------------------------
# Input Columns
# ---------------------------------------------------------------------------

def render_input_columns() -> tuple[str, str, str]:
    """Render the two-column input area. Returns (profile_text, job_description, job_url)."""
    col1, col2 = st.columns(2, gap="medium")

    # --- Column 1: Candidate Profile ---
    with col1:
        with st.container(border=True):
            st.subheader(i18n.t("candidate_profile_header"))

            input_mode = st.radio(
                i18n.t("profile_source_label"),
                options=["paste", "upload"],
                format_func=lambda x: i18n.t(f"profile_mode_{x}"),
                horizontal=True,
                key="profile_mode",
            )

            profile_text = ""

            if input_mode == "upload":
                uploaded_pdf = st.file_uploader(
                    i18n.t("upload_pdf_label"),
                    type=["pdf"],
                    help=i18n.t("upload_pdf_help"),
                )
                if uploaded_pdf is not None:
                    try:
                        profile_text = extract_text_from_pdf(uploaded_pdf)
                        st.success(
                            i18n.t("pdf_success", chars=len(profile_text))
                        )
                    except RuntimeError as err:
                        st.error(str(err))
            else:
                profile_text = st.text_area(
                    i18n.t("profile_text_label"),
                    height=350,
                    placeholder=i18n.t("profile_text_placeholder"),
                    key="profile_text_area",
                )

    # --- Column 2: Job Description ---
    with col2:
        with st.container(border=True):
            st.subheader(i18n.t("job_description_header"))

            job_url = st.text_input(
                i18n.t("job_url_label"),
                placeholder=i18n.t("job_url_placeholder"),
                key="job_url_input",
            )

            job_description = st.text_area(
                i18n.t("job_description_label"),
                height=350,
                placeholder=i18n.t("job_description_placeholder"),
                key="jd_text_area",
            )

    return profile_text, job_description, job_url


# ---------------------------------------------------------------------------
# Results Display
# ---------------------------------------------------------------------------

def render_results(results: dict, job_url: str) -> None:
    """Render the analysis results using Streamlit components."""
    st.divider()
    st.header(i18n.t("results_header"))

    # --- Score ---
    score = max(0, min(100, int(results.get("overall_score", 0))))

    if score >= 75:
        color, quality_key = "green", "score_excellent"
    elif score >= 50:
        color, quality_key = "orange", "score_good"
    else:
        color, quality_key = "red", "score_low"

    score_col, progress_col = st.columns([1, 3])
    with score_col:
        st.metric(label=i18n.t("compatibility_label"), value=f"{score}/100")
        st.markdown(f":{color}[**{i18n.t(quality_key)}**]")
    with progress_col:
        st.progress(score / 100, text=i18n.t("score_progress_text", score=score))

    if job_url:
        st.caption(i18n.t("job_reference_caption", url=job_url))

    st.divider()

    # --- Strengths, Gaps, Suggestions ---
    col_strengths, col_gaps, col_suggestions = st.columns(3, gap="medium")

    with col_strengths:
        with st.container(border=True):
            st.subheader(i18n.t("strengths_header"))
            for item in results.get("pontos_fortes", []):
                st.markdown(f"- {item}")

    with col_gaps:
        with st.container(border=True):
            st.subheader(i18n.t("gaps_header"))
            for item in results.get("lacunas", []):
                st.markdown(f"- {item}")

    with col_suggestions:
        with st.container(border=True):
            st.subheader(i18n.t("suggestions_header"))
            for item in results.get("sugestoes_melhoria", []):
                st.markdown(f"- {item}")

    # --- Raw JSON expander ---
    with st.expander(i18n.t("json_expander_label")):
        st.json(results)

    # --- Disclaimer ---
    st.divider()
    st.caption(i18n.t("disclaimer_text"))
