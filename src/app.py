"""
CV Analyzer -- AI-Driven Career Assistant
=========================================
Entry point. Run with:  streamlit run src/app.py
"""

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("cv-analyzer")

_SRC = str(Path(__file__).resolve().parent)
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import streamlit as st
import openai

from config import APP_ICON, ANALYSIS_PROMPT, COVER_LETTER_PROMPT, FOLLOWUP_PROMPT
from cv_builder import (
    CV_TAILOR_PROMPT,
    cv_data_to_text,
    render_cv_builder,
    render_cv_preview,
)
from cv_utils import ensure_cv_structure
from i18n import prompt_language, t
from job_fetcher import fetch_job_description
from profile_manager import save_profile
from progress_utils import run_with_progress
from providers import analyze_profile, get_api_key, get_selected_model
from tracker_manager import init_db
from ui import (
    render_footer,
    render_gap_report,
    render_header,
    render_input_columns,
    render_job_search,
    render_lgpd_banner,
    render_results,
    render_sidebar,
)


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
        model = get_selected_model()
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
            st.session_state["cv_data"] = ensure_cv_structure(raw)
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

        if st.button(
            t("reanalyze_button"), use_container_width=True,
            key="reanalyze_tailored_btn",
        ):
            cv_data = st.session_state.get("cv_data")
            if cv_data:
                reanalyze_text = cv_data_to_text(cv_data)
                st.session_state["profile_text_area"] = reanalyze_text
                st.session_state["_reanalyze_triggered"] = True
                st.rerun()


def _get_provider_and_model() -> tuple[str, str]:
    """Read the current provider/model from session state (local pattern)."""
    return (
        st.session_state.get("provider_select", "opencode_zen"),
        get_selected_model(),
    )


def _extract_plain_text(result: dict) -> str:
    """Extract a plain-text output from a (possibly JSON-wrapped) AI result.

    Cover letters / follow-up emails are requested as plain text, but some
    providers wrap them into JSON via json-mode. This helper recovers the
    text from the most likely keys and degrades gracefully.
    """
    if isinstance(result, str):
        return result.strip()
    if not isinstance(result, dict):
        return str(result)
    for key in ("letter", "email", "text", "content", "message", "output", "result"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    # Flat dict with a single string value (e.g. {"subject": ...} + body).
    string_values = [str(v).strip() for v in result.values() if isinstance(v, str) and v.strip()]
    if len(string_values) == 1:
        return string_values[0]
    return json.dumps(result, ensure_ascii=False, indent=2)


def _clipboard_copy_button(text: str, button_label: str, widget_id: str, success_label: str) -> None:
    """Render a copy-to-clipboard button (plain HTML + JS) with in-page feedback.

    `streamlit.components.v1.html` cannot trigger `st.toast`, so the JS button
    shows the localized success message inline next to the button.
    """
    import html as html_module

    safe_id = widget_id.replace("-", "_")
    js_text = json.dumps(text, ensure_ascii=False)            # JS string literal
    js_success = json.dumps(success_label, ensure_ascii=False)
    label_html = html_module.escape(button_label)

    block = f"""
    <div style="display:flex;align-items:center;gap:8px;margin:4px 0 10px 0;">
      <button onclick="cvaCopy_{safe_id}()"
        style="background:#f0f2f6;border:1px solid #d1d5db;border-radius:6px;
               padding:6px 16px;font-size:14px;cursor:pointer;color:#111827;">
        {label_html}
      </button>
      <span id="cva_{safe_id}_status" style="color:#0f766e;font-weight:600;"></span>
    </div>
    <script>
    function cvaCopy_{safe_id}() {{
      const statusEl = document.getElementById("cva_{safe_id}_status");
      const value = {js_text};
      const showDone = function () {{
        statusEl.textContent = {js_success};
        setTimeout(function () {{ statusEl.textContent = ""; }}, 2500);
      }};
      const showFail = function () {{
        statusEl.textContent = "✗";
        setTimeout(function () {{ statusEl.textContent = ""; }}, 2500);
      }};
      const legacyCopy = function () {{
        const ta = document.createElement("textarea");
        ta.value = value;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        let ok = false;
        try {{ ok = document.execCommand("copy"); }} catch (e) {{ ok = false; }}
        document.body.removeChild(ta);
        ok ? showDone() : showFail();
      }};
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(value).then(showDone, legacyCopy);
      }} else {{
        legacyCopy();
      }}
    }}
    </script>
    """
    st.components.v1.html(block, height=58, scrolling=False)


def _render_cover_letter_section() -> None:
    """Render the cover-letter generator (Analyzer tab, after results)."""
    profile = st.session_state.get("_last_profile", "")
    jd = st.session_state.get("_last_jd", "")

    # Fall back to a JD textarea when the analyzed JD is missing from session.
    if profile.strip() and not jd.strip():
        jd = st.text_area(
            t("cover_letter_jd_label"),
            placeholder=t("cover_letter_jd_placeholder"),
            height=140,
            key="cover_letter_jd_input",
        )

    if st.button(
        t("cover_letter_button"),
        use_container_width=True,
        key="cover_letter_generate_btn",
    ):
        if not profile.strip():
            st.warning(t("error_profile_empty"))
        elif not jd.strip():
            st.warning(t("error_jd_empty"))
        else:
            provider, model = _get_provider_and_model()
            try:
                api_key = get_api_key(provider)  # captured in the main thread
                lang = prompt_language()
                raw = run_with_progress(
                    lambda: analyze_profile(
                        profile,
                        jd,
                        provider,
                        model,
                        COVER_LETTER_PROMPT,
                        lang,
                        api_key=api_key,
                    ),
                    stages=[t("cover_letter_spinner")],
                    initial_label=t("cover_letter_spinner"),
                )
                st.session_state["_cover_letter"] = _extract_plain_text(raw)
            except openai.RateLimitError:
                st.error(t("error_rate_limit"))
            except Exception as exc:
                st.error(t("error_unexpected", error=exc))

    cover_letter = st.session_state.get("_cover_letter", "")
    if cover_letter:
        with st.expander(t("cover_letter_header"), expanded=True):
            st.markdown(f":green[**{t('badge_faithful_letter')}**]")
            st.code(cover_letter, language=None)
            _clipboard_copy_button(
                cover_letter,
                t("cover_letter_copy"),
                "cover_letter",
                t("cover_letter_copied"),
            )
            st.download_button(
                label=t("cover_letter_download"),
                data=cover_letter.encode("utf-8"),
                file_name="cover_letter.txt",
                mime="text/plain",
                key="cover_letter_download_btn",
            )


def _render_followup_email_section() -> None:
    """Render the follow-up email generator (Analyzer tab, after results)."""
    with st.expander(t("followup_header"), expanded=False):
        st.caption(t("followup_caption"))

        col_company, col_role = st.columns(2)
        company = col_company.text_input(
            t("followup_company"), key="followup_company_input"
        )
        role = col_role.text_input(
            t("followup_role"), key="followup_role_input"
        )

        col_days, col_situation = st.columns(2)
        days_since = col_days.number_input(
            t("followup_days"),
            min_value=0,
            value=3,
            step=1,
            key="followup_days_input",
        )
        situation = col_situation.selectbox(
            t("followup_situation"),
            options=["post_interview", "post_silence"],
            format_func=lambda opt: (
                t("followup_sit_interview")
                if opt == "post_interview"
                else t("followup_sit_silence")
            ),
            key="followup_situation_input",
        )

        if st.button(
            t("followup_generate"),
            use_container_width=True,
            key="followup_generate_btn",
        ):
            provider, model = _get_provider_and_model()
            try:
                api_key = get_api_key(provider)  # captured in the main thread
                lang = prompt_language()
                raw = run_with_progress(
                    lambda: analyze_profile(
                        "",
                        "",
                        provider,
                        model,
                        FOLLOWUP_PROMPT,
                        lang,
                        company=company.strip(),
                        role=role.strip(),
                        days_since=int(days_since),
                        situation=situation,
                        api_key=api_key,
                    ),
                    stages=[t("followup_spinner")],
                    initial_label=t("followup_spinner"),
                )
                st.session_state["_followup_email"] = _extract_plain_text(raw)
            except openai.RateLimitError:
                st.error(t("error_rate_limit"))
            except Exception as exc:
                st.error(t("error_unexpected", error=exc))

        followup_email = st.session_state.get("_followup_email", "")
        if followup_email:
            st.subheader(t("followup_result_header"))
            st.code(followup_email, language=None)
            _clipboard_copy_button(
                followup_email,
                t("followup_copy"),
                "followup",
                t("followup_copied"),
            )


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

    # Handle re-analyze from tailored CV
    if st.session_state.pop("_reanalyze_triggered", False):
        st.session_state["_auto_analyze"] = True

    # Main input area
    profile_text, job_description, job_url = render_input_columns()

    # Auto-trigger analysis when re-analyze was requested
    auto_analyze = st.session_state.pop("_auto_analyze", False)

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
            persist = not st.session_state.get("privacy_no_save", False)
            result = save_profile(identifier.strip(), payload, persist=persist)
            if persist:
                st.sidebar.success(t("profile_saved_success", name=result.name))
            else:
                st.sidebar.success(t("lgpd_no_save_active"))
            st.rerun()

    # Analyze button
    st.divider()
    analyze_clicked = st.button(
        t("analyze_button"), type="primary", use_container_width=True
    )

    if analyze_clicked or auto_analyze:
        if not profile_text.strip():
            st.error(t("error_profile_empty"))
            return

        jd = job_description.strip()

        # Auto-fetch the job description from the URL when nothing was pasted
        if not jd and job_url.strip():
            log.info("Auto-fetching JD from URL: %s", job_url.strip())
            with st.spinner(t("spinner_fetching_job")):
                try:
                    jd = fetch_job_description(job_url.strip())
                except Exception:
                    jd = ""
            if jd:
                log.info("JD fetched successfully (%d chars)", len(jd))
                st.success(t("job_fetch_success", chars=len(jd)))
            else:
                log.warning("Failed to fetch JD from URL")
                st.error(t("job_fetch_failed"))

        if not jd:
            st.error(t("error_jd_empty"))
            return

        selected_provider = st.session_state.get("provider_select", "opencode_zen")
        selected_model = get_selected_model()

        try:
            # Capture the key in the main thread (the progress worker
            # thread must not touch Streamlit session state).
            api_key = get_api_key(selected_provider)
            lang = prompt_language()  # evaluated in the main thread
            log.info(
                "Starting analysis — provider=%s model=%s lang=%s profile=%d chars jd=%d chars",
                selected_provider,
                selected_model,
                lang,
                len(profile_text),
                len(jd),
            )
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
            log.info("Analysis completed successfully — score=%s", results.get("score", "N/A"))
            st.session_state["_last_results"] = results
            st.session_state["_last_job_url"] = job_url
            st.session_state["_last_profile"] = profile_text
            st.session_state["_last_jd"] = jd
            st.session_state["last_jd"] = jd  # reusable by the STAR coach
            st.session_state["_tailored_cv_generated"] = False
        except ValueError as exc:
            log.error("Provider error: %s", exc)
            st.error(str(exc))
        except json.JSONDecodeError as exc:
            log.error("Invalid JSON response: %s", exc)
            st.error(t("error_json_invalid"))
        except openai.RateLimitError:
            log.error("Rate limit exceeded for provider=%s model=%s", selected_provider, selected_model)
            st.error(t("error_rate_limit"))
        except Exception as exc:
            log.exception("Unexpected error during analysis")
            st.error(t("error_unexpected", error=exc))

    # Keep the last analysis results visible across reruns (the widget
    # rerun caused by any click would otherwise clear them).
    if st.session_state.get("_last_results"):
        render_results(
            st.session_state["_last_results"],
            st.session_state.get("_last_job_url", ""),
        )
        _render_cover_letter_section()
        _render_followup_email_section()

    # Always render the tailored-CV offer so the button keeps working
    # on subsequent reruns (it cannot live inside the analyze block).
    _render_tailored_cv_offer()


def main():
    init_db()  # ensure the tracker DB exists (idempotent)

    st.set_page_config(page_title=t("app_title"), page_icon=APP_ICON, layout="wide")

    # --- LGPD consent gate: hard-block the first rendering until accepted ---
    if not st.session_state.get("lgpd_consent"):
        render_lgpd_banner()
        return

    render_header()

    # Sidebar is always visible (shared across tabs)
    identifier, loaded_data, selected_provider, selected_model = render_sidebar()
    st.session_state["_sidebar_identifier"] = identifier
    st.session_state["_sidebar_loaded_data"] = loaded_data

    # --- Tabs: Analyzer | CV Builder | Job Search | Tracker | STAR ---
    tab_analyzer, tab_builder, tab_job_search, tab_tracker, tab_star = st.tabs(
        [
            t("tab_analyzer"),
            t("tab_builder"),
            t("tab_job_search"),
            t("tracker_tab"),
            t("star_tab"),
        ]
    )

    with tab_analyzer:
        render_analyzer()

    with tab_builder:
        render_cv_builder()

    with tab_job_search:
        render_job_search()

    with tab_tracker:
        from tracker_ui import render_tracker_page
        render_tracker_page()

    with tab_star:
        from star_ui import render_star_page
        render_star_page()

    render_footer()


if __name__ == "__main__":
    main()
