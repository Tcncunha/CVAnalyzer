"""
CV Builder page -- parse a LinkedIn / profile text into structured data,
optionally enhance it with AI, render with a chosen template, and offer
download.  Language-aware: everything (AI output, section headings) follows
the selected UI language.
"""

import json
import base64

import streamlit as st

from config import APP_ICON
from cv_templates import render_advanced, render_simple
from i18n import get_lang, prompt_language, t
from pdf_extractor import extract_text_from_pdf
from providers import analyze_profile


# =============================================================================
# AI PROMPTS
# =============================================================================

CV_PARSE_PROMPT = """\
You are an expert CV / resume writer. Extract structured data from the
following candidate profile text. Return ONLY a valid JSON object matching
the schema below -- no markdown, no extra text.

PROFILE TEXT:
\"\"\"
{profile}
\"\"\"

Schema:
{{
  "name": "<string>",
  "title": "<string -- current role or headline>",
  "email": "<string>",
  "phone": "<string>",
  "location": "<string>",
  "linkedin": "<string -- LinkedIn URL if found>",
  "summary": "<string -- 2-4 sentence professional summary>",
  "skills": [<string>, ...],
  "experience": [
    {{
      "role": "<string>",
      "company": "<string>",
      "dates": "<string -- e.g. Jan 2022 - Present>",
      "description": "<string -- 2-4 bullet points, use \\n for newlines>"
    }}
  ],
  "education": [
    {{
      "degree": "<string>",
      "school": "<string>",
      "dates": "<string>"
    }}
  ],
  "languages": [<string>, ...],
  "certifications": [<string>, ...]
}}

Guidelines:
- Extract ALL information available; use empty string "" or empty list []
  for fields not present in the text.
- Write ALL text fields in {language}.
- Keep JSON keys exactly as shown above.
- Be concise but complete.
"""

CV_ENHANCE_PROMPT = """\
You are a senior career coach and professional CV writer with 15+ years
of experience.  Improve the following CV data so it is more impactful,
concise, and tailored for modern recruiters.

CURRENT CV DATA:
```json
{cv_json}
```

Rules:
- Rewrite "summary" to be 2-4 powerful sentences.
- Rewrite each experience "description" bullet to start with a strong
  action verb and, where possible, include a quantified result.
- Keep skills, education, languages, certifications accurate -- do NOT
  invent new items.
- Return the ENTIRE improved JSON object with the same schema.
- Write ALL text fields in {language}.  Do NOT translate the JSON keys.
- Return ONLY the JSON object -- no markdown fences, no extra text.
"""


# =============================================================================
# HELPERS
# =============================================================================

def _parse_json_from_text(text: str) -> dict:
    """Extract a JSON object from text that may contain markdown fences."""
    import re
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group(0))
    raise json.JSONDecodeError("No JSON object found.", text, 0)


def _ensure_structure(raw: dict) -> dict:
    """Guarantee every expected key exists with the right type."""
    defaults = {
        "name": "",
        "title": "",
        "email": "",
        "phone": "",
        "location": "",
        "linkedin": "",
        "summary": "",
        "skills": [],
        "experience": [],
        "education": [],
        "languages": [],
        "certifications": [],
    }
    for key, default in defaults.items():
        val = raw.get(key, default)
        if isinstance(default, list):
            if not isinstance(val, list):
                val = [str(val)] if val else []
        else:
            val = str(val) if val is not None else ""
        defaults[key] = val
    return defaults


def _html_download_link(html: str, filename: str, label: str) -> str:
    """Return an HTML anchor tag that triggers a browser download."""
    b64 = base64.b64encode(html.encode()).decode()
    return (
        f'<a href="data:text/html;base64,{b64}" download="{filename}">'
        f"{label}</a>"
    )


def _get_provider_and_model() -> tuple[str, str]:
    """Read the current provider/model from session state."""
    return (
        st.session_state.get("provider_select", "opencode_zen"),
        st.session_state.get("model_select", "big-pickle"),
    )


# =============================================================================
# PAGE RENDERER
# =============================================================================

def render_cv_builder():
    """Render the full CV Builder page."""
    lang = get_lang()          # "pt" or "en"
    ai_lang = prompt_language() # "Portuguese (Brazil)" or "English"

    st.header(t("cv_builder_header"))
    st.caption(t("cv_builder_caption"))
    st.caption(t("cv_language_note", language=ai_lang))

    # --- Layout selector ---
    layout = st.radio(
        t("cv_layout_label"),
        options=["advanced", "simple"],
        format_func=lambda x: t(f"cv_layout_{x}"),
        horizontal=True,
        key="cv_layout",
    )

    st.divider()

    # --- Profile input ---
    col_input, col_preview = st.columns([1, 1], gap="medium")

    with col_input:
        st.subheader(t("cv_profile_input_header"))

        input_mode = st.radio(
            t("cv_profile_source"),
            options=["paste", "upload"],
            format_func=lambda x: t(f"profile_mode_{x}"),
            horizontal=True,
            key="cv_profile_mode",
        )

        profile_text = ""

        if input_mode == "upload":
            uploaded = st.file_uploader(
                t("upload_pdf_label"),
                type=["pdf"],
                help=t("upload_pdf_help"),
                key="cv_pdf_upload",
            )
            if uploaded is not None:
                try:
                    profile_text = extract_text_from_pdf(uploaded)
                    st.success(t("pdf_success", chars=len(profile_text)))
                except RuntimeError as err:
                    st.error(str(err))
        else:
            profile_text = st.text_area(
                t("cv_profile_text_label"),
                height=300,
                placeholder=t("cv_profile_text_placeholder"),
                key="cv_profile_text",
            )

        # --- Photo upload (optional, for Advanced layout) ---
        if layout == "advanced":
            photo_file = st.file_uploader(
                t("cv_photo_label"),
                type=["jpg", "jpeg", "png"],
                help=t("cv_photo_help"),
                key="cv_photo",
            )
        else:
            photo_file = None

        # --- Enhance toggle ---
        enhance = st.checkbox(
            t("cv_enhance_label"),
            value=True,
            help=t("cv_enhance_help"),
            key="cv_enhance",
        )

    with col_preview:
        st.subheader(t("cv_preview_header"))

        # --- Build button ---
        build_clicked = st.button(
            t("cv_build_button"), type="primary", use_container_width=True
        )

        if build_clicked:
            if not profile_text.strip():
                st.error(t("error_profile_empty"))
                return

            provider, model = _get_provider_and_model()

            try:
                # Step 1: Parse profile into structured JSON
                with st.spinner(t("cv_spinner_building")):
                    raw = analyze_profile(
                        profile_text,
                        "",
                        provider,
                        model,
                        CV_PARSE_PROMPT,
                        ai_lang,
                    )
                cv_data = _ensure_structure(raw)

                # Step 2: (Optional) Enhance with AI
                if enhance:
                    with st.spinner(t("cv_spinner_enhance")):
                        enhanced = analyze_profile(
                            json.dumps(cv_data, ensure_ascii=False),
                            "",
                            provider,
                            model,
                            CV_ENHANCE_PROMPT,
                            ai_lang,
                            cv_json=json.dumps(cv_data, ensure_ascii=False, indent=2),
                        )
                        cv_data = _ensure_structure(enhanced)

                st.session_state["cv_data"] = cv_data
                st.session_state["cv_built"] = True

            except Exception as exc:
                st.error(t("error_unexpected", error=exc))
                return

        # --- Render preview if data exists ---
        if st.session_state.get("cv_built") and "cv_data" in st.session_state:
            cv_data = st.session_state["cv_data"]

            # Process photo
            photo_html = ""
            if layout == "advanced" and photo_file is not None:
                photo_bytes = photo_file.read()
                b64_photo = base64.b64encode(photo_bytes).decode()
                mime = photo_file.type or "image/jpeg"
                photo_html = (
                    f'<div class="photo">'
                    f'<img src="data:{mime};base64,{b64_photo}" alt="photo">'
                    f'</div>'
                )
            elif layout == "advanced":
                photo_html = (
                    '<div class="photo">'
                    '<div style="width:110px;height:110px;border-radius:50%;'
                    'background:#3a5068;display:flex;align-items:center;'
                    'justify-content:center;margin:0 auto;border:3px solid #7eb8da;">'
                    '<span style="color:#fff;font-size:36px;">'
                    f'{(cv_data.get("name","?") or "?")[0].upper()}</span>'
                    '</div></div>'
                )

            # Render HTML (pass lang for section headings)
            if layout == "advanced":
                html = render_advanced(cv_data, photo_html, lang=lang)
            else:
                html = render_simple(cv_data, lang=lang)

            # Display in iframe
            st.components.v1.html(html, height=850, scrolling=True)

            # --- Download buttons + print hint ---
            st.divider()
            st.info(t("cv_print_hint"))

            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                st.markdown(
                    _html_download_link(html, "cv.html", t("cv_download_html")),
                    unsafe_allow_html=True,
                )
            with dl_col2:
                json_str = json.dumps(cv_data, ensure_ascii=False, indent=2)
                st.download_button(
                    label=t("cv_download_json"),
                    data=json_str,
                    file_name="cv_data.json",
                    mime="application/json",
                )
        else:
            st.info(t("cv_preview_placeholder"))
