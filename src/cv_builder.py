"""
CV Builder page -- parse a LinkedIn / profile text into structured data,
optionally enhance it with AI, render with a chosen template, and offer
download.  Language-aware: everything (AI output, section headings) follows
the selected UI language.
"""

import html
import json
import base64

import streamlit as st

from config import APP_ICON
from cv_templates import render_advanced, render_simple
from cv_utils import ensure_cv_structure, parse_json_from_text
from i18n import get_lang, prompt_language, t
from pdf_extractor import extract_text_from_pdf
from progress_utils import run_with_progress
from providers import analyze_profile, get_api_key, get_selected_model


# =============================================================================
# AI PROMPTS
# =============================================================================

CV_PARSE_PROMPT = """\
[SYSTEM ROLE]
You are an enterprise-grade AI Document Intelligence Parser specializing in HR tech and structured CV extraction. 

[OBJECTIVE]
Extract structured candidate data from the provided profile text with absolute fidelity, adhering strictly to the designated JSON schema.

[INPUT DATA]
PROFILE TEXT:
\"\"\"
{profile}
\"\"\"

[DATA INTEGRITY & FAITHFULNESS PROTOCOL]
- Extract ONLY explicit facts present in the text. 
- NEVER infer, embellish, extrapolate, or hallucinate. 
- Strict exclusions: Do NOT add proficiency levels (e.g., "fluent", "advanced", "CEFR"), seniority markers, unstated metrics, tools, certifications, degrees, institutions, or dates not explicitly written. 
- If a language is listed without proficiency, output only the language name.
- For missing fields, use an empty string ("") or an empty list ([]).

[OUTPUT FORMAT]
- Return a valid, raw JSON object ONLY. 
- Do NOT wrap the JSON in markdown blocks (no ```json ... ```).
- Keep the exact JSON keys provided below.
- Ensure proper escaping for strings and literal \\n for newlines in descriptions.

[SCHEMA]
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
      "description": "<string -- 2-4 bullet points, use literal \\n for newlines>"
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

[LANGUAGE REQUIREMENT]
Translate all text values entirely into {language}. Do not retain the source language. Keep JSON keys untranslated.
"""

CV_ENHANCE_PROMPT = """\
[SYSTEM ROLE]
You are a Principal Executive Career Coach and ATS-Optimization Architect with 15+ years of experience in elite talent acquisition.

[OBJECTIVE]
Enhance the impact, punchiness, and readability of the provided candidate CV data without altering its core factual truth.

[INPUT DATA]
CURRENT CV DATA:
```json
{cv_json}
```

[ENHANCEMENT GUIDELINES]
- Rewrite the professional summary to be more impactful, concise, and punchy.
- Strengthen every experience bullet: start with a strong action verb and be concise.
- Reorder skills to surface the most relevant ones first.
- FAITHFULNESS PROTOCOL (CRITICAL): Preserve every fact exactly as provided. Do NOT invent metrics, tools, certifications, degrees, institutions, or dates.

[OUTPUT FORMAT]
- Return a valid, raw JSON object ONLY.
- Do NOT wrap the JSON in markdown blocks (no ```json ... ```).
- Keep the exact JSON keys provided below.
- Ensure proper escaping for strings and literal \\n for newlines in descriptions.

[SCHEMA]
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
      "description": "<string -- 2-4 bullet points, use literal \\n for newlines>"
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

[LANGUAGE REQUIREMENT]
Translate all text values entirely into {language}. Do not translate JSON keys.
"""

CV_TAILOR_PROMPT = '''\
[SYSTEM ROLE]
You are an elite Executive Recruiter and ATS-Optimization Specialist. Your objective is to align candidate profiles precisely with target job descriptions while maintaining rigorous data integrity.

[OBJECTIVE]
Produce a perfectly tailored, ATS-friendly CV based exclusively on the candidate profile and insights provided, targeting the given job description.

[INPUT DATA]
TARGET JOB DESCRIPTION:
"""
{job_description}
"""

CANDIDATE PROFILE:
"""
{profile}
"""

ANALYSIS INSIGHTS:
"""
{analysis_insights}
"""

[TAILORING & ATS GUIDELINES]

Keyword Alignment: Mirror exact terminology from the job description wherever the candidate's actual experience supports it.

Professional Summary: Craft 2-4 sentences mirroring the target role title and top 3 core keywords from the job description.

Experience Optimization: Prioritize and re-order experience bullets by relevance to the target role. Ensure every bullet starts with a strong action verb.

FAITHFULNESS PROTOCOL (CRITICAL): The output must contain ONLY facts present in the candidate profile. Do NOT invent metrics, tools, certifications, dates, or experience levels.

[OUTPUT FORMAT]

Return a valid, raw JSON object ONLY. No markdown code blocks.

Maintain the exact schema structure below.

[SCHEMA]
{{
"name": "",
"title": "<string -- current role or headline>",
"email": "",
"phone": "",
"location": "",
"linkedin": "",
"summary": "<string -- 2-4 sentence professional summary tailored to the job>",
"skills": [, ...],
"experience": [
{{
"role": "",
"company": "",
"dates": "",
"description": "<string -- 2-4 bullet points, use literal \\n for newlines>"
}}
],
"education": [
{{
"degree": "",
"school": "",
"dates": ""
}}
],
"languages": [, ...],
"certifications": [, ...]
}}

[LANGUAGE REQUIREMENT]
Translate all text values entirely into {language}. Do not translate JSON keys.
'''

# =============================================================================
# HELPERS
# =============================================================================

def cv_data_to_text(cv_data: dict) -> str:
    """Convert structured CV data back to plain text for re-analysis."""
    lines = []
    if cv_data.get("name"):
        lines.append(cv_data["name"])
    if cv_data.get("title"):
        lines.append(cv_data["title"])
    lines.append("")

    if cv_data.get("email"):
        lines.append(f"Email: {cv_data['email']}")
    if cv_data.get("phone"):
        lines.append(f"Phone: {cv_data['phone']}")
    if cv_data.get("location"):
        lines.append(f"Location: {cv_data['location']}")
    if cv_data.get("linkedin"):
        lines.append(f"LinkedIn: {cv_data['linkedin']}")
    if any([cv_data.get("email"), cv_data.get("phone"), cv_data.get("location"), cv_data.get("linkedin")]):
        lines.append("")

    if cv_data.get("summary"):
        lines.append("Summary:")
        lines.append(cv_data["summary"])
        lines.append("")

    if cv_data.get("skills"):
        lines.append("Skills:")
        lines.append(", ".join(cv_data["skills"]))
        lines.append("")

    if cv_data.get("experience"):
        lines.append("Experience:")
        for exp in cv_data["experience"]:
            header = f"- {exp.get('role', '')}"
            if exp.get("company"):
                header += f" at {exp['company']}"
            if exp.get("dates"):
                header += f" ({exp['dates']})"
            lines.append(header)
            if exp.get("description"):
                for bullet in str(exp["description"]).split("\n"):
                    bullet = bullet.strip()
                    if bullet:
                        lines.append(f"  {bullet}")
        lines.append("")

    if cv_data.get("education"):
        lines.append("Education:")
        for edu in cv_data["education"]:
            line = f"- {edu.get('degree', '')}"
            if edu.get("school"):
                line += f" — {edu['school']}"
            if edu.get("dates"):
                line += f" ({edu['dates']})"
            lines.append(line)
        lines.append("")

    if cv_data.get("languages"):
        lines.append("Languages:")
        lines.append(", ".join(cv_data["languages"]))
        lines.append("")

    if cv_data.get("certifications"):
        lines.append("Certifications:")
        lines.append(", ".join(cv_data["certifications"]))

    return "\n".join(lines)


def _html_download_link(html: str, filename: str, label: str) -> str:
    """Return an HTML anchor tag that triggers a browser download."""
    b64 = base64.b64encode(html.encode()).decode()
    return (
        f'<a href="data:text/html;base64,{b64}" download="{filename}">'
        f"{html.escape(label)}</a>"
    )


def _get_provider_and_model() -> tuple[str, str]:
    """Read the current provider/model from session state."""
    return (
        st.session_state.get("provider_select", "opencode_zen"),
        get_selected_model(),
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
                    st.error(t("pdf_extract_error", error=err))
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
                cv_data = ensure_cv_structure(raw)

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
                        cv_data = ensure_cv_structure(enhanced)

                st.session_state["cv_data"] = cv_data
                st.session_state["cv_built"] = True

            except Exception as exc:
                st.error(t("error_unexpected", error=exc))
                return

        # --- Render preview if data exists ---
        render_cv_preview(photo_file)


# =============================================================================
# SHARED PREVIEW RENDERER
# =============================================================================

def render_cv_preview(photo_file=None, key_prefix: str = "builder") -> None:
    """Render the CV preview, photo processing, and download buttons.

    Reads cv_data / cv_built / cv_layout from session state, so it can be
    reused from the Analyzer tab (tailored CVs) and the Builder tab.
    `key_prefix` must differ per call site to avoid duplicate widget IDs
    (both tabs render in the same run).
    """
    if not (st.session_state.get("cv_built") and "cv_data" in st.session_state):
        st.info(t("cv_preview_placeholder"))
        return

    lang = get_lang()
    cv_data = st.session_state["cv_data"]
    layout = st.session_state.get("cv_layout", "advanced")

    # Process photo
    photo_html = ""
    if layout == "advanced" and photo_file is not None:
        photo_file.seek(0)  # reset pointer (UploadedFile persists across reruns)
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

    # --- Faithful badge (above the preview) ---
    st.markdown(f":green[**{t('badge_faithful')}**]")

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
            key=f"{key_prefix}_download_json",
        )

    # --- DOCX / PDF export (ATS-friendly, lazy imports so missing optional
    # dependencies degrade to a caption instead of breaking the whole app) ---
    dl_export_col1, dl_export_col2 = st.columns(2)
    with dl_export_col1:
        try:
            from cv_export import export_docx

            docx_bytes = export_docx(cv_data, get_lang())
            st.download_button(
                label=t("cv_download_docx"),
                data=docx_bytes,
                file_name="cv.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key=f"{key_prefix}_download_docx",
            )
        except Exception:
            st.caption(t("export_ats_note"))
    with dl_export_col2:
        try:
            from cv_export import export_pdf

            pdf_bytes = export_pdf(cv_data, get_lang())
            st.download_button(
                label=t("cv_download_pdf"),
                data=pdf_bytes,
                file_name="cv.pdf",
                mime="application/pdf",
                key=f"{key_prefix}_download_pdf",
            )
        except Exception:
            st.caption(t("export_ats_note"))
