"""
Streamlit UI components -- sidebar (with API key inputs), input columns,
results display, and page header.
"""

import streamlit as st

from config import APP_ICON
from i18n import get_lang, LANGUAGES, set_lang, t
from pdf_extractor import extract_text_from_pdf
from profile_manager import list_saved_profiles, load_profile
from providers import DEFAULT_MODEL, DEFAULT_PROVIDER, MODELS, PROVIDERS


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

def render_header() -> None:
    """Render a polished gradient hero banner with a language switcher above it."""
    st.markdown(
        """
        <style>
        .cva-hero {
            background: linear-gradient(135deg, #0b1e3d 0%, #123a5e 45%, #0f766e 100%);
            border-radius: 16px;
            padding: 2.25rem 2.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 12px 28px -12px rgba(2, 12, 27, 0.55);
        }
        .cva-hero-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 54px;
            height: 54px;
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.14);
            font-size: 1.7rem;
            margin-bottom: 0.85rem;
        }
        .cva-hero h1 {
            color: #ffffff;
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            margin: 0;
            line-height: 1.2;
        }
        .cva-hero p {
            color: rgba(255, 255, 255, 0.82);
            font-size: 1.02rem;
            margin: 0.5rem 0 0 0;
            font-weight: 400;
        }
        div[data-testid="stSelectbox"] > div > div {
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _, lang_col = st.columns([5, 1])
    with lang_col:
        lang_keys = list(LANGUAGES.keys())
        choice = st.selectbox(
            "🌐",
            options=lang_keys,
            index=lang_keys.index(get_lang()),
            format_func=lambda k: f"{LANGUAGES[k]['flag']} {LANGUAGES[k]['label']}",
            key="lang_select",
            label_visibility="collapsed",
        )
        set_lang(choice)

    st.markdown(
        f"""
        <div class="cva-hero">
            <div class="cva-hero-icon">{APP_ICON}</div>
            <h1>{t('app_title')}</h1>
            <p>{t('app_caption')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar() -> tuple[str, dict | None, str, str]:
    """Render sidebar controls and return (identifier, loaded_data, provider, model).

    When a provider requires an API key, a password input is shown. The key
    lives only in Streamlit session state and is never written to disk.
    """
    with st.sidebar:
        st.header(t("sidebar_settings_header"))

        # --- Provider selector ---
        provider_keys = list(PROVIDERS.keys())
        default_prov_idx = provider_keys.index(DEFAULT_PROVIDER)

        selected_provider = st.selectbox(
            t("provider_label"),
            options=provider_keys,
            format_func=lambda k: PROVIDERS[k]["name"],
            index=default_prov_idx,
            key="provider_select",
        )

        # --- API key input (only when provider needs one) ---
        provider_cfg = PROVIDERS[selected_provider]
        if provider_cfg["needs_key"]:
            session_key = f"_api_key_{selected_provider}"
            current_val = st.session_state.get(session_key, "")

            api_key = st.text_input(
                t("api_key_label"),
                value=current_val,
                type="password",
                placeholder=t("api_key_placeholder"),
                key=f"api_key_input_{selected_provider}",
            )
            st.session_state[session_key] = api_key

            st.caption(t("api_key_info"))

            if not api_key.strip():
                st.warning(t("api_key_required"))

        # --- Model selector (dynamic based on provider) ---
        model_dict = MODELS.get(selected_provider, {})
        model_keys = list(model_dict.keys())
        default_model_idx = (
            model_keys.index(DEFAULT_MODEL) if DEFAULT_MODEL in model_keys else 0
        )

        selected_model = st.selectbox(
            t("model_label"),
            options=model_keys,
            format_func=lambda k: model_dict[k],
            index=default_model_idx,
            key="model_select",
        )

        st.divider()
        st.header(t("profile_mgmt_header"))

        saved = list_saved_profiles()
        options = [None] + saved

        selected = st.selectbox(
            t("saved_profiles_label"),
            options=options,
            format_func=lambda x: t("new_profile_label") if x is None else x,
            index=0,
            key="saved_profile_select",
        )

        loaded_data = None
        if selected is not None:
            loaded_data = load_profile(selected)
            if loaded_data:
                st.success(t("profile_loaded", name=selected))

        identifier = st.text_input(
            t("candidate_identifier_label"),
            value="" if selected is None else selected,
            placeholder=t("candidate_identifier_placeholder"),
        )

        save_clicked = st.button(
            t("save_profile_button"), use_container_width=True
        )

        if save_clicked:
            if not identifier.strip():
                st.warning(t("save_identifier_warning"))
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
            st.subheader(t("candidate_profile_header"))

            input_mode = st.radio(
                t("profile_source_label"),
                options=["paste", "upload"],
                format_func=lambda x: t(f"profile_mode_{x}"),
                horizontal=True,
                key="profile_mode",
            )

            profile_text = ""

            if input_mode == "upload":
                uploaded_pdf = st.file_uploader(
                    t("upload_pdf_label"),
                    type=["pdf"],
                    help=t("upload_pdf_help"),
                )
                if uploaded_pdf is not None:
                    try:
                        profile_text = extract_text_from_pdf(uploaded_pdf)
                        st.success(t("pdf_success", chars=len(profile_text)))
                    except RuntimeError as err:
                        st.error(str(err))
            else:
                profile_text = st.text_area(
                    t("profile_text_label"),
                    height=350,
                    placeholder=t("profile_text_placeholder"),
                    key="profile_text_area",
                )

    # --- Column 2: Job Description ---
    with col2:
        with st.container(border=True):
            st.subheader(t("job_description_header"))

            job_url = st.text_input(
                t("job_url_label"),
                placeholder=t("job_url_placeholder"),
                key="job_url_input",
            )

            job_description = st.text_area(
                t("job_description_label"),
                height=350,
                placeholder=t("job_description_placeholder"),
                key="jd_text_area",
            )

    return profile_text, job_description, job_url


# ---------------------------------------------------------------------------
# Results Display
# ---------------------------------------------------------------------------

def render_results(results: dict, job_url: str) -> None:
    """Render the analysis results using Streamlit components."""
    st.divider()
    st.header(t("results_header"))

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
        st.metric(label=t("compatibility_label"), value=f"{score}/100")
        st.markdown(f":{color}[**{t(quality_key)}**]")
    with progress_col:
        st.progress(score / 100, text=t("score_progress_text", score=score))

    if job_url:
        st.caption(t("job_reference_caption", url=job_url))

    st.divider()

    # --- Strengths, Gaps, Suggestions ---
    col_strengths, col_gaps, col_suggestions = st.columns(3, gap="medium")

    with col_strengths:
        with st.container(border=True):
            st.subheader(t("strengths_header"))
            for item in results.get("pontos_fortes", []):
                st.markdown(f"- {item}")

    with col_gaps:
        with st.container(border=True):
            st.subheader(t("gaps_header"))
            for item in results.get("lacunas", []):
                st.markdown(f"- {item}")

    with col_suggestions:
        with st.container(border=True):
            st.subheader(t("suggestions_header"))
            for item in results.get("sugestoes_melhoria", []):
                st.markdown(f"- {item}")

    # --- Raw JSON expander ---
    with st.expander(t("json_expander_label")):
        st.json(results)

    # --- Disclaimer ---
    st.divider()
    st.caption(t("disclaimer_text"))


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

def render_footer() -> None:
    """Render the global footer disclaimer."""
    st.divider()
    st.caption(t("footer_disclaimer"))