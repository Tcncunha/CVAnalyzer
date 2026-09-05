"""
AI provider definitions, model registry, API key management, and analysis engine.

Supported providers:
  - OpenCode Zen (free models)
  - Google Gemini
  - OpenAI
  - Anthropic (Claude)
  - GitHub Copilot
"""

import json
import logging
import os
import re
import time

import anthropic
import streamlit as st
from openai import OpenAI

log = logging.getLogger("cv-analyzer.providers")


# =============================================================================
# PROVIDER & MODEL REGISTRY
# =============================================================================

PROVIDERS = {
    "opencode_zen": {
        "name": "OpenCode Zen (Free Models)",
        "base_url": "https://opencode.ai/zen/v1",
        "env_key": "OPENCODE_ZEN_API_KEY",
        "json_mode": False,
        "needs_key": True,
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
    "copilot": {
        "name": "GitHub Copilot",
        "base_url": "https://api.githubcopilot.com",
        "env_key": "COPILOT_API_KEY",
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
        "nemotron-3.5-lightning-free": "Nemotron 3.5 Lightning (Free)",
        "nemotron-3-ultra-free": "Nemotron 3 Ultra (Free)",
        "deepseek-v4-flash-free": "DeepSeek V4 Flash (Free)",
        "mimo-v2.5-free": "MiMo V2.5 (Free)",
        "ling-3.0-flash-fin-free": "Ling 3.0 Flash Fin (Free)",
        "muse-spark-1.3-contributor-free": "Muse Spark 1.3 (Free)",
        "muse-spark-1.2-contributor-free": "Muse Spark 1.2 (Free)",
    },
    "gemini": {
        "gemini-3.8-flash": "Gemini 3.8 Flash",
        "gemini-3.7-flash": "Gemini 3.7 Flash",
        "gemini-3.6-flash": "Gemini 3.6 Flash",
        "gemini-3.5-flash": "Gemini 3.5 Flash",
        "gemini-3.5-flash-lite": "Gemini 3.5 Flash Lite",
        "gemini-3.1-pro": "Gemini 3.1 Pro",
        "gemini-3-flash": "Gemini 3 Flash",
        "gemini-2.5-pro": "Gemini 2.5 Pro",
        "gemini-2.5-flash": "Gemini 2.5 Flash",
    },
    "openai": {
        "gpt-5.6-sol": "GPT-5.6 Sol",
        "gpt-5.6-terra": "GPT-5.6 Terra",
        "gpt-5.6-luna": "GPT-5.6 Luna",
        "gpt-5.5": "GPT-5.5",
        "gpt-5.4": "GPT-5.4",
        "gpt-5.4-mini": "GPT-5.4 Mini",
        "gpt-5.4-nano": "GPT-5.4 Nano",
        "gpt-5": "GPT-5",
    },
    "anthropic": {
        "claude-fable-5": "Claude Fable 5",
        "claude-opus-5": "Claude Opus 5",
        "claude-sonnet-5": "Claude Sonnet 5",
        "claude-haiku-4-5": "Claude Haiku 4.5",
        "claude-opus-4-8": "Claude Opus 4.8",
        "claude-opus-4-7": "Claude Opus 4.7",
        "claude-sonnet-4-6": "Claude Sonnet 4.6",
        "claude-sonnet-4-5": "Claude Sonnet 4.5",
    },
    "copilot": {
        "gpt-5.6-sol": "GPT-5.6 Sol",
        "gpt-5.6-terra": "GPT-5.6 Terra",
        "gpt-5.6-luna": "GPT-5.6 Luna",
        "gpt-5.5": "GPT-5.5",
        "gpt-5.4": "GPT-5.4",
        "gpt-5.4-mini": "GPT-5.4 Mini",
        "claude-sonnet-5": "Claude Sonnet 5",
        "claude-opus-5": "Claude Opus 5",
        "claude-haiku-4-5": "Claude Haiku 4.5",
        "gemini-3.8-flash": "Gemini 3.8 Flash",
        "grok-4.6": "Grok 4.6",
        "kimi-k3": "Kimi K3",
    },
}

DEFAULT_PROVIDER = "opencode_zen"
DEFAULT_MODEL = "big-pickle"

# Best default model per provider, used when a provider is selected (or
# auto-detected from the API key).
DEFAULT_MODEL_BY_PROVIDER = {
    "opencode_zen": "big-pickle",
    "gemini": "gemini-3.8-flash",
    "openai": "gpt-5.6-sol",
    "anthropic": "claude-sonnet-5",
    "copilot": "gpt-5.6-sol",
}


def get_selected_model() -> str:
    """Return the model currently selected in the sidebar for the active provider.

    Reads the provider-scoped model widget key and falls back to the
    provider's default if the value is missing or no longer valid.
    """
    provider = st.session_state.get("provider_select", DEFAULT_PROVIDER)
    provider = provider if provider in PROVIDERS else DEFAULT_PROVIDER
    model = st.session_state.get(f"model_select_{provider}")
    if model not in MODELS.get(provider, {}):
        model = DEFAULT_MODEL_BY_PROVIDER.get(provider, DEFAULT_MODEL)
    return model


# =============================================================================
# API KEY MANAGEMENT (session-only, never persisted)
# =============================================================================

def get_api_key(provider: str) -> str:
    """Return the API key for the given provider from session state.

    Keys are entered via the sidebar and live only in Streamlit session state.
    Raises ValueError if no key is found.
    """
    cfg = PROVIDERS.get(provider)
    if not cfg:
        raise ValueError(f"Unknown provider: {provider}")

    # Try the stored key (set by on_change callback)
    key = st.session_state.get(f"api_key_{provider}", "").strip()
    if key:
        return key

    # Fallback: read directly from the widget's session_state key
    key = st.session_state.get(f"api_key_w_{provider}", "").strip()
    if key:
        return key

    # Fallback: environment variable / .env file
    key = os.getenv(cfg["env_key"], "").strip()
    if key:
        return key

    raise ValueError(
        f"Please enter an API key for {cfg['name']} in the sidebar "
        f"or set {cfg['env_key']} in the .env file."
    )


# -----------------------------------------------------------------------------
# PROVIDER AUTO-DETECTION (from a pasted API key)
# -----------------------------------------------------------------------------

_KEY_PATTERNS = (
    ("gemini", ("AIza",)),
    ("anthropic", ("sk-ant-",)),
    ("openai", ("sk-proj-", "sk-svcacct-", "sk-admin-")),
    ("copilot", ("ghp_", "gho_", "ghu_", "ghs_", "ghr_", "github_pat_")),
)


def detect_provider_from_key(api_key: str) -> str | None:
    """Guess the provider from an API key prefix (or None if unknown).

    Prefix-matching is done longest-first; a bare ``sk-...`` key is either a
    legacy OpenAI key (embeds the ``T3BlbkFJ`` base64 marker) or an OpenCode
    Zen key.
    """
    key = (api_key or "").strip()
    if not key:
        return None
    for provider, prefixes in _KEY_PATTERNS:
        if key.startswith(prefixes):
            return provider
    if key.startswith("sk-"):
        if "T3BlbkFJ" in key:
            return "openai"
        return "opencode_zen"
    return None


# =============================================================================
# ANALYSIS ENGINE
# =============================================================================

def _parse_json_from_text(text: str) -> dict:
    """Extract a JSON object from text that may contain markdown or extra content."""
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group(0))
    raise json.JSONDecodeError("No JSON object found in the response.", text, 0)


# -----------------------------------------------------------------------------
# LANGUAGE GUARD (free models sometimes ignore the language instruction)
# -----------------------------------------------------------------------------

_PT_DIACRITICS = set("ãõçêâô")


def _detect_portuguese(text: str) -> bool:
    """Heuristic detection of Portuguese text (distinctive vs EN/ES)."""
    if not text:
        return False
    low = text.lower()
    diacritics = sum(1 for ch in low if ch in _PT_DIACRITICS)
    if diacritics >= 3:
        return True
    markers = ("não", "você", "uma ", "dos ", "das ", "são ")
    hits = sum(1 for m in markers if m in low)
    return hits >= 2 and diacritics >= 1


def _repair_content(provider, api_key, cfg, model, raw_json: dict, language: str) -> dict:
    """Ask the provider to rewrite the text values of raw_json in `language`."""
    log.info("Language repair triggered — model=%s target_lang=%s", model, language)
    repair_prompt = (
        "The text values in the JSON below are in the WRONG language.\n"
        f"Rewrite ONLY the text values (strings and string-array items) entirely in {language}.\n"
        "Keep the JSON keys and the structure EXACTLY as they are. Do not add, remove "
        "or reorder items. Do not invent content.\n"
        "Return ONLY the corrected JSON object, no markdown, no extra text.\n\n"
        f"JSON:\n{json.dumps(raw_json, ensure_ascii=False)}"
    )
    start = time.time()
    if provider == "anthropic":
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0.2,
            system="You always respond with valid JSON only.",
            messages=[{"role": "user", "content": repair_prompt}],
        )
        elapsed = time.time() - start
        log.info("Language repair done in %.1fs", elapsed)
        return _parse_json_from_text(resp.content[0].text)

    client = OpenAI(api_key=api_key, base_url=cfg["base_url"])
    resp = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": "You always respond with valid JSON only."},
            {"role": "user", "content": repair_prompt},
        ],
    )
    elapsed = time.time() - start
    log.info("Language repair done in %.1fs", elapsed)
    return _parse_json_from_text(resp.choices[0].message.content)


def _guard_language(result: dict, provider, api_key, cfg, model, language: str) -> dict:
    """Auto-fix the output language when the model ignores the instruction."""
    if language.lower() == "portuguese":
        return result
    joined = json.dumps(result, ensure_ascii=False)
    if not _detect_portuguese(joined):
        return result
    try:
        return _repair_content(provider, api_key, cfg, model, result, language)
    except Exception:
        return result


def analyze_profile(
    profile_text: str,
    job_description: str,
    provider: str,
    model: str,
    prompt: str,
    language: str = "English",
    api_key: str | None = None,
    **extra,
) -> dict:
    """Send profile + JD to the selected provider and return structured JSON."""
    cfg = PROVIDERS[provider]
    api_key = api_key if api_key else get_api_key(provider)

    fmt = dict(
        profile=profile_text,
        job_description=job_description,
        language=language,
    )
    fmt.update(extra)
    user_content = prompt.format(**fmt)

    log.info("API call → provider=%s model=%s prompt_len=%d", provider, model, len(user_content))
    start = time.time()

    # --- Anthropic (different API format) ---
    if provider == "anthropic":
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0.3,
            system=(
                "You always respond with valid JSON only. "
                f"Write all text content in {language}."
            ),
            messages=[{"role": "user", "content": user_content}],
        )
        elapsed = time.time() - start
        log.info("API response received in %.1fs (Anthropic)", elapsed)
        raw = response.content[0].text
        result = _parse_json_from_text(raw)
        return _guard_language(result, provider, api_key, cfg, model, language)

    # --- OpenAI-compatible providers (Zen, Gemini, OpenAI) ---
    client = OpenAI(api_key=api_key, base_url=cfg["base_url"])
    messages = [
        {
            "role": "system",
            "content": (
                "You always respond with valid JSON only. "
                f"Write all text content in {language}."
            ),
        },
        {"role": "user", "content": user_content},
    ]

    if cfg["json_mode"]:
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=messages,
        )
        elapsed = time.time() - start
        log.info("API response received in %.1fs (json_mode)", elapsed)
        raw = response.choices[0].message.content
        result = json.loads(raw)
        return _guard_language(result, provider, api_key, cfg, model, language)

    # Non-JSON-mode: try response_format, fall back to text parsing
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=messages,
        )
        elapsed = time.time() - start
        log.info("API response received in %.1fs (json_mode fallback)", elapsed)
        raw = response.choices[0].message.content
        result = json.loads(raw)
        return _guard_language(result, provider, api_key, cfg, model, language)
    except Exception as exc:
        log.warning("json_mode failed (%s), retrying without json_mode", exc)
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            messages=messages,
        )
        elapsed = time.time() - start
        log.info("API response received in %.1fs (text fallback)", elapsed)
        raw = response.choices[0].message.content
        result = _parse_json_from_text(raw)
        return _guard_language(result, provider, api_key, cfg, model, language)
