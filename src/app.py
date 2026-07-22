"""
CV Analyzer — AI-Driven Career Assistant
=========================================
Entry point. Run with:  streamlit run src/app.py
"""

import json

import streamlit as st

from analyzer import analyze_profile
from config import APP_ICON, APP_TITLE
from profile_manager import save_profile
from ui import render_input_columns, render_results, render_sidebar


def main():
    st.set_page_config(page_title="CV Analyzer", page_icon=APP_ICON, layout="wide")
    st.title(f"{APP_ICON} {APP_TITLE}")
    st.caption(
        "Analise a compatibilidade do seu perfil com vagas de emprego usando inteligência artificial."
    )

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
            st.sidebar.success(f"Perfil salvo em {path.name}")
            st.rerun()

    # Analyze button
    st.divider()
    analyze_clicked = st.button(
        "🔍 Analisar Compatibilidade", type="primary", use_container_width=True
    )

    if analyze_clicked:
        if not profile_text.strip():
            st.error("Por favor, insira o perfil do candidato (texto ou PDF).")
            return
        if not job_description.strip():
            st.error("Por favor, insira a descrição da vaga.")
            return

        try:
            with st.spinner("Analisando compatibilidade com IA..."):
                results = analyze_profile(
                    profile_text, job_description, selected_provider, selected_model
                )
            render_results(results, job_url)
        except EnvironmentError as exc:
            st.error(str(exc))
        except json.JSONDecodeError:
            st.error(
                "A resposta da IA não está em formato JSON válido. Tente novamente."
            )
        except Exception as exc:
            st.error(f"Erro inesperado durante a análise: {exc}")


if __name__ == "__main__":
    main()
