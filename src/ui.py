"""
Streamlit UI components -- sidebar (with API key inputs), input columns,
results display, and page header.
"""

import base64
import html
import math
import os

import requests
import streamlit as st

from i18n import get_lang, LANGUAGES, set_lang, t
from job_fetcher import fetch_job_description
from job_search import COUNTRIES, DEFAULT_COUNTRY, fetch_jobs, get_adzuna_keys
from pdf_extractor import extract_text_from_pdf
from profile_manager import clear_all_profiles, list_saved_profiles, load_profile
from providers import (
    DEFAULT_MODEL,
    DEFAULT_MODEL_BY_PROVIDER,
    DEFAULT_PROVIDER,
    MODELS,
    PROVIDERS,
    is_free_zen_model,
    detect_provider_from_key,
)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

def render_header() -> None:
    """Render compact professional header bar with branding and language switcher."""
    st.markdown(
        """
        <style>
        /* ================================================================
           CVAnalyzer – Modern Job Platform Dashboard
           ================================================================ */

        /* ---------- Global ---------- */
        .block-container { padding-top: 1rem !important; max-width: 1200px !important; }
        .stApp { background-color: #f8fafc !important; }
        section[data-testid="stSidebar"] { background-color: #ffffff !important; }
        section[data-testid="stSidebar"] .stMarkdown p,
        section[data-testid="stSidebar"] label { color: #334155 !important; }

        /* ---------- Header Bar ---------- */
        .cva-header {
            display: flex; align-items: center; justify-content: space-between;
            background: #ffffff; border-radius: 14px; padding: 0.75rem 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;
            margin-bottom: 1rem;
        }
        .cva-header-brand { display: flex; align-items: center; gap: 0.75rem; }
        .cva-header-logo {
            width: 40px; height: 40px; border-radius: 10px;
            background: linear-gradient(135deg, #0f766e, #14b8a6);
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: 800; font-size: 1rem;
        }
        .cva-header-text h1 { font-size: 1.15rem; font-weight: 700; color: #0f172a; margin: 0; line-height: 1.2; }
        .cva-header-text p { font-size: 0.75rem; color: #64748b; margin: 0; }

        /* ---------- Feature Cards (Landing) ---------- */
        .cva-feat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.8rem; margin: 1rem 0; }
        .cva-feat-card {
            background: #ffffff; border-radius: 14px; padding: 1.3rem;
            border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            transition: all 0.2s ease; cursor: pointer; text-decoration: none;
        }
        .cva-feat-card:hover { box-shadow: 0 6px 16px rgba(0,0,0,0.08); transform: translateY(-3px); }
        .cva-feat-icon {
            width: 44px; height: 44px; border-radius: 12px; display: flex;
            align-items: center; justify-content: center; font-size: 1.3rem;
            margin-bottom: 0.7rem;
        }
        .cva-feat-icon-teal { background: #f0fdfa; color: #0f766e; }
        .cva-feat-icon-blue { background: #eff6ff; color: #2563eb; }
        .cva-feat-icon-purple { background: #faf5ff; color: #9333ea; }
        .cva-feat-icon-orange { background: #fff7ed; color: #ea580c; }
        .cva-feat-icon-green { background: #f0fdf4; color: #16a34a; }
        .cva-feat-icon-pink { background: #fdf2f8; color: #db2777; }
        .cva-feat-title { font-size: 0.92rem; font-weight: 700; color: #0f172a; margin: 0 0 0.25rem 0; }
        .cva-feat-desc { font-size: 0.78rem; color: #64748b; line-height: 1.45; margin: 0; }

        /* ---------- Stat Cards ---------- */
        .cva-stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.7rem; margin: 0.8rem 0; }
        .cva-stat-card {
            background: #ffffff; border-radius: 12px; padding: 0.9rem 1rem;
            border: 1px solid #e2e8f0; box-shadow: 0 1px 2px rgba(0,0,0,0.04);
            text-align: center;
        }
        .cva-stat-value { font-size: 1.5rem; font-weight: 800; color: #0f172a; }
        .cva-stat-label { font-size: 0.68rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; margin-top: 0.15rem; }

        /* ---------- Input Section ---------- */
        .cva-section-title {
            font-size: 0.92rem; font-weight: 700; color: #0f172a;
            display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.6rem;
        }
        .cva-section-badge {
            display: inline-flex; align-items: center; padding: 0.12rem 0.55rem;
            border-radius: 999px; font-size: 0.65rem; font-weight: 600;
            background: #f0fdfa; color: #0f766e; border: 1px solid #99f6e4;
        }

        /* ---------- Chips / Badges ---------- */
        .cva-chip-row { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.35rem 0 0.9rem 0; }
        .cva-chip {
            display: inline-flex; align-items: center; padding: 0.2rem 0.7rem;
            border-radius: 999px; font-size: 0.78rem; font-weight: 600;
            border: 1px solid; white-space: nowrap;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .cva-chip:hover { transform: translateY(-1px); box-shadow: 0 2px 6px rgba(0,0,0,0.08); }
        .cva-chip-green { background: #ecfdf5; border-color: #6ee7b7; color: #047857; }
        .cva-chip-red { background: #fef2f2; border-color: #fca5a5; color: #b91c1c; }

        /* ---------- List Items ---------- */
        .cva-item {
            display: flex; align-items: flex-start; gap: 0.55rem;
            padding: 0.5rem 0.75rem; margin-bottom: 0.35rem;
            background: #f8fafc; border-radius: 0 10px 10px 0;
            font-size: 0.85rem; line-height: 1.5; color: #1e293b;
            border: 1px solid #f1f5f9; transition: box-shadow 0.15s ease;
        }
        .cva-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
        .cva-item-icon { flex-shrink: 0; line-height: 1.5; }

        /* ---------- Cards / Containers ---------- */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid #e2e8f0 !important; border-radius: 12px !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
            background: #ffffff !important;
        }

        /* ---------- Expanders ---------- */
        details[data-testid="stExpander"] {
            border: 1px solid #e2e8f0 !important; border-radius: 12px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
            background: #ffffff !important; overflow: hidden;
        }
        details[data-testid="stExpander"] summary { font-weight: 600 !important; color: #0f766e !important; }
        details[data-testid="stExpander"]:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important; }

        /* ---------- Buttons ---------- */
        .stButton > button {
            border-radius: 10px !important; font-weight: 600 !important;
            transition: all 0.2s ease !important; border: none !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
        }
        .stButton > button:hover { box-shadow: 0 4px 12px rgba(15,118,110,0.3) !important; transform: translateY(-1px) !important; }
        .stButton > button:active { transform: translateY(0) !important; }
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="stBaseButton-primary"] {
            background: linear-gradient(135deg, #0f766e, #0d9488) !important;
            color: #ffffff !important;
        }

        /* ---------- Inputs ---------- */
        .stTextInput > div > div > input, .stTextArea > div > div > textarea {
            border-radius: 10px !important; border: 1.5px solid #e2e8f0 !important;
            background: #ffffff !important; color: #1e293b !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }
        .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {
            border-color: #0f766e !important;
            box-shadow: 0 0 0 3px rgba(15,118,110,0.12) !important;
        }
        .stTextInput > div > div > input::placeholder,
        .stTextArea > div > div > textarea::placeholder { color: #94a3b8 !important; }

        /* ---------- Select Boxes ---------- */
        .stSelectbox > div > div { border-radius: 10px !important; border: 1.5px solid #e2e8f0 !important; background: #ffffff !important; }
        .stSelectbox > div > div:focus-within { border-color: #0f766e !important; box-shadow: 0 0 0 3px rgba(15,118,110,0.12) !important; }

        /* ---------- File Uploader ---------- */
        section[data-testid="stFileUploadDropzone"] {
            border-radius: 12px !important; border: 2px dashed #cbd5e1 !important;
            background: #f8fafc !important; transition: all 0.2s ease !important;
        }
        section[data-testid="stFileUploadDropzone"]:hover {
            border-color: #0f766e !important; background: #f0fdfa !important;
        }

        /* ---------- Progress Bars ---------- */
        .stProgress > div > div { border-radius: 8px !important; background: #e2e8f0 !important; }
        .stProgress > div > div > div { border-radius: 8px !important; background: linear-gradient(90deg, #0f766e, #14b8a6) !important; }

        /* ---------- Dividers / Misc ---------- */
        hr { border: none !important; border-top: 1px solid #e2e8f0 !important; margin: 1rem 0 !important; }
        .stCaption, p.caption { color: #64748b !important; }
        h2, h3 { color: #0f172a !important; }
        a { color: #0f766e !important; text-decoration: none !important; }
        a:hover { color: #0d9488 !important; text-decoration: underline !important; }

        /* ---------- Tabs ---------- */
        .stTabs [data-baseweb="tab-list"] { gap: 0.3rem; }
        .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; font-weight: 600; font-size: 0.85rem; }
        .stTabs [aria-selected="true"] { background: #f0fdfa !important; color: #0f766e !important; }

        /* ---------- Sidebar Expander ---------- */
        section[data-testid="stSidebar"] details[data-testid="stExpander"] {
            border: 1px solid #e2e8f0 !important; border-radius: 10px !important;
            background: #f8fafc !important;
        }
        section[data-testid="stSidebar"] .stButton > button { border-radius: 10px !important; }

        /* ---------- Info/Warning/Error ---------- */
        .element-container div[data-testid="stInfo"] { border-radius: 12px !important; border-left: 4px solid #0f766e !important; }
        .element-container div[data-testid="stWarning"] { border-radius: 12px !important; }
        .element-container div[data-testid="stError"] { border-radius: 12px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _render_main_banner()

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


def _render_main_banner() -> None:
    """Render compact header bar with branding."""
    banner_path = os.path.join(os.path.dirname(__file__), "img", "MainBanner.png")
    try:
        with open(banner_path, "rb") as fh:
            banner_b64 = base64.b64encode(fh.read()).decode("ascii")
    except OSError:
        banner_b64 = ""

    if banner_b64:
        st.markdown(
            f"""
            <div class="cva-header">
                <div class="cva-header-brand">
                    <img src="data:image/png;base64,{banner_b64}"
                         style="width:40px;height:40px;border-radius:10px;object-fit:cover;"
                         alt="logo">
                    <div class="cva-header-text">
                        <h1>{html.escape(t("app_title"))}</h1>
                        <p>{html.escape(t("app_caption"))}</p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="cva-header">
                <div class="cva-header-brand">
                    <div class="cva-header-logo">CV</div>
                    <div class="cva-header-text">
                        <h1>{html.escape(t("app_title"))}</h1>
                        <p>{html.escape(t("app_caption"))}</p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_landing_cards() -> None:
    """Render dashboard-style feature cards for the landing page."""
    st.markdown(
        """
        <div class="cva-feat-grid">
            <div class="cva-feat-card">
                <div class="cva-feat-icon cva-feat-icon-teal">🎯</div>
                <div class="cva-feat-title">CV Analyzer</div>
                <div class="cva-feat-desc">Analyze your profile against job descriptions with AI-powered compatibility scoring.</div>
            </div>
            <div class="cva-feat-card">
                <div class="cva-feat-icon cva-feat-icon-blue">📝</div>
                <div class="cva-feat-title">CV Builder</div>
                <div class="cva-feat-desc">Generate tailored, ATS-optimized resumes in DOCX, PDF, or HTML formats.</div>
            </div>
            <div class="cva-feat-card">
                <div class="cva-feat-icon cva-feat-icon-purple">🔍</div>
                <div class="cva-feat-title">Job Search</div>
                <div class="cva-feat-desc">Find real job listings from Adzuna across multiple countries and categories.</div>
            </div>
            <div class="cva-feat-card">
                <div class="cva-feat-icon cva-feat-icon-orange">⚡</div>
                <div class="cva-feat-title">Auto Match</div>
                <div class="cva-feat-desc">Automatically match your profile against multiple vacancies at once.</div>
            </div>
            <div class="cva-feat-card">
                <div class="cva-feat-icon cva-feat-icon-green">📊</div>
                <div class="cva-feat-title">Tracker</div>
                <div class="cva-feat-desc">Track your job applications, status, and follow-ups in one place.</div>
            </div>
            <div class="cva-feat-card">
                <div class="cva-feat-icon cva-feat-icon-pink">🎭</div>
                <div class="cva-feat-title">STAR Coach</div>
                <div class="cva-feat-desc">Practice behavioral interview questions using the STAR method with AI feedback.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# LGPD Consent Banner
# ---------------------------------------------------------------------------

def render_lgpd_banner() -> None:
    """Render the LGPD privacy/consent gate that blocks the app until accepted."""
    st.markdown(f"### {t('lgpd_header')}")
    st.info(t("lgpd_text"))

    st.checkbox(
        t("lgpd_dont_save"),
        value=False,
        key="privacy_no_save",
        help=t("lgpd_dont_save_help"),
    )

    if st.button(t("lgpd_accept"), type="primary", use_container_width=True):
        st.session_state["lgpd_consent"] = True
        st.rerun()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar() -> tuple[str, dict | None, str, str]:
    """Render sidebar controls and return (identifier, loaded_data, provider, model).

    When a provider requires an API key, a password input is shown. The key
    lives only in Streamlit session state and is never written to disk.
    """
    with st.sidebar:
        with st.expander(t("sidebar_settings_header"), expanded=True):
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
                def _on_api_change(p=selected_provider):
                    sk = f"api_key_{p}"
                    pasted = (st.session_state.get(f"api_key_w_{p}", "") or "").strip()
                    st.session_state[sk] = pasted
                    detected = detect_provider_from_key(pasted)
                    if detected and detected != p and detected in PROVIDERS:
                        # The pasted key belongs to another provider: switch to it
                        # automatically and carry the key + default model over.
                        st.session_state["provider_select"] = detected
                        st.session_state[f"api_key_w_{detected}"] = pasted
                        st.session_state[f"api_key_{detected}"] = pasted
                        default_model = DEFAULT_MODEL_BY_PROVIDER.get(
                            detected, DEFAULT_MODEL
                        )
                        if default_model in MODELS.get(detected, {}):
                            st.session_state[f"model_select_{detected}"] = default_model

                api_key = st.text_input(
                    t("api_key_label"),
                    type="password",
                    placeholder=t("api_key_placeholder"),
                    key=f"api_key_w_{selected_provider}",
                    on_change=_on_api_change,
                )

                st.caption(t("api_key_info"))

                detected = detect_provider_from_key(api_key)
                if detected and detected in PROVIDERS:
                    st.success(t("api_key_detected", provider=PROVIDERS[detected]["name"]))

                if not api_key.strip():
                    st.warning(t("api_key_required"))

            # --- Model selector (dynamic based on provider) ---
            model_dict = MODELS.get(selected_provider, {})
            model_keys = list(model_dict.keys())
            default_model = DEFAULT_MODEL_BY_PROVIDER.get(selected_provider, DEFAULT_MODEL)
            default_model_idx = (
                model_keys.index(default_model) if default_model in model_keys else 0
            )

            selected_model = st.selectbox(
                t("model_label"),
                options=model_keys,
                format_func=lambda k: model_dict[k],
                index=default_model_idx,
                key=f"model_select_{selected_provider}",
            )

            # --- Provider disclaimer ---
            provider_name = PROVIDERS.get(selected_provider, {}).get(
                "name", selected_provider
            )
            st.caption(f"{t('provider_disclaimer')} — **{provider_name}**")

        st.divider()

        with st.expander(t("lgpd_header"), expanded=False):
            if "_lgpd_notice" in st.session_state:
                st.success(st.session_state.pop("_lgpd_notice"))

            st.checkbox(
                t("lgpd_dont_save"),
                value=st.session_state.get("privacy_no_save", False),
                key="privacy_no_save",
                help=t("lgpd_dont_save_help"),
            )

            # --- Clear data flow (two-step confirm) ---
            clear_arm = st.checkbox(
                t("lgpd_clear_confirm"),
                key="lgpd_clear_arm",
                value=False,
            )
            if st.button(
                t("lgpd_clear_button"),
                use_container_width=True,
                disabled=not clear_arm,
            ):
                # Clear tracked session-state data keys
                _privacy_keys = [
                    "profile_text_area",
                    "jd_text_area",
                    "job_url_input",
                    "cv_data",
                    "cv_built",
                    "_last_results",
                    "_last_job_url",
                    "_last_profile",
                    "_last_jd",
                    "last_jd",
                    "_cover_letter",
                    "_followup_email",
                    "_tailored_cv_generated",
                    "cv_profile_text",
                    "cv_data_uploaded",
                    "_job_results",
                    "_job_count",
                    "star_questions",
                    "star_idx",
                    "star_results",
                    "star_jd_fallback",
                    "_tracker_notice",
                ]
                for key in _privacy_keys:
                    if key in st.session_state:
                        del st.session_state[key]

                cleared_profiles = clear_all_profiles()

                # Clear tracker data
                from tracker_manager import clear_all as clear_all_tracker
                clear_all_tracker()

                # Show confirmation on the next rerun (widget state cannot be
                # mutated after instantiation in the same run).
                st.session_state["_lgpd_notice"] = t("lgpd_cleared")
                st.rerun()

        st.divider()

        # --- Adzuna keys (Job Search tab) ---
        with st.expander(t("job_search_keys_header")):
            st.caption(t("job_search_keys_hint"))
            st.text_input(
                t("job_search_app_id_label"),
                placeholder="0000000000000000",
                key="adzuna_app_id_w",
            )
            st.text_input(
                t("job_search_app_key_label"),
                type="password",
                placeholder="0000000000000000",
                key="adzuna_app_key_w",
            )

        st.divider()

        with st.expander(t("profile_mgmt_header"), expanded=False):
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

            profile_text = ""

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
                    st.error(t("pdf_extract_error", error=err))

            with st.expander(t("linkedin_tutorial_header"), expanded=not profile_text):
                st.markdown(f"""
                {t("linkedin_tutorial_step1")}

                {t("linkedin_tutorial_step2")}

                {t("linkedin_tutorial_step3")}

                {t("linkedin_tutorial_step4")}

                > {t("linkedin_tutorial_tip")}
                """)

    # --- Column 2: Job Description ---
    with col2:
        with st.container(border=True):
            st.subheader(t("job_description_header"))

            job_url = st.text_input(
                t("job_url_label"),
                placeholder=t("job_url_placeholder"),
                key="job_url_input",
            )

            st.caption(t("job_url_hint"))

            if job_url.strip():
                if st.button(
                    t("job_fetch_button"),
                    key="fetch_job_btn",
                    use_container_width=True,
                ):
                    with st.spinner(t("spinner_fetching_job")):
                        try:
                            fetched = fetch_job_description(job_url.strip())
                        except Exception:
                            fetched = ""
                    if fetched:
                        st.session_state["jd_text_area"] = fetched
                        st.rerun()
                    else:
                        st.error(t("job_fetch_failed"))

            job_description = st.text_area(
                t("job_description_label"),
                height=350,
                placeholder=t("job_description_placeholder"),
                key="jd_text_area",
            )

    return profile_text, job_description, job_url


# ---------------------------------------------------------------------------
# Job Search
# ---------------------------------------------------------------------------

def _render_job_card(job: dict) -> None:
    """Render a single job result; the button sends its JD to the Analyzer."""
    header = f"{job['title']} – {job['company']}" if job["company"] else job["title"]
    with st.expander(header):
        meta_parts = [x for x in (job["location"], job["category"]) if x]
        if job["salary"]:
            meta_parts.append(f":green[**{job['salary']}**]")
        if job["created"]:
            meta_parts.append(t("job_search_posted", date=job["created"]))
        if meta_parts:
            st.markdown(" · ".join(meta_parts))
        st.markdown(job["description"])

        col_use, col_link = st.columns(2)
        with col_use:
            if st.button(
                t("job_search_use_button"),
                type="primary",
                key=f"use_job_{job['id']}",
                use_container_width=True,
            ):
                if not job["url"]:
                    st.error(t("job_fetch_failed"))
                else:
                    with st.spinner(t("spinner_fetching_job")):
                        try:
                            jd = fetch_job_description(job["url"])
                        except Exception:
                            jd = ""
                    if jd:
                        st.session_state["jd_text_area"] = jd
                        st.session_state["job_url_input"] = job["url"]
                        st.session_state["_last_job_url"] = job["url"]
                        st.success(t("job_search_use_success"))
                    else:
                        st.error(t("job_fetch_failed"))
        with col_link:
            if job["url"]:
                st.link_button(
                    t("job_search_open"),
                    job["url"],
                    key=f"open_job_{job['id']}",
                    use_container_width=True,
                )


def render_job_search() -> None:
    """Render the Job Search tab (Adzuna-powered)."""
    st.header(t("job_search_header"))
    st.caption(t("job_search_caption"))

    try:
        app_id, app_key = get_adzuna_keys()
    except ValueError:
        st.info(t("job_search_no_keys"))
        return

    with st.container(border=True):
        st.subheader(t("job_search_config_header"))
        keyword = st.text_input(
            t("job_search_keyword_label"),
            placeholder=t("job_search_keyword_placeholder"),
            key="job_kw",
        )
        col_loc, col_cnt, col_res = st.columns([2, 1, 1])
        location = col_loc.text_input(
            t("job_search_location_label"),
            placeholder=t("job_search_location_placeholder"),
            key="job_loc",
        )
        country = col_cnt.selectbox(
            t("job_search_country_label"),
            options=list(COUNTRIES.keys()),
            format_func=lambda c: COUNTRIES[c],
            index=list(COUNTRIES.keys()).index(DEFAULT_COUNTRY),
            key="job_country",
        )
        results_per_page = col_res.selectbox(
            t("job_search_results_label"),
            options=[10, 20, 30, 50],
            index=1,
            key="job_results_n",
        )
        search_clicked = st.button(
            t("job_search_button"), type="primary", use_container_width=True
        )

    if search_clicked:
        if not keyword.strip():
            st.warning(t("job_search_keyword_required"))
        else:
            try:
                with st.spinner(t("job_search_spinner")):
                    jobs, count = fetch_jobs(
                        keyword.strip(),
                        location,
                        country,
                        results_per_page,
                        app_id,
                        app_key,
                    )
                st.session_state["_job_results"] = jobs
                st.session_state["_job_count"] = count
            except Exception as exc:
                st.error(t("job_search_error", error=exc))

    # Keep the last results visible across reruns (any click triggers one).
    jobs = st.session_state.get("_job_results", [])
    count = st.session_state.get("_job_count", 0)

    if search_clicked and not jobs:
        st.info(t("job_search_no_results"))

    if jobs:
        st.caption(t("job_search_count", count=count, shown=len(jobs)))
        for job in jobs:
            _render_job_card(job)


# ---------------------------------------------------------------------------
# Results Display
# ---------------------------------------------------------------------------

_SCORE_COLOR_HEX = {"green": "#22c55e", "orange": "#f59e0b", "red": "#ef4444"}


def _render_score_gauge(score: int, color: str, quality_label: str) -> None:
    """Render a circular score gauge (SVG) next to the quality label."""
    radius = 46
    circumference = 2 * math.pi * radius
    filled = circumference * score / 100
    hex_color = _SCORE_COLOR_HEX.get(color, "#22c55e")

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:1.5rem;padding:0.6rem 0 0.8rem 0;
            background:#ffffff;border-radius:12px;border:1px solid #e2e8f0;
            box-shadow:0 1px 3px rgba(0,0,0,0.06);padding:1rem 1.2rem;">
            <svg width="110" height="110" viewBox="0 0 110 110" style="flex-shrink:0;">
                <circle cx="55" cy="55" r="{radius}" fill="none"
                    stroke="#e2e8f0" stroke-width="10"/>
                <circle cx="55" cy="55" r="{radius}" fill="none"
                    stroke="{hex_color}" stroke-width="10" stroke-linecap="round"
                    stroke-dasharray="{filled:.1f} {circumference:.1f}"
                    transform="rotate(-90 55 55)"/>
                <text x="55" y="61" text-anchor="middle" font-size="24"
                    font-weight="800" fill="#1e293b">{score}</text>
            </svg>
            <div>
                <div style="font-size:0.78rem;color:#64748b;
                    text-transform:uppercase;letter-spacing:0.05em;font-weight:600;">
                    {html.escape(t("compatibility_label"))}
                </div>
                <div style="font-size:1.35rem;font-weight:800;color:{hex_color};margin-top:2px;">
                    {html.escape(quality_label)}
                </div>
                <div style="font-size:0.85rem;color:#94a3b8;margin-top:4px;">
                    {score}/100
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_list_items(items: list, icon: str, accent_hex: str) -> None:
    """Render strings as icon-accented item cards (mirrors the STAR feedback style)."""
    for item in items:
        safe = html.escape(str(item))
        st.markdown(
            f"""
            <div class="cva-item" style="border-left:3px solid {accent_hex};">
                <span class="cva-item-icon">{icon}</span>
                <span>{safe}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


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

    _render_score_gauge(score, color, t(quality_key))

    if job_url:
        st.caption(t("job_reference_caption", url=job_url))

    # --- ATS Gap Report (right after the score block, before the
    # strengths/gaps/suggestions columns) ---
    render_gap_report(results)

    st.divider()

    # --- Strengths, Gaps, Suggestions ---
    col_strengths, col_gaps, col_suggestions = st.columns(3, gap="medium")

    with col_strengths:
        with st.container(border=True):
            st.subheader(t("strengths_header"))
            _render_list_items(results.get("pontos_fortes", []), "✅", "#22c55e")

    with col_gaps:
        with st.container(border=True):
            st.subheader(t("gaps_header"))
            _render_list_items(results.get("lacunas", []), "⚠️", "#f59e0b")

    with col_suggestions:
        with st.container(border=True):
            st.subheader(t("suggestions_header"))
            _render_list_items(results.get("sugestoes_melhoria", []), "💡", "#60a5fa")

    # --- Raw JSON expander ---
    with st.expander(t("json_expander_label")):
        st.json(results)

    # --- Disclaimer ---
    st.divider()
    st.caption(t("disclaimer_text"))


# ---------------------------------------------------------------------------
# ATS Gap Report
# ---------------------------------------------------------------------------

def _render_keyword_chips(keywords: list, color: str) -> None:
    """Render a wrapping row of keyword pill badges with their category."""
    css_class = "cva-chip-green" if color == "green" else "cva-chip-red"
    chips_html = []
    for item in keywords:
        keyword = item.get("keyword", "") if isinstance(item, dict) else str(item)
        category = item.get("category", "") if isinstance(item, dict) else ""
        if not keyword:
            continue
        label = f"{keyword} ({category})" if category else keyword
        safe_label = html.escape(label)
        chips_html.append(f'<span class="cva-chip {css_class}">{safe_label}</span>')
    if chips_html:
        st.markdown(
            f'<div class="cva-chip-row">{"".join(chips_html)}</div>',
            unsafe_allow_html=True,
        )


def render_gap_report(results: dict) -> None:
    """Render the ATS keyword gap report from analysis results (graceful)."""
    kw = results.get("keyword_analysis")
    if not kw or not isinstance(kw, dict):
        return

    st.divider()
    st.header(t("gap_report_header"))
    st.caption(t("gap_report_subtitle"))

    # Category score bars
    category_scores = kw.get("category_scores", {}) or {}
    categories = [
        ("hard_skills", "gap_report_hard"),
        ("soft_skills", "gap_report_soft"),
        ("tools", "gap_report_tools"),
        ("certifications", "gap_report_certs"),
    ]
    for cat_key, label_key in categories:
        raw = category_scores.get(cat_key, 0)
        try:
            score = int(float(raw if raw is not None else 0))
        except (TypeError, ValueError):
            score = 0
        score = max(0, min(100, score))
        st.progress(score / 100.0, text=f"{t(label_key)}: {score}%")

    matched = kw.get("matched_keywords", []) or []
    missing = kw.get("missing_keywords", []) or []
    if not isinstance(matched, list):
        matched = []
    if not isinstance(missing, list):
        missing = []

    if not matched and not missing:
        st.caption(t("gap_report_no_data"))
        return

    if matched:
        st.markdown(f"**{t('gap_report_matched')}**")
        _render_keyword_chips(matched, "green")

    if missing:
        st.markdown(f"**{t('gap_report_missing')}**")
        _render_keyword_chips(missing, "red")


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

def render_footer() -> None:
    """Render the global footer disclaimer."""
    st.divider()
    st.caption(t("footer_disclaimer"))
    st.divider()
    st.caption(t("footer_credit"))
