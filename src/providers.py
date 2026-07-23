"""
AI provider definitions, model registry, API key management, and analysis engine.

Supported providers:
  - OpenCode Zen (free models, no key required)
  - Google Gemini
  - OpenAI
  - Anthropic (Claude)
"""

import json
import os
import re

import anthropic
import streamlit as st
from openai import OpenAI


# =============================================================================
# PROVIDER & MODEL REGISTRY
# =============================================================================

PROVIDERS = {
    "opencode_zen": {
        "name": "OpenCode Zen (Free Models)",
        "base_url": "https://opencode.ai/zen/v1",
        "env_key": "OPENCODE_ZEN_API_KEY",
        "json_mode": False,
        "needs_key": False,
    },
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "env_key": "GEMINI_API_KEY",
        "json_mode": True,
        "needs_key": True,
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "json_mode": True,
        "needs_key": True,
    },
    "anthropic": {
        "name": "Anthropic (Claude)",
        "base_url": "https://api.anthropic.com/v1",
        "env_key": "ANTHROPIC_API_KEY",
        "json_mode": False,
        "needs_key": True,
    },
}

MODELS = {
    "opencode_zen": {
        "big-pickle": "Big Pickle (Free)",
        "deepseek-v4-flash-free": "DeepSeek V4 Flash (Free)",
        "mimo-v2.5-free": "MiMo V2.5 (Free)",
        "north-mini-code-free": "North Mini Code (Free)",
        "nemotron-3-ultra-free": "Nemotron 3 Ultra (Free)",
    },
    "gemini": {
        "gemini-2.5-flash-preview-04-17": "Gemini 2.5 Flash (Preview)",
        "gemini-2.0-flash": "Gemini 2.0 Flash",
        "gemini-2.0-flash-lite": "Gemini 2.0 Flash Lite",
        "gemini-1.5-flash": "Gemini 1.5 Flash",
        "gemini-1.5-pro": "Gemini 1.5 Pro",
    },
    "openai": {
        "gpt-4o": "GPT-4o",
        "gpt-4o-mini": "GPT-4o Mini",
        "gpt-4-turbo": "GPT-4 Turbo",
        "gpt-3.5-turbo": "GPT-3.5 Turbo",
    },
    "anthropic": {
        "claude-sonnet-4-20250514": "Claude Sonnet 4",
        "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet",
        "claude-3-5-haiku-20241022": "Claude 3.5 Haiku",
        "claude-3-opus-20240229": "Claude 3 Opus",
    },
}

DEFAULT_PROVIDER = "opencode_zen"
DEFAULT_MODEL = "big-pickle"


# =============================================================================
# API KEY MANAGEMENT (session-only, never persisted)
# =============================================================================

def get_api_key(provider: str) -> str:
    """Return the API key for the given provider from session state or env.

    Priority: session state (user-entered) > environment variable.
    """
    cfg = PROVIDERS.get(provider)
    if not cfg:
        raise ValueError(f"Unknown provider: {provider}")

    # 1. Check session state (user entered via sidebar)
    session_key = f"_api_key_{provider}"
    key = st.session_state.get(session_key, "").strip()
    if key:
        return key

    # 2. Fall back to environment variable
    key = os.getenv(cfg["env_key"], "").strip()
    if key:
        return key

    return ""


# =============================================================================
# ANALYSIS ENGINE
# =============================================================================

def _parse_json_from_text(text: str) -> dict:
    """Extract a JSON object from text that may contain markdown or extra content."""
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group(0))
    raise json.JSONDecodeError("No JSON object found in the response.", text, 0)


def analyze_profile(
    profile_text: str,
    job_description: str,
    provider: str,
    model: str,
    prompt: str,
    language: str = "English",
) -> dict:
    """Send profile + JD to the selected provider and return structured JSON."""
    cfg = PROVIDERS[provider]
    api_key = get_api_key(provider)

    user_content = prompt.format(
        profile=profile_text,
        job_description=job_description,
        language=language,
    )

    # --- Anthropic (different API format) ---
    if provider == "anthropic":
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0.3,
            system="You always respond with valid JSON only.",
            messages=[{"role": "user", "content": user_content}],
        )
        raw = response.content[0].text
        return _parse_json_from_text(raw)

    # --- OpenAI-compatible providers (Zen, Gemini, OpenAI) ---
    client = OpenAI(api_key=api_key, base_url=cfg["base_url"])
    messages = [
        {"role": "system", "content": "You always respond with valid JSON only."},
        {"role": "user", "content": user_content},
    ]

    if cfg["json_mode"]:
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=messages,
        )
        raw = response.choices[0].message.content
        return json.loads(raw)

    # Non-JSON-mode: try response_format, fall back to text parsing
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
