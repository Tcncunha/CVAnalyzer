"""
Auto Match — UI module for bulk job search + AI compatibility scoring.

Searches Adzuna for jobs matching user keywords, fetches full descriptions,
runs the AI compatibility analysis on each, and presents results ranked by
score with expandable details and one-click actions.
"""

import logging

import streamlit as st

from auto_match import run_auto_match
from i18n import prompt_language, t
from job_search import COUNTRIES, DEFAULT_COUNTRY, get_adzuna_keys
from pdf_extractor import extract_text_from_pdf
from progress_utils import run_with_progress
from providers import get_api_key, get_selected_model

log = logging.getLogger("cv-analyzer.auto_match")


def _log_progress(completed: int, total: int, job_title: str) -> None:
    """Thread-safe progress hook: logs each analyzed job (never touches UI)."""
    log.info("Analyzing job %d of %d — %s", completed, total, job_title)


# ---------------------------------------------------------------------------
# Score helpers
# ---------------------------------------------------------------------------

def _score_color(score: int) -> str:
    if score >= 75:
        return "green"
    if score >= 60:
        return "orange"
    return "red"


def _score_label_key(score: int) -> str:
    if score >= 75:
        return "score_excellent"
    if score >= 60:
        return "score_good"
    return "score_low"


# ---------------------------------------------------------------------------
# Main renderer
# ---------------------------------------------------------------------------

def render_auto_match() -> None:
    st.header(t("auto_match_header"))
    st.caption(t("auto_match_caption"))

    # --- 0. Adzuna guard ---
    try:
        app_id, app_key = get_adzuna_keys()
    except ValueError:
        st.info(t("am_no_adzuna_keys"))
        return

    # --- 1. CV Upload (US-AM-01) ---
    with st.container(border=True):
        st.subheader(t("am_cv_header"))

        default_text = st.session_state.get(
            "_last_profile",
            st.session_state.get("profile_text_area", ""),
        )

        cv_input_mode = st.radio(
            t("am_cv_source_label"),
            options=["upload", "paste"],
            format_func=lambda x: t(f"profile_mode_{x}"),
            horizontal=True,
            key="am_cv_mode",
        )

        cv_text = ""

        if cv_input_mode == "upload":
            uploaded_pdf = st.file_uploader(
                t("am_cv_upload_label"),
                type=["pdf"],
                help=t("am_cv_upload_help"),
                key="am_cv_pdf_upload",
            )
            if uploaded_pdf is not None:
                try:
                    cv_text = extract_text_from_pdf(uploaded_pdf)
                    st.success(t("am_cv_chars_loaded", count=len(cv_text)))
                except RuntimeError as err:
                    st.error(t("pdf_extract_error", error=err))
        else:
            cv_text = st.text_area(
                t("am_cv_text_label"),
                value=default_text,
                height=260,
                placeholder=t("am_cv_text_placeholder"),
                key="am_cv_text_area",
            )

        if cv_text.strip():
            st.caption(t("am_cv_chars_count", count=len(cv_text)))

    # --- 2. Preferences (US-AM-02) ---
    with st.container(border=True):
        st.subheader(t("am_preferences_header"))

        keyword = st.text_input(
            t("am_keyword_label"),
            placeholder=t("am_keyword_placeholder"),
            key="am_keyword",
        )

        col_loc, col_country = st.columns([2, 1])
        location = col_loc.text_input(
            t("am_location_label"),
            placeholder=t("am_location_placeholder"),
            key="am_location",
        )
        country = col_country.selectbox(
            t("job_search_country_label"),
            options=list(COUNTRIES.keys()),
            format_func=lambda c: COUNTRIES[c],
            index=list(COUNTRIES.keys()).index(DEFAULT_COUNTRY),
            key="am_country",
        )

        col_results, col_threshold = st.columns(2)
        results_per_page = col_results.selectbox(
            t("am_results_per_page"),
            options=[10, 20, 30, 50],
            index=1,
            key="am_results_per_page",
        )
        threshold = col_threshold.slider(
            t("am_threshold_label"),
            min_value=30,
            max_value=90,
            value=60,
            step=5,
            key="am_threshold",
        )

    # --- 3. Search + Match button (US-AM-03) ---
    st.divider()

    is_running = st.session_state.get("am_running", False)
    validation_error_shown = False

    if st.button(
        t("am_search_button"),
        type="primary",
        use_container_width=True,
        disabled=is_running,
        key="am_search_btn",
    ):
        resolved_cv = cv_text.strip()

        if not resolved_cv:
            st.error(t("am_error_no_cv"))
            validation_error_shown = True
            return
        if not keyword.strip():
            st.error(t("am_error_no_keyword"))
            validation_error_shown = True
            return

        st.session_state["am_running"] = True
        st.session_state["am_match_results"] = None

        try:
            provider = st.session_state.get("provider_select", "opencode_zen")
            model = get_selected_model()
            api_key = get_api_key(provider)
            lang = prompt_language()

            def _execute_search():
                return run_auto_match(
                    cv_text=resolved_cv,
                    keyword=keyword.strip(),
                    location=location.strip(),
                    country=country,
                    results_per_page=results_per_page,
                    threshold=threshold,
                    app_id=app_id,
                    app_key=app_key,
                    provider=provider,
                    model=model,
                    api_key=api_key,
                    language=lang,
                    progress_callback=_log_progress,
                )

            match_results = run_with_progress(
                _execute_search,
                stages=[
                    t("am_progress_searching"),
                    t("am_progress_analyzing"),
                    t("am_progress_done"),
                ],
                initial_label=t("am_progress_searching"),
            )

            st.session_state["am_match_results"] = match_results
            st.session_state["am_search_keyword"] = keyword.strip()
            st.session_state["am_threshold_used"] = threshold
            st.session_state["am_last_cv_used"] = resolved_cv
        except Exception as exc:
            log.exception("Auto Match failed")
            st.error(t("am_search_error", error=exc))
        finally:
            st.session_state["am_running"] = False

    # --- 4. Results display (US-AM-04 / US-AM-06) ---
    match_results = st.session_state.get("am_match_results")
    if not match_results:
        if not validation_error_shown:
            _render_empty_states(cv_text, keyword)
        return

    results_list = match_results.get("results", [])
    total_found = match_results.get("total_found", 0)
    total_matched = match_results.get("total_matched", 0)
    total_below = match_results.get("total_below_threshold", 0)
    total_failed = match_results.get("total_failed", 0)
    threshold_used = st.session_state.get("am_threshold_used", 60)

    st.subheader(t("am_results_header"))

    meta_parts = []
    meta_parts.append(t("am_stat_found", count=total_found))
    meta_parts.append(t("am_stat_matched", count=total_matched))
    if total_below:
        meta_parts.append(t("am_stat_below", count=total_below))
    if total_failed:
        meta_parts.append(t("am_stat_failed", count=total_failed))
    st.caption(" · ".join(meta_parts))

    if total_found == 0:
        st.info(t("am_no_results"))
        return

    if total_matched == 0 and total_failed == total_found:
        st.warning(t("am_all_failed"))
        return

    if total_matched == 0 and total_below > 0:
        st.info(t("am_none_above_threshold", threshold=threshold_used))
        if total_failed > 0:
            st.warning(t("am_partial_failure", count=total_failed))
        return

    show_all = st.checkbox(
        t("am_show_all_toggle"),
        value=False,
        key="am_show_all",
    )

    matched_results = [r for r in results_list if r.get("status") == "matched"]
    below_results = [r for r in results_list if r.get("status") == "below_threshold"]

    matched_results.sort(
        key=lambda r: r.get("analysis", {}).get("overall_score", 0) if r.get("analysis") else 0,
        reverse=True,
    )
    below_results.sort(
        key=lambda r: r.get("analysis", {}).get("overall_score", 0) if r.get("analysis") else 0,
        reverse=True,
    )

    hidden_count = 0

    for result in matched_results:
        _render_match_card(result)

    if show_all:
        for result in below_results:
            _render_match_card(result)
        hidden_count = 0
    else:
        hidden_count = len(below_results)

    if hidden_count > 0:
        st.caption(
            t("am_hidden_count", count=hidden_count, threshold=threshold_used)
        )

    if total_matched > 0 and total_failed > 0:
        st.warning(t("am_partial_failure", count=total_failed))


def _render_empty_states(cv_text: str, keyword: str) -> None:
    if not cv_text.strip():
        st.warning(t("am_empty_no_cv"))
    elif not keyword.strip():
        st.warning(t("am_empty_no_keyword"))


# ---------------------------------------------------------------------------
# Single match card (US-AM-04 / US-AM-05)
# ---------------------------------------------------------------------------

def _render_match_card(result: dict) -> None:
    job = result.get("job", {})
    analysis = result.get("analysis")

    title = job.get("title", "")
    company = job.get("company", "")
    header = f"{title} -- {company}" if company else title

    if analysis:
        score = max(0, min(100, int(analysis.get("overall_score", 0))))
        color = _score_color(score)
        label_key = _score_label_key(score)
        badge = f" :{color}[**{score}% — {t(label_key)}**]"
    else:
        badge = f" :red[*{t('am_analysis_unavailable')}*]"

    with st.expander(f"{header}{badge}"):
        meta_parts = []
        if job.get("location"):
            meta_parts.append(job["location"])
        if job.get("category"):
            meta_parts.append(job["category"])
        if job.get("salary"):
            meta_parts.append(f":green[**{job['salary']}**]")
        if job.get("created"):
            meta_parts.append(t("am_posted_date", date=job["created"]))
        if meta_parts:
            st.markdown(" · ".join(meta_parts))

        jd_source = job.get("jd_source", "")
        if jd_source == "empty":
            st.caption(t("am_jd_not_available"))
        elif jd_source == "snippet":
            st.caption(t("am_jd_partial"))

        if analysis:
            col_strengths, col_gaps = st.columns(2)
            with col_strengths:
                st.markdown(f"**{t('am_strengths_label')}**")
                for item in analysis.get("pontos_fortes", [])[:3]:
                    st.markdown(f"- {item}")
            with col_gaps:
                st.markdown(f"**{t('am_gaps_label')}**")
                for item in analysis.get("lacunas", [])[:3]:
                    st.markdown(f"- {item}")

            if analysis.get("sugestoes_melhoria"):
                with st.expander(t("am_suggestions_label")):
                    for item in analysis["sugestoes_melhoria"]:
                        st.markdown(f"- {item}")

        if job.get("full_description"):
            with st.expander(t("am_full_description_label")):
                st.markdown(job["full_description"])

        st.divider()

        col_apply, col_tailor = st.columns(2)
        with col_apply:
            job_url = job.get("url", "")
            if job_url:
                st.link_button(
                    t("am_apply_button"),
                    job_url,
                    key=f"am_apply_{job.get('id', '')}",
                    use_container_width=True,
                )
            else:
                st.button(
                    t("am_apply_button"),
                    disabled=True,
                    help=t("am_apply_no_url"),
                    key=f"am_apply_disabled_{job.get('id', '')}",
                    use_container_width=True,
                )
        with col_tailor:
            if st.button(
                t("am_tailor_button"),
                key=f"am_tailor_{job.get('id', '')}",
                use_container_width=True,
            ):
                profile_text = st.session_state.get(
                    "am_last_cv_used", st.session_state.get("_last_profile", "")
                )
                st.session_state["profile_text_area"] = profile_text
                st.session_state["_last_profile"] = profile_text
                full_jd = job.get("full_description") or job.get("description", "")
                st.session_state["jd_text_area"] = full_jd
                st.session_state["_last_jd"] = full_jd
                st.session_state["job_url_input"] = job.get("url", "")
                st.session_state["_last_job_url"] = job.get("url", "")
                st.session_state["_auto_analyze"] = True
                st.session_state["app_tabs"] = t("tab_analyzer")
                st.rerun()
