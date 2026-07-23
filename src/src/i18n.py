"""
Internationalization (i18n) — language strings and helpers.

Supported languages: Portuguese ("pt", original language of the app) and
English ("en"). All user-facing text lives in the STRINGS dictionary below;
UI modules should never hardcode display text — they should call `t(key)`.
"""

import streamlit as st

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
