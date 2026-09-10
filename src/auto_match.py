"""
Auto Match — pure service layer for bulk job search + AI compatibility scoring.

Pipeline: Adzuna job search → full job description fetch → per-job AI
analysis → structured results with status and score.

This module is UI-free and never touches Streamlit session state, so it is
safe to run inside a background thread (see progress_utils.run_with_progress).
All results are volatile — nothing is persisted to disk.
"""

import logging
import time
from typing import Callable

from config import ANALYSIS_PROMPT
from job_fetcher import fetch_job_description
from job_search import DEFAULT_COUNTRY, fetch_jobs
from providers import DEFAULT_MODEL, DEFAULT_PROVIDER, analyze_profile

log = logging.getLogger("cv-analyzer.auto_match")

MAX_RESULTS = 50
DEFAULT_THRESHOLD = 60
MIN_THRESHOLD = 30
MAX_THRESHOLD = 90

_STATUS_ANALYZED = {"matched", "below_threshold", "failed"}
_STATUS_FAILED = {"failed", "no_url", "no_jd"}


def _is_transient_failure(exc: Exception) -> bool:
    """Detect transient API errors (rate limit / server / connection) worth retrying."""
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if isinstance(status, int) and (status == 429 or 500 <= status < 600):
        return True
    text = str(exc).lower()
    return "429" in text or "rate limit" in text or "timed out" in text or "timeout" in text


def _string_list(value) -> list[str]:
    """Coerce a raw AI list field into a clean list of strings."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


def _validate_inputs(
    profile_text: str,
    keyword: str,
    adzuna_app_id: str,
    adzuna_app_key: str,
    ai_api_key: str,
) -> None:
    if not profile_text.strip():
        raise ValueError("Profile text is required for auto match.")
    if not keyword.strip():
        raise ValueError("A search keyword is required for auto match.")
    if not adzuna_app_id.strip() or not adzuna_app_key.strip():
        raise ValueError("Adzuna App ID and App Key are required for auto match.")
    if not ai_api_key.strip():
        raise ValueError("An AI provider API key is required for auto match.")


def _build_result(
    job: dict,
    status: str,
    jd_source: str,
    full_description: str,
    analysis: dict | None,
) -> dict:
    """Pack one normalized AutoMatchResult for a single job."""
    return {
        "job": {
            "id": str(job.get("id", "")),
            "title": str(job.get("title", "")),
            "company": str(job.get("company", "")),
            "location": str(job.get("location", "")),
            "category": str(job.get("category", "")),
            "description": str(job.get("description", "")),
            "full_description": full_description,
            "url": str(job.get("url", "")),
            "salary": str(job.get("salary", "")),
            "created": str(job.get("created", "")),
            "jd_source": jd_source,
        },
        "analysis": analysis,
        "status": status,
    }


def _analyze_with_ai(
    profile_text: str,
    jd_text: str,
    provider: str,
    model: str,
    api_key: str,
    language: str,
) -> dict | None:
    """Run one AI analysis; return a normalized dict or None on any failure."""
    raw = None
    for attempt in range(2):
        try:
            raw = analyze_profile(
                profile_text,
                jd_text,
                provider,
                model,
                ANALYSIS_PROMPT,
                language,
                api_key=api_key,
            )
            break
        except Exception as exc:
            if attempt == 0 and _is_transient_failure(exc):
                log.warning(
                    "Transient AI failure (attempt 1), retrying in 1.5s: %s", exc
                )
                time.sleep(1.5)
                continue
            log.warning(
                "AI analysis failed for provider=%s model=%s: %s", provider, model, exc
            )
            return None
    if not isinstance(raw, dict):
        log.warning("AI analysis returned non-dict payload: %r", type(raw).__name__)
        return None
    try:
        score = int(float(raw.get("overall_score")))
    except (TypeError, ValueError):
        log.warning("AI analysis missing a valid overall_score")
        return None
    analysis = {
        "overall_score": max(0, min(100, score)),
        "pontos_fortes": _string_list(raw.get("pontos_fortes"))[:3],
        "lacunas": _string_list(raw.get("lacunas"))[:3],
        "sugestoes_melhoria": _string_list(raw.get("sugestoes_melhoria")),
    }
    if isinstance(raw.get("keyword_analysis"), dict):
        analysis["keyword_analysis"] = raw["keyword_analysis"]
    return analysis


def _analyze_job(
    job: dict,
    profile_text: str,
    threshold: int,
    provider: str,
    model: str,
    api_key: str,
    language: str,
) -> dict:
    """Classify a single job into one of the five AutoMatch statuses."""
    url = str(job.get("url", "")).strip()
    full_description = ""

    if not url:
        return _build_result(job, "no_url", "empty", "", None)

    try:
        full_description = (fetch_job_description(url) or "").strip()
    except Exception as exc:
        log.warning("Full JD fetch failed for job %s: %s", job.get("id"), exc)

    if full_description:
        jd_source = "fetched"
        jd_text = full_description
    else:
        jd_source = "snippet"
        jd_text = str(job.get("description") or "").strip()

    if not jd_text:
        return _build_result(job, "no_jd", "empty", "", None)

    analysis = _analyze_with_ai(profile_text, jd_text, provider, model, api_key, language)
    if analysis is None:
        return _build_result(job, "failed", jd_source, full_description, None)

    status = "matched" if analysis["overall_score"] >= threshold else "below_threshold"
    return _build_result(job, status, jd_source, full_description, analysis)


def run_auto_match(
    profile_text: str = "",
    keyword: str = "",
    location: str = "",
    country: str = DEFAULT_COUNTRY,
    results_per_page: int = 20,
    threshold: int = DEFAULT_THRESHOLD,
    adzuna_app_id: str = "",
    adzuna_app_key: str = "",
    ai_api_key: str = "",
    ai_provider: str = DEFAULT_PROVIDER,
    ai_model: str = DEFAULT_MODEL,
    language: str = "English",
    progress_callback: Callable[[int, int, str], None] | None = None,
    **aliases,
) -> dict:
    """Run a full auto-match cycle and return ranked results.

    Fetches jobs from Adzuna, fetches full descriptions where possible,
    analyzes each job against the profile with AI, and classifies every
    result as matched / below_threshold / failed / no_url / no_jd.

    Accepts both the canonical parameter names and the aliases used by
    auto_match_ui.py (cv_text, app_id, app_key, api_key, provider, model).

    Calls progress_callback(completed, total, job_title) as each job is
    processed. Returns a volatile summary dict — nothing is persisted.
    """
    profile_text = aliases.pop("cv_text", profile_text)
    adzuna_app_id = aliases.pop("app_id", adzuna_app_id)
    adzuna_app_key = aliases.pop("app_key", adzuna_app_key)
    ai_api_key = aliases.pop("api_key", ai_api_key)
    ai_provider = aliases.pop("provider", ai_provider)
    ai_model = aliases.pop("model", ai_model)

    _validate_inputs(profile_text, keyword, adzuna_app_id, adzuna_app_key, ai_api_key)

    threshold = _clamp(threshold, MIN_THRESHOLD, MAX_THRESHOLD)
    results_per_page = _clamp(results_per_page, 1, MAX_RESULTS)

    log.info(
        "Auto match start — keyword=%s country=%s results_requested=%d threshold=%d",
        keyword.strip(),
        country,
        results_per_page,
        threshold,
    )

    try:
        jobs, _ = fetch_jobs(
            keyword.strip(),
            location,
            country,
            results_per_page,
            adzuna_app_id.strip(),
            adzuna_app_key.strip(),
        )
    except Exception as exc:
        log.warning("Adzuna search failed for keyword=%s: %s", keyword.strip(), exc)
        raise ValueError(
            "Adzuna search failed. Check the App ID/Key or try again later."
        ) from exc

    results = []
    total = len(jobs)
    for index, job in enumerate(jobs, start=1):
        results.append(
            _analyze_job(
                job,
                profile_text.strip(),
                threshold,
                ai_provider,
                ai_model,
                ai_api_key.strip(),
                language,
            )
        )
        if progress_callback is not None:
            progress_callback(index, total, str(job.get("title", "")))

    matched = sum(1 for r in results if r["status"] == "matched")
    below_threshold = sum(1 for r in results if r["status"] == "below_threshold")
    analyzed = sum(1 for r in results if r["status"] in _STATUS_ANALYZED)
    failed = sum(1 for r in results if r["status"] in _STATUS_FAILED)

    log.info(
        "Auto match done — found=%d analyzed=%d matched=%d below=%d failed=%d",
        total,
        analyzed,
        matched,
        below_threshold,
        failed,
    )

    return {
        "results": results,
        "total_found": total,
        "total_analyzed": analyzed,
        "total_failed": failed,
        "total_below_threshold": below_threshold,
        "total_matched": matched,
    }