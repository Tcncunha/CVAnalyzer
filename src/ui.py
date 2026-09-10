"""
Streamlit UI components -- sidebar (with API key inputs), input columns,
results display, and page header.
"""

import base64
import html
import math
import os

import streamlit as st

from i18n import get_lang, LANGUAGES, set_lang, t
from job_fetcher import fetch_job_description
from job_providers import CASCADE_ORDER, run_cascade
from job_search import COUNTRIES, DEFAULT_COUNTRY, fetch_jobs, get_adzuna_keys
from pdf_extractor import extract_text_from_upload
from profile_manager import clear_all_profiles, list_saved_profiles, load_profile
from providers import (
    DEFAULT_MODEL,
    DEFAULT_MODEL_BY_PROVIDER,
    DEFAULT_PROVIDER,
    MODELS,
    PROVIDERS,
    detect_provider_from_key,
)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

def render_header() -> None:
    """Render the main brand banner (wide strip) with a compact language switcher."""
    st.markdown(
        """
        <style>
        .cva-banner {
            width: 100%;
            height: 200px;
            object-fit: cover;
            object-position: center center;
            display: block;
            border-radius: 14px;
            box-shadow: 0 12px 28px -12px rgba(2, 12, 27, 0.55);
        }
        .cva-lang-row {
            display: flex;
            justify-content: flex-end;
            margin-top: 0.4rem;
        }
        .cva-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
            margin: 0.35rem 0 0.9rem 0;
        }
        .cva-chip {
            display: inline-flex;
            align-items: center;
            padding: 0.18rem 0.75rem;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 600;
            border: 1px solid;
            white-space: nowrap;
        }
        .cva-chip-green {
            background: rgba(34, 197, 94, 0.12);
            border-color: rgba(34, 197, 94, 0.5);
            color: #4ade80;
        }
        .cva-chip-red {
            background: rgba(239, 68, 68, 0.12);
            border-color: rgba(239, 68, 68, 0.5);
            color: #f87171;
        }
        .cva-item {
            display: flex;
            align-items: flex-start;
            gap: 0.55rem;
            padding: 0.45rem 0.7rem;
            margin-bottom: 0.4rem;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 0 8px 8px 0;
            font-size: 0.92rem;
            line-height: 1.45;
        }
        .cva-item-icon {
            flex-shrink: 0;
            line-height: 1.45;
        }
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
    """Embed the MainBanner image (base64) as a wide hero strip at the top."""
    banner_path = os.path.join(os.path.dirname(__file__), "img", "MainBanner.png")
    try:
        with open(banner_path, "rb") as fh:
            banner_b64 = base64.b64encode(fh.read()).decode("ascii")
    except OSError:
        banner_b64 = ""
    if banner_b64:
        st.markdown(
            f'<img class="cva-banner" src="data:image/png;base64,{banner_b64}" '
            f'alt="{t("app_title")}" '
            'style="width:100%;height:200px;object-fit:cover;object-position:center center;'
            'display:block;border-radius:14px;" />',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f"### {t('app_title')}")


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
                    "_cascade_result",
                    "_cascade_target_used",
                    "_cascade_calls_accum",
                    "star_questions",
                    "star_idx",
                    "star_results",
                    "star_jd_fallback",
                    "_tracker_notice",
                ]
                for key in _privacy_keys:
                    if key in st.session_state:
                        del st.session_state[key]

                clear_all_profiles()

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

        # --- Optional cascade provider keys (session-only) ---
        if st.session_state.get("_cascade_mode"):
            with st.expander(t("cascade_keys_header"), expanded=False):
                st.caption(t("cascade_keys_hint"))
                st.text_input(
                    t("cascade_serpapi_key_label"),
                    type="password",
                    key="serpapi_key_w",
                )
                st.text_input(
                    t("cascade_jooble_key_label"),
                    type="password",
                    key="jooble_key_w",
                )
                st.text_input(
                    t("cascade_usajobs_key_label"),
                    type="password",
                    key="usajobs_key_w",
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
                    type=["pdf", "html", "htm"],
                    help=t("upload_pdf_help"),
                )
                if uploaded_pdf is not None:
                    try:
                        profile_text = extract_text_from_upload(uploaded_pdf)
                        st.success(t("pdf_success", chars=len(profile_text)))
                    except RuntimeError as err:
                        st.error(t("pdf_extract_error", error=err))
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

def _source_display_name(source: str) -> str:
    """Return the localized display name for a job source (falls back to raw)."""
    if not source:
        return ""
    if source == "serpapi":
        return t("cascade_source_google_jobs")
    label = t(f"cascade_source_{source}")
    if label.startswith("cascade_source_"):
        return str(source)
    return label


def _job_card_key(prefix: str, job: dict, card_index: int) -> str:
    """Build a unique widget key per rendered job card (source-namespaced)."""
    source = job.get("source", "")
    job_id = job.get("id") or ""
    id_part = f"{source}_{job_id}" if job_id else f"idx_{card_index}"
    return f"{prefix}_{id_part}"


def _render_job_card(job: dict, card_index: int) -> None:
    """Render a single job result; the button sends its JD to the Analyzer."""
    header = f"{job['title']} – {job['company']}" if job["company"] else job["title"]
    with st.expander(header):
        source = job.get("source", "")
        if source:
            badge_html = (
                f'<span class="cva-chip cva-chip-green">'
                f'{html.escape(_source_display_name(source))}</span>'
            )
            st.markdown(badge_html, unsafe_allow_html=True)
        meta_parts = [x for x in (job["location"], job["category"]) if x]
        if job["salary"]:
            meta_parts.append(f":green[**{job['salary']}**]")
        if job["created"]:
            meta_parts.append(t("job_search_posted", date=job["created"]))
        if meta_parts:
            st.markdown(" · ".join(meta_parts))
        st.markdown(job["description"])

        btn_key = _job_card_key("use_job", job, card_index)
        open_btn_key = _job_card_key("open_job", job, card_index)
        col_use, col_link = st.columns(2)
        with col_use:
            if st.button(
                t("job_search_use_button"),
                type="primary",
                key=btn_key,
                use_container_width=True,
            ):
                if not job.get("url"):
                    st.error(t("cascade_error_no_link"))
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
            if job.get("url"):
                st.link_button(
                    t("job_search_open"),
                    job["url"],
                    key=open_btn_key,
                    use_container_width=True,
                )


def _render_cascade_messages(result: dict, target: int) -> None:
    """Render cascade error/coverage notices (US-15) close to the results."""
    jobs = result.get("jobs", [])
    errors = {k: v for k, v in (result.get("errors") or {}).items() if v}
    reached_target = bool(result.get("reached_target"))

    if not jobs:
        if errors:
            st.error(t("cascade_error_all_sources"))
        return
    if not errors:
        return

    failed_names = " · ".join(errors.keys())
    if reached_target:
        st.warning(t("cascade_error_partial_reached", sources=failed_names))
    else:
        st.warning(
            t(
                "cascade_error_partial_not_reached",
                found=len(jobs),
                target=target,
                sources=failed_names,
            )
        )


def render_job_search() -> None:
    """Render the Job Search tab (Adzuna-powered, with optional cascade mode)."""
    st.header(t("job_search_header"))
    st.caption(t("job_search_caption"))

    cascade_mode = st.session_state.get("_cascade_mode", False)
    if not cascade_mode and st.session_state.get("_cascade_result") is not None:
        st.session_state["_cascade_result"] = None

    try:
        app_id, app_key = get_adzuna_keys()
    except ValueError:
        if not cascade_mode and not st.session_state.get("_job_results"):
            st.info(t("job_search_no_keys"))
            return
        st.info(t("job_search_no_keys"))
        app_id, app_key = "", ""

    with st.container(border=True):
        st.subheader(t("job_search_config_header"))
        cascade_mode = st.toggle(
            t("cascade_toggle_label"),
            value=cascade_mode,
            help=t("cascade_toggle_help"),
            key="_cascade_mode",
        )
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
        if cascade_mode:
            cascade_target = st.selectbox(
                t("cascade_target_label"),
                options=[10, 20, 30, 50],
                index=1,
                key="_cascade_target",
            )
        else:
            cascade_target = results_per_page
        search_clicked = st.button(
            t("job_search_button"), type="primary", use_container_width=True
        )

    if search_clicked:
        if not keyword.strip():
            st.warning(t("job_search_keyword_required"))
        else:
            try:
                with st.spinner(t("job_search_spinner")):
                    if cascade_mode:
                        cascade_config = {
                            "query": keyword.strip(),
                            "location": location,
                            "country": country,
                            "results_per_page": cascade_target,
                            "adzuna_app_id": (
                                st.session_state.get("adzuna_app_id", "")
                                or st.session_state.get("adzuna_app_id_w", "")
                            ),
                            "adzuna_app_key": (
                                st.session_state.get("adzuna_app_key", "")
                                or st.session_state.get("adzuna_app_key_w", "")
                            ),
                            "serpapi_api_key": st.session_state.get(
                                "serpapi_key_w", ""
                            ),
                            "jooble_api_key": st.session_state.get("jooble_key_w", ""),
                            "usajobs_api_key": st.session_state.get(
                                "usajobs_key_w", ""
                            ),
                        }
                        cascade_result = run_cascade(cascade_config, cascade_target)
                        jobs = cascade_result.get("jobs", [])
                        count = len(jobs)
                        st.session_state["_cascade_result"] = cascade_result
                        st.session_state["_cascade_target_used"] = cascade_target
                        run_calls = cascade_result.get("calls") or {}
                        if run_calls:
                            accumulated_calls = st.session_state.get(
                                "_cascade_calls_accum", {}
                            )
                            for src_name, call_count in run_calls.items():
                                accumulated_calls[src_name] = (
                                    accumulated_calls.get(src_name, 0) + call_count
                                )
                            st.session_state[
                                "_cascade_calls_accum"
                            ] = accumulated_calls
                    else:
                        jobs, count = fetch_jobs(
                            keyword.strip(),
                            location,
                            country,
                            results_per_page,
                            app_id,
                            app_key,
                        )
                        st.session_state["_cascade_result"] = None
                st.session_state["_job_results"] = jobs
                st.session_state["_job_count"] = count
            except Exception as exc:
                st.error(t("job_search_error", error=exc))

    # Keep the last results visible across reruns (any click triggers one).
    jobs = st.session_state.get("_job_results", [])
    count = st.session_state.get("_job_count", 0)
    if cascade_mode:
        cascade_result = st.session_state.get("_cascade_result")
        accumulated_calls = st.session_state.get("_cascade_calls_accum") or {}
    else:
        cascade_result = None
        accumulated_calls = {}

    if search_clicked and not jobs:
        st.info(t("job_search_no_results"))

    if cascade_result:
        target_used = st.session_state.get("_cascade_target_used", 20)
        _render_cascade_messages(cascade_result, target_used)

    if jobs:
        st.caption(t("job_search_count", count=count, shown=len(jobs)))
        for idx, job in enumerate(jobs):
            _render_job_card(job, idx)

        coverage = (cascade_result or {}).get("coverage") or {}
        if coverage:
            coverage_parts = [
                t(
                    "cascade_coverage_item",
                    source=_source_display_name(src),
                    count=n,
                )
                for src, n in coverage.items()
                if n
            ]
            if coverage_parts:
                st.caption(
                    f"{t('cascade_coverage_label')}: {' · '.join(coverage_parts)}"
                )

        if not cascade_result or coverage.get("adzuna"):
            st.caption(t("job_search_adzuna_credit"))

        calls = accumulated_calls
        if calls:
            with st.expander(t("cascade_calls_header")):
                for provider_cls in CASCADE_ORDER:
                    src = provider_cls.source
                    n = calls.get(src, 0)
                    if n:
                        if src == "jooble":
                            st.caption(
                                t(
                                    "cascade_jooble_quota",
                                    source=_source_display_name(src),
                                    count=n,
                                )
                            )
                            st.caption(t("cascade_jooble_quota_hint"))
                        else:
                            st.caption(
                                t(
                                    "cascade_calls_item",
                                    source=_source_display_name(src),
                                    count=n,
                                )
                            )


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
        <div style="display:flex;align-items:center;gap:1.5rem;padding:0.4rem 0 0.6rem 0;">
            <svg width="110" height="110" viewBox="0 0 110 110" style="flex-shrink:0;">
                <circle cx="55" cy="55" r="{radius}" fill="none"
                    stroke="rgba(255,255,255,0.10)" stroke-width="10"/>
                <circle cx="55" cy="55" r="{radius}" fill="none"
                    stroke="{hex_color}" stroke-width="10" stroke-linecap="round"
                    stroke-dasharray="{filled:.1f} {circumference:.1f}"
                    transform="rotate(-90 55 55)"/>
                <text x="55" y="61" text-anchor="middle" font-size="24"
                    font-weight="800" fill="#ffffff">{score}</text>
            </svg>
            <div>
                <div style="font-size:0.8rem;color:rgba(255,255,255,0.6);
                    text-transform:uppercase;letter-spacing:0.04em;">
                    {html.escape(t("compatibility_label"))}
                </div>
                <div style="font-size:1.35rem;font-weight:800;color:{hex_color};margin-top:2px;">
                    {html.escape(quality_label)}
                </div>
                <div style="font-size:0.85rem;color:rgba(255,255,255,0.55);margin-top:4px;">
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
