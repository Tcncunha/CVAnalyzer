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
    "es": {"label": "Espanol", "flag": "ES", "prompt_language": "Spanish"},
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
        "error_rate_limit": "Limite de uso gratuito atingido (429). Aguarde alguns minutos e tente novamente, ou troque de modelo/provedor (ex.: Gemini gratis ou OpenAI com chave).",
        "error_unexpected": "Erro inesperado durante a analise: {error}",
        # --- Sidebar ---
        "sidebar_settings_header": "Configuracoes",
        "provider_label": "Provedor de IA",
        "model_label": "Modelo",
        "api_key_label": "Chave de API",
        "api_key_placeholder": "Cole sua chave de API aqui...",
        "api_key_info": "Sua chave fica apenas nesta sessao (nao e salva).",
        "api_key_required": "Por favor, insira uma chave de API para usar este provedor.",
        "api_key_detected": "Chave reconhecida: {provider}. Provedor selecionado automaticamente.",
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
        "job_url_label": "Link da vaga",
        "job_url_placeholder": "https://...",
        "job_url_hint": "Cole o link da vaga e clique em buscar para obter a descricao automaticamente, ou cole a descricao manualmente abaixo.",
        "job_fetch_button": "Buscar descricao pelo link",
        "spinner_fetching_job": "Buscando descricao da vaga no link...",
        "job_fetch_success": "Descricao obtida do link ({chars} caracteres).",
        "job_fetch_failed": "Nao foi possivel obter a descricao pelo link (o site pode bloquear acessos automatizados). Cole a descricao manualmente.",
        "job_description_label": "Cole a descricao completa da vaga",
        "job_description_placeholder": "Cole aqui a descricao da vaga...",
        # --- Tailored CV offer ---
        "tailored_cv_header": "CV focado nesta vaga",
        "tailored_cv_caption": "Com base na analise, gere um CV otimizado exatamente para esta vaga (ATS) usando o CV Builder.",
        "tailored_cv_button": "Gerar CV focado nesta vaga",
        "tailored_cv_spinner": "Gerando CV focado na vaga...",
        "tailored_cv_success": "CV gerado com sucesso! Visualize abaixo ou baixe o HTML.",
        "reanalyze_button": "Re-analisar com este CV",
        "reanalyze_spinner": "Re-analisando CV gerado...",
        "progress_send": "Enviando perfil e vaga para a IA...",
        "progress_analyzing": "IA analisando compatibilidade...",
        "progress_parsing": "Montando resultado...",
        "progress_cv_tailoring": "IA criando CV focado na vaga...",
        "progress_cv_writing": "Escrevendo secoes do CV...",
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
        # --- Job Search ---
        "tab_job_search": "Busca de Vagas",
        "job_search_header": "Busca de Vagas",
        "job_search_caption": "Busque vagas reais pela API do Adzuna e envie uma vaga direto para a analise de compatibilidade do CV.",
        "job_search_config_header": "Configuracoes da busca",
        "job_search_keyword_label": "Palavras-chave",
        "job_search_keyword_placeholder": "Ex.: Python, Data Analyst, Product Manager",
        "job_search_location_label": "Localizacao (opcional)",
        "job_search_location_placeholder": "Ex.: Sao Paulo, Lisboa, remoto",
        "job_search_country_label": "Pais",
        "job_search_results_label": "Resultados por pagina",
        "job_search_button": "Buscar Vagas",
        "job_search_spinner": "Buscando vagas no Adzuna...",
        "job_search_keyword_required": "Digite palavras-chave para buscar vagas.",
        "job_search_no_keys": "Para buscar vagas, informe seu Adzuna App ID e App Key no menu lateral. As chaves sao gratuitas em developer.adzuna.com e ficam apenas nesta sessao.",
        "job_search_no_results": "Nenhuma vaga encontrada para esses criterios. Tente outras palavras-chave ou localizacao.",
        "job_search_count": "{count} vaga(s) encontrada(s). Exibindo {shown}.",
        "job_search_use_button": "Usar nesta analise",
        "job_search_use_success": "Descricao da vaga carregada! Va para a aba 'Analise de CV' e clique em Analisar Compatibilidade.",
        "job_search_posted": "Publicada em {date}",
        "job_search_open": "Abrir vaga no site",
        "job_search_keys_header": "Busca de Vagas -- Chaves Adzuna",
        "job_search_keys_hint": "Gratuitas em developer.adzuna.com. Ficam apenas nesta sessao (nao sao salvas).",
        "job_search_app_id_label": "Adzuna App ID",
        "job_search_app_key_label": "Adzuna App Key",
        "job_search_error": "Erro na busca de vagas: {error}",
        # --- Footer ---
        "footer_disclaimer": (
            "Este e um projeto pessoal e nao uma solucao comercial. "
            "Foi criado como uma ideia para ajudar pessoas a utilizarem "
            "inteligencia artificial na busca por emprego. "
            "Nao e um servico profissional -- use com responsabilidade e "
            "sempre revise o conteudo gerado por IA."
        ),
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
        "error_rate_limit": "Free usage limit reached (429). Wait a few minutes and try again, or switch model/provider (e.g., free Gemini or OpenAI with a key).",
        "error_unexpected": "Unexpected error during analysis: {error}",
        # --- Sidebar ---
        "sidebar_settings_header": "Settings",
        "provider_label": "AI Provider",
        "model_label": "Model",
        "api_key_label": "API Key",
        "api_key_placeholder": "Paste your API key here...",
        "api_key_info": "Your key is only used in this session (not saved).",
        "api_key_required": "Please enter an API key to use this provider.",
        "api_key_detected": "Key detected as {provider}. Provider selected automatically.",
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
        "job_url_label": "Job posting link",
        "job_url_placeholder": "https://...",
        "job_url_hint": "Paste the job link and click fetch to grab the description automatically, or paste the description manually below.",
        "job_fetch_button": "Fetch description from link",
        "spinner_fetching_job": "Fetching job description from link...",
        "job_fetch_success": "Description fetched from link ({chars} characters).",
        "job_fetch_failed": "Could not get the description from the link (the site may block automated access). Please paste the description manually.",
        "job_description_label": "Paste the full job description",
        "job_description_placeholder": "Paste the job description here...",
        # --- Tailored CV offer ---
        "tailored_cv_header": "CV focused on this job",
        "tailored_cv_caption": "Based on the analysis, generate a CV optimized exactly for this vacancy (ATS) using the CV Builder.",
        "tailored_cv_button": "Generate CV focused on this job",
        "tailored_cv_spinner": "Generating job-focused CV...",
        "tailored_cv_success": "CV generated successfully! Preview below or download the HTML.",
        "reanalyze_button": "Re-analyze with this CV",
        "reanalyze_spinner": "Re-analyzing generated CV...",
        "progress_send": "Sending profile and job to the AI...",
        "progress_analyzing": "AI analyzing compatibility...",
        "progress_parsing": "Building result...",
        "progress_cv_tailoring": "AI building job-focused CV...",
        "progress_cv_writing": "Writing CV sections...",
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
        # --- Job Search ---
        "tab_job_search": "Job Search",
        "job_search_header": "Job Search",
        "job_search_caption": "Search real job listings via the Adzuna API and send a posting straight to the compatibility analysis.",
        "job_search_config_header": "Search settings",
        "job_search_keyword_label": "Keywords",
        "job_search_keyword_placeholder": "E.g.: Python, Data Analyst, Product Manager",
        "job_search_location_label": "Location (optional)",
        "job_search_location_placeholder": "E.g.: Sao Paulo, Lisbon, remote",
        "job_search_country_label": "Country",
        "job_search_results_label": "Results per page",
        "job_search_button": "Search Jobs",
        "job_search_spinner": "Searching jobs on Adzuna...",
        "job_search_keyword_required": "Enter keywords to search for jobs.",
        "job_search_no_keys": "To search jobs, enter your Adzuna App ID and App Key in the sidebar. Keys are free at developer.adzuna.com and live only in this session.",
        "job_search_no_results": "No jobs found for these criteria. Try other keywords or location.",
        "job_search_count": "{count} job(s) found. Showing {shown}.",
        "job_search_use_button": "Use for analysis",
        "job_search_use_success": "Job description loaded! Go to the 'CV Analyzer' tab and click Analyze Compatibility.",
        "job_search_posted": "Posted {date}",
        "job_search_open": "Open job on site",
        "job_search_keys_header": "Job Search -- Adzuna Keys",
        "job_search_keys_hint": "Free at developer.adzuna.com. Keys are used only in this session (not saved).",
        "job_search_app_id_label": "Adzuna App ID",
        "job_search_app_key_label": "Adzuna App Key",
        "job_search_error": "Error searching jobs: {error}",
        # --- Footer ---
        "footer_disclaimer": (
            "This is a personal project, not a commercial solution. "
            "It was created as an idea to help people use artificial "
            "intelligence in their job search. "
            "It is not a professional service -- use it responsibly and "
            "always review AI-generated content."
        ),
    },
    "es": {
        # --- App shell ---
        "app_title": "CV Analyzer -- Asistente de Carrera con IA",
        "app_caption": "Analiza la compatibilidad de tu perfil con ofertas de empleo usando inteligencia artificial.",
        "profile_saved_success": "Perfil guardado en {name}",
        "analyze_button": "Analizar Compatibilidad",
        "error_profile_empty": "Por favor, introduce el perfil del candidato (texto o PDF).",
        "error_jd_empty": "Por favor, introduce la descripcion de la oferta.",
        "spinner_analyzing": "Analizando compatibilidad con IA...",
        "error_json_invalid": "La respuesta de la IA no esta en un formato valido. Intentalo de nuevo.",
        "error_rate_limit": "Limite de uso gratuito alcanzado (429). Espera unos minutos e intentalo de nuevo, o cambia de modelo/proveedor (p. ej., Gemini gratis u OpenAI con clave).",
        "error_unexpected": "Error inesperado durante el analisis: {error}",
        # --- Sidebar ---
        "sidebar_settings_header": "Configuracion",
        "provider_label": "Proveedor de IA",
        "model_label": "Modelo",
        "api_key_label": "Clave de API",
        "api_key_placeholder": "Pega tu clave de API aqui...",
        "api_key_info": "Tu clave solo se usa en esta sesion (no se guarda).",
        "api_key_required": "Por favor, introduce una clave de API para usar este proveedor.",
        "api_key_detected": "Clave reconocida: {provider}. Proveedor seleccionado automaticamente.",
        "profile_mgmt_header": "Gestionar Perfil",
        "saved_profiles_label": "Perfiles guardados",
        "new_profile_label": "-- Nuevo Perfil --",
        "profile_loaded": "Perfil '{name}' cargado.",
        "candidate_identifier_label": "Identificador del Candidato",
        "candidate_identifier_placeholder": "Ej: Juan Perez",
        "save_profile_button": "Guardar Perfil",
        "save_identifier_warning": "Indica un identificador para guardar.",
        # --- Input columns ---
        "candidate_profile_header": "Perfil del Candidato",
        "profile_source_label": "Fuente del perfil",
        "profile_mode_paste": "Pegar Texto",
        "profile_mode_upload": "Subir PDF",
        "upload_pdf_label": "Sube el CV en PDF",
        "upload_pdf_help": "Arrastra o selecciona un archivo PDF.",
        "pdf_success": "PDF procesado con exito ({chars} caracteres).",
        "profile_text_label": "Pega el texto del perfil / LinkedIn aqui",
        "profile_text_placeholder": "Pega aqui el contenido del curriculum o perfil de LinkedIn...",
        "job_description_header": "Descripcion de la Oferta",
        "job_url_label": "Enlace de la oferta",
        "job_url_placeholder": "https://...",
        "job_url_hint": "Pega el enlace de la oferta y haz clic en buscar para obtener la descripcion automaticamente, o pega la descripcion manualmente abajo.",
        "job_fetch_button": "Buscar descripcion desde el enlace",
        "spinner_fetching_job": "Buscando la descripcion de la oferta en el enlace...",
        "job_fetch_success": "Descripcion obtenida del enlace ({chars} caracteres).",
        "job_fetch_failed": "No se pudo obtener la descripcion desde el enlace (el sitio puede bloquear accesos automatizados). Pega la descripcion manualmente.",
        "job_description_label": "Pega la descripcion completa de la oferta",
        "job_description_placeholder": "Pega aqui la descripcion de la oferta...",
        # --- Tailored CV offer ---
        "tailored_cv_header": "CV enfocado en esta oferta",
        "tailored_cv_caption": "Segun el analisis, genera un CV optimizado exactamente para esta vacante (ATS) usando el CV Builder.",
        "tailored_cv_button": "Generar CV enfocado en esta oferta",
        "tailored_cv_spinner": "Generando CV enfocado en la oferta...",
        "tailored_cv_success": "¡CV generado con exito! Revisalo abajo o descarga el HTML.",
        "reanalyze_button": "Re-analizar con este CV",
        "reanalyze_spinner": "Re-analizando CV generado...",
        "progress_send": "Enviando perfil y oferta a la IA...",
        "progress_analyzing": "La IA esta analizando la compatibilidad...",
        "progress_parsing": "Construyendo el resultado...",
        "progress_cv_tailoring": "La IA esta creando el CV enfocado en la oferta...",
        "progress_cv_writing": "Escribiendo secciones del CV...",
        # --- Results ---
        "results_header": "Resultado del Analisis",
        "compatibility_label": "Compatibilidad",
        "score_progress_text": "Puntuacion: {score}%",
        "score_excellent": "Compatibilidad excelente",
        "score_good": "Buena compatibilidad",
        "score_low": "Compatibilidad baja",
        "job_reference_caption": "Referencia de la oferta: [{url}]({url})",
        "strengths_header": "Puntos Fuertes",
        "gaps_header": "Carencias",
        "suggestions_header": "Sugerencias de Mejora",
        "json_expander_label": "JSON completo del analisis",
        "disclaimer_text": (
            "Aviso: Este analisis es generado por IA y puede contener errores. "
            "Diferentes modelos y proveedores pueden producir puntuaciones y "
            "valoraciones distintas para el mismo perfil. Usalo como referencia, "
            "no como veredicto final."
        ),
        # --- Backend / errors ---
        "unknown_provider_error": "Proveedor desconocido: {provider}",
        "missing_api_key_error": "Por favor, introduce una clave de API para el proveedor {provider}.",
        "no_json_found_error": "No se encontro ningun objeto JSON en la respuesta.",
        "pdf_extract_error": "Error al extraer texto del PDF: {error}",
        # --- CV Builder ---
        "tab_analyzer": "Analisis de CV",
        "tab_builder": "Creador de CV",
        "cv_builder_header": "Creador de CV",
        "cv_builder_caption": "Pega tu perfil de LinkedIn y genera un CV profesional con diseno personalizado.",
        "cv_layout_label": "Elige el diseno",
        "cv_layout_advanced": "Avanzado (dos columnas)",
        "cv_layout_simple": "Simple (una columna)",
        "cv_profile_input_header": "Perfil del Candidato",
        "cv_profile_source": "Fuente del perfil",
        "cv_profile_text_label": "Pega el texto del perfil / LinkedIn aqui",
        "cv_profile_text_placeholder": "Pega aqui tu LinkedIn, curriculum o perfil profesional...",
        "cv_photo_label": "Foto de perfil (opcional)",
        "cv_photo_help": "Arrastra o selecciona una foto para el CV Avanzado.",
        "cv_preview_header": "Vista previa del CV",
        "cv_build_button": "Generar CV",
        "cv_spinner_building": "Analizando el perfil y generando CV...",
        "cv_download_html": "Descargar CV (HTML)",
        "cv_download_json": "Descargar datos (JSON)",
        "cv_preview_placeholder": "Pega tu perfil y haz clic en 'Generar CV' para ver la vista previa.",
        "cv_enhance_label": "Mejorar con IA",
        "cv_enhance_help": "Usa IA para mejorar el resumen, las vinetas y la redaccion del CV.",
        "cv_spinner_enhance": "Mejorando el contenido del CV con IA...",
        "cv_print_hint": "Consejo: Usa Ctrl+P (o Cmd+P) en el HTML descargado para guardar como PDF.",
        "cv_language_note": "El CV se generara en {language}.",
        # --- Job Search ---
        "tab_job_search": "Busqueda de Empleo",
        "job_search_header": "Busqueda de Empleo",
        "job_search_caption": "Busca ofertas reales via la API de Adzuna y envia una oferta directo al analisis de compatibilidad.",
        "job_search_config_header": "Configuracion de la busqueda",
        "job_search_keyword_label": "Palabras clave",
        "job_search_keyword_placeholder": "Ej.: Python, Data Analyst, Product Manager",
        "job_search_location_label": "Ubicacion (opcional)",
        "job_search_location_placeholder": "Ej.: Sao Paulo, Lisboa, remoto",
        "job_search_country_label": "Pais",
        "job_search_results_label": "Resultados por pagina",
        "job_search_button": "Buscar Empleos",
        "job_search_spinner": "Buscando empleos en Adzuna...",
        "job_search_keyword_required": "Introduce palabras clave para buscar empleos.",
        "job_search_no_keys": "Para buscar empleos, introduce tu Adzuna App ID y App Key en la barra lateral. Las claves son gratis en developer.adzuna.com y solo se usan en esta sesion.",
        "job_search_no_results": "No se encontraron empleos con esos criterios. Prueba otras palabras clave o ubicacion.",
        "job_search_count": "{count} empleo(s) encontrado(s). Mostrando {shown}.",
        "job_search_use_button": "Usar para analisis",
        "job_search_use_success": "Descripcion de la oferta cargada. Ve a la pestana 'Analisis de CV' y haz clic en Analizar Compatibilidad.",
        "job_search_posted": "Publicado {date}",
        "job_search_open": "Abrir empleo en el sitio",
        "job_search_keys_header": "Busqueda de Empleo -- Claves Adzuna",
        "job_search_keys_hint": "Gratis en developer.adzuna.com. Las claves solo se usan en esta sesion (no se guardan).",
        "job_search_app_id_label": "Adzuna App ID",
        "job_search_app_key_label": "Adzuna App Key",
        "job_search_error": "Error al buscar empleos: {error}",
        # --- Footer ---
        "footer_disclaimer": (
            "Este es un proyecto personal y no una solucion comercial. "
            "Fue creado como una idea para ayudar a las personas a usar "
            "inteligencia artificial en la busqueda de empleo. "
            "No es un servicio profesional -- usalo con responsabilidad y "
            "revisa siempre el contenido generado por IA."
        ),
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
