"""
Adzuna job search client -- real job listings via the free Adzuna API.

Get free App ID / App Key at https://developer.adzuna.com
Keys are session-only: entered in the sidebar, never persisted to disk.
"""

import streamlit as st

from job_providers import (
    AdzunaProvider,
    MAX_DESCRIPTION_CHARS,
    _clean_text,
)

DEFAULT_COUNTRY = "br"

COUNTRIES = {
    "at": "Austria",
    "au": "Australia",
    "be": "Belgium",
    "br": "Brasil",
    "ca": "Canada",
    "ch": "Switzerland",
    "cz": "Czech Republic",
    "de": "Germany",
    "dk": "Denmark",
    "es": "Spain",
    "fi": "Finland",
    "fr": "France",
    "gb": "United Kingdom",
    "hu": "Hungary",
    "ie": "Ireland",
    "in": "India",
    "it": "Italy",
    "mx": "Mexico",
    "nl": "Netherlands",
    "no": "Norway",
    "nz": "New Zealand",
    "pl": "Poland",
    "pt": "Portugal",
    "ro": "Romania",
    "se": "Sweden",
    "sg": "Singapore",
    "us": "United States",
    "za": "South Africa",
}


def get_adzuna_keys() -> tuple[str, str]:
    """Return (app_id, app_key) from session state. Raises ValueError if missing."""
    app_id = (
        st.session_state.get("adzuna_app_id", "").strip()
        or st.session_state.get("adzuna_app_id_w", "").strip()
    )
    app_key = (
        st.session_state.get("adzuna_app_key", "").strip()
        or st.session_state.get("adzuna_app_key_w", "").strip()
    )
    if not app_id or not app_key:
        raise ValueError("Adzuna App ID / App Key missing.")
    return app_id, app_key


def fetch_jobs(
    query: str,
    location: str,
    country: str,
    results_per_page: int,
    app_id: str,
    app_key: str,
) -> tuple[list[dict], int]:
    """Search Adzuna and return (normalized jobs, total count)."""
    config = {
        "query": query,
        "location": location,
        "country": country,
        "results_per_page": results_per_page,
        "adzuna_app_id": app_id,
        "adzuna_app_key": app_key,
    }
    provider = AdzunaProvider(config)
    payload = provider.search()
    jobs = provider.normalize(payload)
    total = int(payload.get("count", len(jobs))) if isinstance(payload, dict) else len(jobs)
    return jobs, total
