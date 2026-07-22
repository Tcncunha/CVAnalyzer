"""
Streamlit UI components — sidebar, input columns, and result rendering.
"""

import streamlit as st

from config import (
    DEFAULT_MODEL,
    DEFAULT_PROFILE_LABEL,
    DEFAULT_PROVIDER,
    MODELS,
    PROVIDERS,
)
from pdf_extractor import extract_text_from_pdf
from profile_manager import list_saved_profiles, load_profile, save_profile


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar() -> tuple[str, dict | None, str, str]:
    """Render sidebar controls and return (identifier, loaded_data, provider, model)."""
    with st.sidebar:
        st.header("⚙️ Configurações")

        # --- Provider ---
        provider_keys = list(PROVIDERS.keys())
        provider_labels = [PROVIDERS[k]["name"] for k in provider_keys]
        default_prov_idx = provider_keys.index(DEFAULT_PROVIDER)

        chosen_prov_label = st.selectbox("Provedor de IA", provider_labels, index=default_prov_idx)
        selected_provider = provider_keys[provider_labels.index(chosen_prov_label)]

        # --- Model (dynamic based on provider) ---
        model_dict = MODELS.get(selected_provider, {})
        model_keys = list(model_dict.keys())
        model_labels = list(model_dict.values())

        default_model_idx = model_keys.index(DEFAULT_MODEL) if DEFAULT_MODEL in model_keys else 0

        chosen_model_label = st.selectbox("Modelo", model_labels, index=default_model_idx)
        selected_model = model_keys[model_labels.index(chosen_model_label)]

        st.divider()
        st.header("📋 Gerenciar Perfil")

        saved = list_saved_profiles()
        options = [DEFAULT_PROFILE_LABEL] + saved

        selected = st.selectbox("Perfis salvos", options, index=0)

        loaded_data = None
        if selected != DEFAULT_PROFILE_LABEL:
            loaded_data = load_profile(selected)
            if loaded_data:
                st.success(f"Perfil '{selected}' carregado.")

        identifier = st.text_input(
            "Identificador do Candidato",
            value="" if selected == DEFAULT_PROFILE_LABEL else selected,
            placeholder="Ex: João Silva",
        )

        save_clicked = st.button("💾 Salvar Perfil", use_container_width=True)

        if save_clicked:
            if not identifier.strip():
                st.warning("Informe um identificador para salvar.")
            else:
                st.session_state["_save_requested"] = True

    return identifier, loaded_data, selected_provider, selected_model


# ---------------------------------------------------------------------------
# Input Columns
# ---------------------------------------------------------------------------

def render_input_columns() -> tuple[str, str, str]:
    """Render the two-column input area. Returns (profile_text, job_description, job_url)."""
    col1, col2 = st.columns(2)

    # --- Column 1: Candidate Profile ---
    with col1:
        st.subheader("👤 Perfil do Candidato")

        input_mode = st.radio(
            "Fonte do perfil",
            ["Colar Texto", "Upload PDF"],
            horizontal=True,
            key="profile_mode",
        )

        profile_text = ""

        if input_mode == "Upload PDF":
            uploaded_pdf = st.file_uploader(
                "Envie o CV em PDF",
                type=["pdf"],
                help="Arraste ou selecione um arquivo PDF.",
            )
            if uploaded_pdf is not None:
                try:
                    profile_text = extract_text_from_pdf(uploaded_pdf)
                    st.success(
                        f"PDF processado com sucesso ({len(profile_text)} caracteres)."
                    )
                except RuntimeError as err:
                    st.error(str(err))
        else:
            profile_text = st.text_area(
                "Cole o texto do perfil / LinkedIn aqui",
                height=350,
                placeholder="Cole aqui o conteúdo do currículo ou perfil do LinkedIn...",
                key="profile_text_area",
            )

    # --- Column 2: Job Description ---
    with col2:
        st.subheader("💼 Descrição da Vaga")

        job_url = st.text_input(
            "Link da vaga (referência)",
            placeholder="https://...",
            key="job_url_input",
        )

        job_description = st.text_area(
            "Cole a descrição completa da vaga",
            height=350,
            placeholder="Cole aqui a descrição da vaga...",
            key="jd_text_area",
        )

    return profile_text, job_description, job_url


# ---------------------------------------------------------------------------
# Results Display
# ---------------------------------------------------------------------------

def render_results(results: dict, job_url: str) -> None:
    """Render the analysis results using Streamlit components."""
    st.divider()
    st.header("📊 Resultado da Análise")

    # --- Score ---
    score = max(0, min(100, int(results.get("overall_score", 0))))

    score_col, progress_col = st.columns([1, 3])
    with score_col:
        st.metric(label="Compatibilidade", value=f"{score}/100")
    with progress_col:
        st.progress(score / 100, text=f"Score: {score}%")

    if job_url:
        st.caption(f"Referência da vaga: [{job_url}]({job_url})")

    st.divider()

    # --- Strengths, Gaps, Suggestions ---
    col_strengths, col_gaps, col_suggestions = st.columns(3)

    with col_strengths:
        st.subheader("✅ Pontos Fortes")
        for item in results.get("pontos_fortes", []):
            st.markdown(f"- {item}")

    with col_gaps:
        st.subheader("⚠️ Lacunas")
        for item in results.get("lacunas", []):
            st.markdown(f"- {item}")

    with col_suggestions:
        st.subheader("💡 Sugestões de Melhoria")
        for item in results.get("sugestoes_melhoria", []):
            st.markdown(f"- {item}")

    # --- Raw JSON expander ---
    with st.expander("🔎 JSON completo da análise"):
        st.json(results)

    # --- Disclaimer ---
    st.divider()
    st.caption(
        "⚠️ **Aviso:** Esta análise é gerada por IA e pode conter erros. "
        "Diferentes modelos e provedores podem resultar em scores e "
        "avaliações distintos para o mesmo perfil. Use como referência, "
        "não como veredicto final use como base a media que eles derem por exemplo 45 uma e 65 a media e 55."
    )
