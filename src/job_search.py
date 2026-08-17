"""
Adzuna job search client -- real job listings via the free Adzuna API.

Get free App ID / App Key at https://developer.adzuna.com
Keys are session-only: entered in the sidebar, never persisted to disk.
"""

import re

import requests
import streamlit as st

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"

COUNTRIES = {
    "br": "Brasil",
    "us": "United States",
    "gb": "United Kingdom",
    "ca": "Canada",
    "de": "Germany",
    "fr": "France",
    "es": "Spain",
    "it": "Italy",
    "nl": "Netherlands",
    "au": "Australia",
    "in": "India",
}

DEFAULT_COUNTRY = "br"

_CURRENCY = {
    "br": "R$",
    "us": "$",
    "gb": "£",
    "ca": "C$",
    "de": "€",
    "fr": "€",
    "es": "€",
    "it": "€",
    "nl": "€",
    "au": "A$",
    "in": "₹",
}

MAX_DESCRIPTION_CHARS = 320


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


def _clean_text(text: str) -> str:
    """Collapse whitespace and truncate long descriptions."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) > MAX_DESCRIPTION_CHARS:
        text = text[:MAX_DESCRIPTION_CHARS].rstrip() + "..."
    return text


def _format_salary(item: dict, country: str) -> str:
    """Format the Adzuna salary range with the country's currency symbol."""
    symbol = _CURRENCY.get(country, "$")
    salary_min = item.get("salary_min") or -1
    salary_max = item.get("salary_max") or -1
    if salary_min < 0 and salary_max < 0:
        return ""
    if salary_min < 0:
        return f"{symbol} {salary_max:,.0f}"
    if salary_max < 0:
        return f"{symbol} {salary_min:,.0f}"
    return f"{symbol} {salary_min:,.0f} - {symbol} {salary_max:,.0f}"


def _display_name(value, key: str) -> str:
    """Extract display_name from an Adzuna nested dict (company/location/category)."""
    if isinstance(value, dict):
        return value.get("display_name", "")
    return ""


def fetch_jobs(
    query: str,
    location: str,
    country: str,
    results_per_page: int,
    app_id: str,
    app_key: str,
) -> tuple[list[dict], int]:
    """Search Adzuna and return (normalized jobs, total count)."""
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": results_per_page,
        "what": query,
        "content-type": "application/json",
    }
    if location.strip():
        params["where"] = location.strip()

    resp = requests.get(
        f"{ADZUNA_BASE_URL}/{country}/search/1", params=params, timeout=20
    )
    resp.raise_for_status()
    payload = resp.json()

    jobs = []
    for idx, item in enumerate(payload.get("results", [])):
        jobs.append(
            {
                "id": item.get("id", idx),
                "title": item.get("title", ""),
                "company": _display_name(item.get("company"), "company"),
                "location": _display_name(item.get("location"), "location"),
                "category": _display_name(item.get("category"), "category"),
                "description": _clean_text(item.get("description", "")),
                "url": item.get("redirect_url", ""),
                "salary": _format_salary(item, country),
                "created": str(item.get("created", ""))[:10],
            }
        )

    return jobs, int(payload.get("count", len(jobs)))
