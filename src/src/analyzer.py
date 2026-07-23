"""
Multi-provider analysis engine (OpenCode Zen + Gemini via OpenAI-compatible endpoint).
"""

import json
import re

from openai import OpenAI

import i18n
from config import ANALYSIS_PROMPT, MODELS, PROVIDERS, get_api_key


def _parse_json_from_text(text: str) -> dict:
    """Extract a JSON object from text that may contain markdown or extra content."""
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group(0))
    raise json.JSONDecodeError(i18n.t("no_json_found_error"), text, 0)


def analyze_profile(
    profile_text: str,
    job_description: str,
    provider: str,
    model: str,
    language: str | None = None,
) -> dict:
    """Send profile + JD to the selected provider and return structured JSON.

    `language` controls the language the AI writes the analysis fields in
    (defaults to the current UI language, see i18n.prompt_language()).
    """
    cfg = PROVIDERS[provider]
    api_key = get_api_key(provider)
    client = OpenAI(api_key=api_key, base_url=cfg["base_url"])

    if language is None:
        language = i18n.prompt_language()

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
