"""
Legacy-compatible wrapper around the shared analysis engine in providers.py.

Kept for backward compatibility; all real logic (provider registry, API key
handling, JSON parsing, language guard) lives in providers.py. New code should
import directly from providers instead.
"""

from config import ANALYSIS_PROMPT
from providers import (
    MODELS,
    PROVIDERS,
    _parse_json_from_text,
    analyze_profile as _analyze_profile,
    get_api_key,
)


def analyze_profile(
    profile_text: str, job_description: str, provider: str, model: str
) -> dict:
    """Send profile + JD to the selected provider and return structured JSON.

    Backward-compatible signature: delegates to providers.analyze_profile using
    the master analysis prompt from config.
    """
    return _analyze_profile(
        profile_text,
        job_description,
        provider,
        model,
        prompt=ANALYSIS_PROMPT,
    )


__all__ = [
    "MODELS",
    "PROVIDERS",
    "get_api_key",
    "analyze_profile",
    "_parse_json_from_text",
]