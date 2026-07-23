"""
Internationalization (i18n) — language strings and helpers.

Supported languages: Portuguese ("pt") and English ("en").
All user-facing text lives in the STRINGS dictionary below;
UI modules should never hardcode display text — call t(key) instead.
"""

import streamlit as st

DEFAULT_LANG = "pt"

LANGUAGES = {
    "pt": {"label": "Portugues", "flag": "BR", "prompt_language": "Portuguese (Brazil)"},
    "en": {"label": "English", "flag": "GB", "prompt_language": "English"},
}

STRINGS = {
    "pt": {
        # --- App shell ---
        "app_title": "CV Analyzer -- Assistente de Carreira com IA",
        "app_caption": "Analise a compatibilidade do seu perfil com vagas de emprego usando inteligencia artificial.",
        "profile_saved_success": "Perfil salvo em {name}",
        "analyze_button": "Analises Compatibilidade",
        "error_profile_empty": "Por favor, insira o perfil do candidato (texto ou PDF).",
        "error_jd_empty": "Por favor, insira a descricao da vaga.",
        "spinner_analyzing": "Analisando compatibilidade com IA...",
        "error_json_invalid": "A resposta da IA nao esta em formato valido. Tente novamente.",
        "error_unexpected": "Erro inesperado durante a analise: {error}",
        # --- Sidebar ---
        "sidebar_settings_header": "Configuracoes",
        "provider_label": "Provedor de IA",
        "model_label": "Modelo",
        "api_key_label": "Chave de API",
        "api_key_placeholder": "Cole sua chave de API aqui...",
        "api_key_info": "Sua chave fica apenas nesta sessao (nao e salva).",
        "api_key_required": "Por favor, insira uma chave de API para usar este provedor.",
        "profile_mgmt_header": "Gerenciar Perfil",
        "saved_profiles_label": "Perfis salvos",
        "new_profile_label": "-- Novo Perfil --",
        "profile_loaded": "Perfil '{name}' carregado.",
        "candidate_identifier_label": "Identificador do Candidato",
        "candidate_identifier_placeholder": "Ex: Joao Silva",
        "save_profile_button": "Salvar Perfil",
        "save_identifier_warning": "Informe um identificador para salvar.",
        # --- Input columns ---
        "candidate_profile_header": "Perfil do Candidato",
        "profile_source_label": "Fonte do perfil",
        "profile_mode_paste": "Colar Texto",
        "profile_mode_upload": "Upload PDF",
        "upload_pdf_label": "Envie o CV em PDF",
        "upload_pdf_help": "Arraste ou selecione um arquivo PDF.",
        "pdf_success": "PDF processado com sucesso ({chars} caracteres).",
        "profile_text_label": "Cole o texto do perfil / LinkedIn aqui",
        "profile_text_placeholder": "Cole aqui o conteudo do curriculo ou perfil do LinkedIn...",
        "job_description_header": "Descricao da Vaga",
        "job_url_label": "Link da vaga (referencia)",
        "job_url_placeholder": "https://...",
        "job_description_label": "Cole a descricao completa da vaga",
        "job_description_placeholder": "Cole aqui a descricao da vaga...",
        # --- Results ---
        "results_header": "Resultado da Analise",
        "compatibility_label": "Compatibilidade",
        "score_progress_text": "Score: {score}%",
        "score_excellent": "Excelente compatibilidade",
        "score_good": "Boa compatibilidade",
        "score_low": "Compatibilidade baixa",
        "job_reference_caption": "Referencia da vaga: [{url}]({url})",
        "strengths_header": "Pontos Fortes",
        "gaps_header": "Lacunas",
        "suggestions_header": "Sugestoes de Melhoria",
        "json_expander_label": "JSON completo da analise",
        "disclaimer_text": (
            "Aviso: Esta analise e gerada por IA e pode conter erros. "
            "Diferentes modelos e provedores podem resultar em scores e "
            "avaliacoes distintos para o mesmo perfil. Use como referencia, "
            "nao como veredicto final."
        ),
        # --- Backend / errors ---
        "unknown_provider_error": "Provedor desconhecido: {provider}",
        "missing_api_key_error": "Por favor, insira uma chave de API para o provedor {provider}.",
        "no_json_found_error": "Nenhum objeto JSON encontrado na resposta.",
        "pdf_extract_error": "Erro ao extrair texto do PDF: {error}",
        # --- CV Builder ---
        "tab_analyzer": "Analise de CV",
        "tab_builder": "Construtor de CV",
        "cv_builder_header": "Construtor de CV",
        "cv_builder_caption": "Cole seu perfil do LinkedIn e gere um CV profissional com layout personalizado.",
        "cv_layout_label": "Escolha o layout",
        "cv_layout_advanced": "Avancado (duas colunas)",
        "cv_layout_simple": "Simples (coluna unica)",
        "cv_profile_input_header": "Perfil do Candidato",
        "cv_profile_source": "Fonte do perfil",
        "cv_profile_text_label": "Cole o texto do perfil / LinkedIn aqui",
        "cv_profile_text_placeholder": "Cole aqui o conteudo do seu LinkedIn, curriculo ou perfil profissional...",
        "cv_photo_label": "Foto do perfil (opcional)",
        "cv_photo_help": "Arraste ou selecione uma foto para o CV Avancado.",
        "cv_preview_header": "Visualizacao do CV",
        "cv_build_button": "Gerar CV",
        "cv_spinner_building": "Analisando perfil e gerando CV...",
        "cv_download_html": "Baixar CV (HTML)",
        "cv_download_json": "Baixar dados (JSON)",
        "cv_preview_placeholder": "Cole seu perfil e clique em 'Gerar CV' para visualizar.",
        "cv_enhance_label": "Aprimorar com IA",
        "cv_enhance_help": "Use IA para melhorar resumo, bullet points e措辞 do CV.",
        "cv_spinner_enhance": "Aprimorando conteudo do CV com IA...",
        "cv_print_hint": "Dica: Use Ctrl+P (ou Cmd+P) no HTML baixado para salvar como PDF.",
        "cv_language_note": "O CV sera gerado em {language}.",
    },
    "en": {
        # --- App shell ---
        "app_title": "CV Analyzer -- AI Career Assistant",
        "app_caption": "Analyze how well your profile matches job openings using artificial intelligence.",
        "profile_saved_success": "Profile saved to {name}",
        "analyze_button": "Analyze Compatibility",
        "error_profile_empty": "Please enter the candidate's profile (text or PDF).",
        "error_jd_empty": "Please enter the job description.",
        "spinner_analyzing": "Analyzing compatibility with AI...",
        "error_json_invalid": "The AI response is not valid JSON. Please try again.",
        "error_unexpected": "Unexpected error during analysis: {error}",
        # --- Sidebar ---
        "sidebar_settings_header": "Settings",
        "provider_label": "AI Provider",
        "model_label": "Model",
        "api_key_label": "API Key",
        "api_key_placeholder": "Paste your API key here...",
        "api_key_info": "Your key is only used in this session (not saved).",
        "api_key_required": "Please enter an API key to use this provider.",
        "profile_mgmt_header": "Manage Profile",
        "saved_profiles_label": "Saved profiles",
        "new_profile_label": "-- New Profile --",
        "profile_loaded": "Profile '{name}' loaded.",
        "candidate_identifier_label": "Candidate Identifier",
        "candidate_identifier_placeholder": "E.g.: John Smith",
        "save_profile_button": "Save Profile",
        "save_identifier_warning": "Please provide an identifier to save.",
        # --- Input columns ---
        "candidate_profile_header": "Candidate Profile",
        "profile_source_label": "Profile source",
        "profile_mode_paste": "Paste Text",
        "profile_mode_upload": "Upload PDF",
        "upload_pdf_label": "Upload the CV as PDF",
        "upload_pdf_help": "Drag and drop or select a PDF file.",
        "pdf_success": "PDF processed successfully ({chars} characters).",
        "profile_text_label": "Paste the profile / LinkedIn text here",
        "profile_text_placeholder": "Paste the resume or LinkedIn profile content here...",
        "job_description_header": "Job Description",
        "job_url_label": "Job posting link (reference)",
        "job_url_placeholder": "https://...",
        "job_description_label": "Paste the full job description",
        "job_description_placeholder": "Paste the job description here...",
        # --- Results ---
        "results_header": "Analysis Result",
        "compatibility_label": "Compatibility",
        "score_progress_text": "Score: {score}%",
        "score_excellent": "Excellent match",
        "score_good": "Good match",
        "score_low": "Low match",
        "job_reference_caption": "Job reference: [{url}]({url})",
        "strengths_header": "Strengths",
        "gaps_header": "Gaps",
        "suggestions_header": "Improvement Suggestions",
        "json_expander_label": "Full analysis JSON",
        "disclaimer_text": (
            "Disclaimer: This analysis is AI-generated and may contain "
            "errors. Different models and providers may produce different "
            "scores and assessments for the same profile. Use it as a "
            "reference, not a final verdict."
        ),
        # --- Backend / errors ---
        "unknown_provider_error": "Unknown provider: {provider}",
        "missing_api_key_error": "Please enter an API key for provider: {provider}.",
        "no_json_found_error": "No JSON object found in the response.",
        "pdf_extract_error": "Error extracting text from PDF: {error}",
        # --- CV Builder ---
        "tab_analyzer": "CV Analyzer",
        "tab_builder": "CV Builder",
        "cv_builder_header": "CV Builder",
        "cv_builder_caption": "Paste your LinkedIn profile and generate a professional CV with a personalized layout.",
        "cv_layout_label": "Choose layout",
        "cv_layout_advanced": "Advanced (two-column)",
        "cv_layout_simple": "Simple (single-column)",
        "cv_profile_input_header": "Candidate Profile",
        "cv_profile_source": "Profile source",
        "cv_profile_text_label": "Paste the profile / LinkedIn text here",
        "cv_profile_text_placeholder": "Paste your LinkedIn, resume or professional profile content here...",
        "cv_photo_label": "Profile photo (optional)",
        "cv_photo_help": "Drag and drop or select a photo for the Advanced CV.",
        "cv_preview_header": "CV Preview",
        "cv_build_button": "Generate CV",
        "cv_spinner_building": "Analyzing profile and generating CV...",
        "cv_download_html": "Download CV (HTML)",
        "cv_download_json": "Download data (JSON)",
        "cv_preview_placeholder": "Paste your profile and click 'Generate CV' to preview.",
        "cv_enhance_label": "Enhance with AI",
        "cv_enhance_help": "Use AI to improve summary, bullet points and wording.",
        "cv_spinner_enhance": "Enhancing CV content with AI...",
        "cv_print_hint": "Tip: Use Ctrl+P (or Cmd+P) on the downloaded HTML to save as PDF.",
        "cv_language_note": "The CV will be generated in {language}.",
    },
}


def get_lang() -> str:
    """Return the currently selected language code ('pt' or 'en')."""
    return st.session_state.get("lang", DEFAULT_LANG)


def set_lang(lang: str) -> None:
    """Persist the selected language code in session state."""
    st.session_state["lang"] = lang if lang in STRINGS else DEFAULT_LANG


def t(key: str, **kwargs) -> str:
    """Translate key into the current language, formatting with kwargs."""
    lang = get_lang()
    text = STRINGS.get(lang, STRINGS[DEFAULT_LANG]).get(key)
    if text is None:
        text = STRINGS[DEFAULT_LANG].get(key, key)
    return text.format(**kwargs) if kwargs else text


def prompt_language() -> str:
    """Return the language name to instruct the AI to write its output in."""
    return LANGUAGES.get(get_lang(), LANGUAGES[DEFAULT_LANG])["prompt_language"]
