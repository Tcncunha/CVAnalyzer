"""
CV Analyzer — AI-Driven Career Assistant
=========================================
Single-file version: i18n, config, PDF extraction, profile persistence,
AI analysis, and the Streamlit UI all live in this one module.

Run with:  streamlit run src/app.py
(rename this file to app.py, replacing the old multi-file version)
"""

import json
import os
import re
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

# =============================================================================
# 1) I18N — translation strings and helpers (EN / PT)
# =============================================================================

DEFAULT_LANG = "pt"

# Metadata used to render the language switcher and to tell the AI which
# language it should write its analysis in.
LANGUAGES = {
    "pt": {"label": "Português", "flag": "🇧🇷", "prompt_language": "Portuguese (Brazil)"},
    "en": {"label": "English", "flag": "🇬🇧", "prompt_language": "English"},
}

STRINGS = {
    "pt": {
        # --- App shell ---
        "app_title": "CV Analyzer — Assistente de Carreira com IA",
        "app_caption": "Analise a compatibilidade do seu perfil com vagas de emprego usando inteligência artificial.",
        "profile_saved_success": "Perfil salvo em {name}",
        "analyze_button": "🔍 Analisar Compatibilidade",
        "error_profile_empty": "Por favor, insira o perfil do candidato (texto ou PDF).",
        "error_jd_empty": "Por favor, insira a descrição da vaga.",
        "spinner_analyzing": "Analisando compatibilidade com IA...",
        "error_json_invalid": "A resposta da IA não está em formato JSON válido. Tente novamente.",
        "error_unexpected": "Erro inesperado durante a análise: {error}",
        # --- Sidebar ---
        "sidebar_settings_header": "⚙️ Configurações",
        "provider_label": "Provedor de IA",
        "model_label": "Modelo",
        "profile_mgmt_header": "📋 Gerenciar Perfil",
        "saved_profiles_label": "Perfis salvos",
        "new_profile_label": "-- Novo Perfil --",
        "profile_loaded": "Perfil '{name}' carregado.",
        "candidate_identifier_label": "Identificador do Candidato",
        "candidate_identifier_placeholder": "Ex: João Silva",
        "save_profile_button": "💾 Salvar Perfil",
        "save_identifier_warning": "Informe um identificador para salvar.",
        # --- Input columns ---
        "candidate_profile_header": "👤 Perfil do Candidato",
        "profile_source_label": "Fonte do perfil",
        "profile_mode_paste": "Colar Texto",
        "profile_mode_upload": "Upload PDF",
        "upload_pdf_label": "Envie o CV em PDF",
        "upload_pdf_help": "Arraste ou selecione um arquivo PDF.",
        "pdf_success": "PDF processado com sucesso ({chars} caracteres).",
        "profile_text_label": "Cole o texto do perfil / LinkedIn aqui",
        "profile_text_placeholder": "Cole aqui o conteúdo do currículo ou perfil do LinkedIn...",
        "job_description_header": "💼 Descrição da Vaga",
        "job_url_label": "Link da vaga (referência)",
        "job_url_placeholder": "https://...",
        "job_description_label": "Cole a descrição completa da vaga",
        "job_description_placeholder": "Cole aqui a descrição da vaga...",
        # --- Results ---
        "results_header": "📊 Resultado da Análise",
        "compatibility_label": "Compatibilidade",
        "score_progress_text": "Score: {score}%",
        "score_excellent": "Excelente compatibilidade",
        "score_good": "Boa compatibilidade",
        "score_low": "Compatibilidade baixa",
        "job_reference_caption": "Referência da vaga: [{url}]({url})",
        "strengths_header": "✅ Pontos Fortes",
        "gaps_header": "⚠️ Lacunas",
        "suggestions_header": "💡 Sugestões de Melhoria",
        "json_expander_label": "🔎 JSON completo da análise",
        "disclaimer_text": (
            "⚠️ **Aviso:** Esta análise é gerada por IA e pode conter erros. "
            "Diferentes modelos e provedores podem resultar em scores e "
            "avaliações distintos para o mesmo perfil. Use como referência, "
            "não como veredicto final — considere, por exemplo, a média entre "
            "execuções (ex: 45 em uma e 65 em outra, média 55)."
        ),
        # --- Backend / errors ---
        "unknown_provider_error": "Provedor desconhecido: {provider}",
        "missing_api_key_error": (
            "A variável de ambiente {env_var} não está configurada. "
            "Crie um arquivo .env na raiz do projeto com:\n\n"
            "  {env_var}=sua-chave-aqui\n"
        ),
        "no_json_found_error": "Nenhum objeto JSON encontrado na resposta.",
        "pdf_extract_error": "Erro ao extrair texto do PDF: {error}",
    },
    "en": {
        # --- App shell ---
        "app_title": "CV Analyzer — AI Career Assistant",
        "app_caption": "Analyze how well your profile matches job openings using artificial intelligence.",
        "profile_saved_success": "Profile saved to {name}",
        "analyze_button": "🔍 Analyze Compatibility",
        "error_profile_empty": "Please enter the candidate's profile (text or PDF).",
        "error_jd_empty": "Please enter the job description.",
        "spinner_analyzing": "Analyzing compatibility with AI...",
        "error_json_invalid": "The AI response is not valid JSON. Please try again.",
        "error_unexpected": "Unexpected error during analysis: {error}",
        # --- Sidebar ---
        "sidebar_settings_header": "⚙️ Settings",
        "provider_label": "AI Provider",
        "model_label": "Model",
        "profile_mgmt_header": "📋 Manage Profile",
        "saved_profiles_label": "Saved profiles",
        "new_profile_label": "-- New Profile --",
        "profile_loaded": "Profile '{name}' loaded.",
        "candidate_identifier_label": "Candidate Identifier",
        "candidate_identifier_placeholder": "E.g.: John Smith",
        "save_profile_button": "💾 Save Profile",
        "save_identifier_warning": "Please provide an identifier to save.",
        # --- Input columns ---
        "candidate_profile_header": "👤 Candidate Profile",
        "profile_source_label": "Profile source",
        "profile_mode_paste": "Paste Text",
        "profile_mode_upload": "Upload PDF",
        "upload_pdf_label": "Upload the CV as PDF",
        "upload_pdf_help": "Drag and drop or select a PDF file.",
        "pdf_success": "PDF processed successfully ({chars} characters).",
        "profile_text_label": "Paste the profile / LinkedIn text here",
        "profile_text_placeholder": "Paste the resume or LinkedIn profile content here...",
        "job_description_header": "💼 Job Description",
        "job_url_label": "Job posting link (reference)",
        "job_url_placeholder": "https://...",
        "job_description_label": "Paste the full job description",
        "job_description_placeholder": "Paste the job description here...",
        # --- Results ---
        "results_header": "📊 Analysis Result",
        "compatibility_label": "Compatibility",
        "score_progress_text": "Score: {score}%",
        "score_excellent": "Excellent match",
        "score_good": "Good match",
        "score_low": "Low match",
        "job_reference_caption": "Job reference: [{url}]({url})",
        "strengths_header": "✅ Strengths",
        "gaps_header": "⚠️ Gaps",
        "suggestions_header": "💡 Improvement Suggestions",
        "json_expander_label": "🔎 Full analysis JSON",
        "disclaimer_text": (
            "⚠️ **Disclaimer:** This analysis is AI-generated and may contain "
            "errors. Different models and providers may produce different "
            "scores and assessments for the same profile. Use it as a "
            "reference, not a final verdict — consider, for example, the "
            "average across runs (e.g., 45 in one and 65 in another, "
            "average 55)."
        ),
        # --- Backend / errors ---
        "unknown_provider_error": "Unknown provider: {provider}",
        "missing_api_key_error": (
            "The environment variable {env_var} is not set. "
            "Create a .env file in the project root with:\n\n"
            "  {env_var}=your-key-here\n"
        ),
        "no_json_found_error": "No JSON object found in the response.",
        "pdf_extract_error": "Error extracting text from PDF: {error}",
    },
}


def get_lang() -> str:
    """Return the currently selected language code ('pt' or 'en')."""
    return st.session_state.get("lang", DEFAULT_LANG)


def set_lang(lang: str) -> None:
    """Persist the selected language code in session state."""
    st.session_state["lang"] = lang if lang in STRINGS else DEFAULT_LANG


def t(key: str, **kwargs) -> str:
    """Translate `key` into the current language, formatting with `kwargs`."""
    lang = get_lang()
    text = STRINGS.get(lang, STRINGS[DEFAULT_LANG]).get(key)
    if text is None:
        text = STRINGS[DEFAULT_LANG].get(key, key)
    return text.format(**kwargs) if kwargs else text


def prompt_language() -> str:
    """Return the language name to instruct the AI to write its output in."""
    return LANGUAGES.get(get_lang(), LANGUAGES[DEFAULT_LANG])["prompt_language"]


# =============================================================================
# 2) CONFIG — paths, constants, providers, environment, AI prompt
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

PROVIDERS = {
    "opencode_zen": {
        "name": "OpenCode Zen (Free Models)",
        "base_url": "https://opencode.ai/zen/v1",
        "env_key": "OPENCODE_ZEN_API_KEY",
        "json_mode": False,
    },
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "env_key": "GEMINI_API_KEY",
        "json_mode": True,
    },
}

MODELS = {
    "opencode_zen": {
        "big-pickle": "Big Pickle (Free)",
        "deepseek-v4-flash-free": "DeepSeek V4 Flash (Free)",
        "mimo-v2.5-free": "MiMo V2.5 (Free)",
        "north-mini-code-free": "North Mini Code (Free)",
        "nemotron-3-ultra-free": "Nemotron 3 Ultra (Free)",
    },
    "gemini": {
        "gemini-2.5-flash-preview-04-17": "Gemini 2.5 Flash (Preview)",
        "gemini-2.0-flash": "Gemini 2.0 Flash",
        "gemini-2.0-flash-lite": "Gemini 2.0 Flash Lite",
        "gemini-1.5-flash": "Gemini 1.5 Flash",
        "gemini-1.5-pro": "Gemini 1.5 Pro",
    },
}

DEFAULT_PROVIDER = "opencode_zen"
DEFAULT_MODEL = "big-pickle"


def get_api_key(provider: str) -> str:
    """Return the API key for the given provider or raise."""
    cfg = PROVIDERS.get(provider)
    if not cfg:
        raise EnvironmentError(t("unknown_provider_error", provider=provider))

    key = os.getenv(cfg["env_key"], "").strip()
    if not key:
        env_var = cfg["env_key"]
        raise EnvironmentError(t("missing_api_key_error", env_var=env_var))
    return key


PROFILES_DIR = PROJECT_ROOT / "src" / "profiles_json"
PROFILES_DIR.mkdir(exist_ok=True)

APP_ICON = "🎯"

ANALYSIS_PROMPT = """\
You are a senior technical recruiter and career coach with 15+ years of
experience in talent acquisition for top-tier tech companies.

Analyze the following candidate profile against the provided job description.
Provide a thorough, honest, and actionable assessment.

CANDIDATE PROFILE:
\"\"\"
{profile}
\"\"\"

JOB DESCRIPTION:
\"\"\"
{job_description}
\"\"\"

Respond ONLY with a valid JSON object (no markdown, no extra text) using
exactly this schema:
{{
  "overall_score": <integer 0-100>,
  "pontos_fortes": [<string>, ...],
  "lacunas": [<string>, ...],
  "sugestoes_melhoria": [<string>, ...]
}}

Guidelines:
- "overall_score" represents how well the candidate fits the role (0-100).
- "pontos_fortes" lists the candidate's strongest alignment points (3-7 items).
- "lacunas" lists missing skills, experiences, or gaps (2-6 items).
- "sugestoes_melhoria" lists specific, actionable tips to improve the resume \
  for this role (3-6 items).
- Be specific, reference actual content from the profile and job description.
- Write all fields in {language}. Keep the JSON keys exactly as given above \
  (do not translate the keys, only the text values).
"""


# =============================================================================
# 3) PDF EXTRACTION
# =============================================================================

def extract_text_from_pdf(uploaded_file) -> str:
    """Extract all text from an uploaded PDF file-like object."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        reader = PdfReader(tmp_path)
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(pages).strip()

        os.unlink(tmp_path)
        return text
    except Exception as exc:
        raise RuntimeError(t("pdf_extract_error", error=exc)) from exc


# =============================================================================
# 4) PROFILE PERSISTENCE — local JSON files
# =============================================================================

def list_saved_profiles() -> list[str]:
    """Return sorted list of saved profile identifiers (without extension)."""
    return sorted(p.stem for p in PROFILES_DIR.glob("*.json") if p.is_file())


def save_profile(identifier: str, data: dict) -> Path:
    """Persist a profile dictionary to a JSON file."""
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", identifier.strip())
    file_path = PROFILES_DIR / f"{safe_name}.json"
    file_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return file_path


def load_profile(identifier: str) -> dict | None:
    """Load a profile from disk. Returns None if not found."""
    file_path = PROFILES_DIR / f"{identifier}.json"
    if file_path.exists():
        return json.loads(file_path.read_text(encoding="utf-8"))
    return None


# =============================================================================
# 5) ANALYSIS ENGINE — multi-provider (OpenCode Zen + Gemini, OpenAI-compatible)
# =============================================================================

def _parse_json_from_text(text: str) -> dict:
    """Extract a JSON object from text that may contain markdown or extra content."""
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group(0))
    raise json.JSONDecodeError(t("no_json_found_error"), text, 0)


def analyze_profile(
    profile_text: str,
    job_description: str,
    provider: str,
    model: str,
    language: str | None = None,
) -> dict:
    """Send profile + JD to the selected provider and return structured JSON.

    `language` controls the language the AI writes the analysis fields in
    (defaults to the current UI language, see prompt_language()).
    """
    cfg = PROVIDERS[provider]
    api_key = get_api_key(provider)
    client = OpenAI(api_key=api_key, base_url=cfg["base_url"])

    if language is None:
        language = prompt_language()

    messages = [
        {
            "role": "system",
            "content": "You always respond with valid JSON only.",
        },
        {
            "role": "user",
            "content": ANALYSIS_PROMPT.format(
                profile=profile_text,
                job_description=job_description,
                language=language,
            ),
        },
    ]

    # Free models may not support response_format — try with it first,
    # fall back to plain text + regex JSON extraction if it fails.
    if cfg["json_mode"]:
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=messages,
        )
        raw = response.choices[0].message.content
        return json.loads(raw)

    # Non-JSON-mode provider: try response_format, fall back to text parsing
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=messages,
        )
        raw = response.choices[0].message.content
        return json.loads(raw)
    except Exception:
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            messages=messages,
        )
        raw = response.choices[0].message.content
        return _parse_json_from_text(raw)


# =============================================================================
# 6) UI — sidebar, input columns, results
# =============================================================================

def render_sidebar() -> tuple[str, dict | None, str, str]:
    """Render sidebar controls and return (identifier, loaded_data, provider, model)."""
    with st.sidebar:
        st.header(t("sidebar_settings_header"))

        # --- Provider ---
        provider_keys = list(PROVIDERS.keys())
        default_prov_idx = provider_keys.index(DEFAULT_PROVIDER)

        selected_provider = st.selectbox(
            t("provider_label"),
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


# =============================================================================
# 7) APP ENTRY POINT
# =============================================================================

def render_header() -> None:
    """Render the title/caption alongside a language switcher (EN/PT)."""
    title_col, lang_col = st.columns([5, 1], vertical_alignment="bottom")

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

    with title_col:
        st.title(f"{APP_ICON} {t('app_title')}")

    st.caption(t("app_caption"))


def main():
    st.set_page_config(page_title=t("app_title"), page_icon=APP_ICON, layout="wide")

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

        try:
            with st.spinner(t("spinner_analyzing")):
                results = analyze_profile(
                    profile_text,
                    job_description,
                    selected_provider,
                    selected_model,
                    prompt_language(),
                )
            render_results(results, job_url)
        except EnvironmentError as exc:
            st.error(str(exc))
        except json.JSONDecodeError:
            st.error(t("error_json_invalid"))
        except Exception as exc:
            st.error(t("error_unexpected", error=exc))


if __name__ == "__main__":
    main()
