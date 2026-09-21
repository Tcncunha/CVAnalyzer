"""
AI provider definitions, model registry, API key management, and analysis engine.

Routing: Cerebras -> OpenCode Zen (if enabled) -> Gemini -> Groq free.
Callers just use analyze_profile() as before.

Supported providers:
  - Job Ascend Free (shared Groq key, no user key needed)
  - OpenCode Zen (free models)
  - Google Gemini
  - OpenAI
  - Anthropic (Claude)
  - GitHub Copilot
"""

import json
import logging
import os
import threading
import time
import uuid

import anthropic
import streamlit as st
from cv_utils import parse_json_from_text as _parse_json_from_text
from openai import OpenAI

log = logging.getLogger("cv-analyzer.providers")

# OpenCode requires external clients to identify themselves with a stable
# session ID per conversation (x-opencode-session) and a custom User-Agent.
# Since calls run in worker threads (no session_state access), use a single
# stable ID per process — good enough for routing/prompt-cache purposes.
_OPENCODE_SESSION_ID = f"cv-analyzer-{uuid.uuid4().hex[:16]}"


def _opencode_headers(provider: str) -> dict[str, str] | None:
    if provider != "opencode_zen":
        return None
    return {
        "x-opencode-session": _OPENCODE_SESSION_ID,
        "User-Agent": "CV-Analyzer/1.0 (streamlit job matching app)",
    }


def is_free_zen_model(model: str) -> bool:
    """True when the model is one of OpenCode Zen's free-tier models.

    As of 2026-09, OpenCode restricts free-tier models to requests made from
    inside OpenCode itself; external clients get a MissingSessionID error.
    """
    return bool(model) and (model.endswith("-free") or model == "big-pickle")


# =============================================================================
# PROVIDER & MODEL REGISTRY
# =============================================================================

PROVIDERS = {
    "groq_free": {
        "name": "Job Ascend Free (Groq, no key needed)",
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "SHARED_GROQ_KEY",
        "json_mode": False,
        # gpt-oss on Groq rejects response_format=json_object (400
        # json_validate_failed), so skip that attempt entirely and go
        # straight to text parsing — each failed attempt burns TPM quota.
        "skip_json_attempt": True,
        "needs_key": False,
    },
    "cerebras": {
        "name": "Cerebras (owner key)",
        "base_url": "https://api.cerebras.ai/v1",
        "env_key": "CEREBRAS_API_KEY",
        "json_mode": False,
        # Same rationale as Groq: straight to text parsing.
        "skip_json_attempt": True,
        "needs_key": True,
    },
    "opencode_zen": {
        "name": "OpenCode Zen (Free Models)",
        "base_url": "https://opencode.ai/zen/v1",
        "env_key": "OPENCODE_ZEN_API_KEY",
        "json_mode": False,
        # Skip the response_format probe: blocked free tier answers 403
        # either way, so go straight to text and save a wasted call.
        "skip_json_attempt": True,
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
    "groq_free": {
        "openai/gpt-oss-120b": "GPT-OSS 120B (best quality)",
        "openai/gpt-oss-20b": "GPT-OSS 20B (fast, for Auto Match)",
        "allam-2-7b": "Allam 2 7B (fallback, highest quota)",
    },
    "cerebras": {
        "gpt-oss-120b": "GPT-OSS 120B (best quality)",
        "qwen-3.8-27b": "Qwen 3.8 27B (fast)",
    },
    "opencode_zen": {
        "big-pickle": "Big Pickle (Free)",
        "nemotron-3.5-lightning-free": "Nemotron 3.5 Lightning (Free)",
        "nemotron-3-ultra-free": "Nemotron 3 Ultra (Free)",
        "deepseek-v4-flash-free": "DeepSeek V4 Flash (Free)",
        "mimo-v2.5-free": "MiMo V2.5 (Free)",
        "ling-3.0-flash-fin-free": "Ling 3.0 Flash Fin (Free)",
        "muse-spark-1.3-contributor-free": "Muse Spark 1.3 (Free)",
        "muse-spark-1.2-contributor-free": "Muse Spark 1.2 (Free)",
        "deepseek-v4-flash": "DeepSeek V4 Flash",
        "deepseek-v4-pro": "DeepSeek V4 Pro",
        "glm-5.3-flash": "GLM 5.3 Flash",
        "glm-5.2": "GLM 5.2",
        "minimax-m3": "MiniMax M3",
        "minimax-m2.7": "MiniMax M2.7",
        "kimi-k2.7-code": "Kimi K2.7 Code",
        "kimi-k3": "Kimi K3",
        "hy3": "Hy3",
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

DEFAULT_PROVIDER = "groq_free"
DEFAULT_MODEL = "big-pickle"

# ---------------------------------------------------------------------------
# Free shared-key routing (Groq). No user key needed: the owner sets
# SHARED_GROQ_KEY in .env (local) or Streamlit Secrets (cloud).
#   - Analysis-quality flows (Analyzer, CV Builder, STAR) -> 120b
#   - High-volume flows (Auto Match, 1 call per vacancy) -> 20b
#   - Quota fallback if 20b is exhausted -> allam-2-7b (7K req/day)
# ---------------------------------------------------------------------------
FREE_PROVIDER = "groq_free"
FREE_ANALYSIS_MODEL = "openai/gpt-oss-120b"
FREE_VOLUME_MODEL = "openai/gpt-oss-20b"
FREE_FALLBACK_MODEL = "allam-2-7b"

# Best default model per provider, used when a provider is selected (or
# auto-detected from the API key).
DEFAULT_MODEL_BY_PROVIDER = {
    "groq_free": "openai/gpt-oss-120b",
    "opencode_zen": "big-pickle",
    "gemini": "gemini-2.5-flash",
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

def _read_key(provider: str) -> str:
    """Return the stored key for a provider, or "" if none is configured.

    Never raises. Lookup order: session state -> .env -> Streamlit Secrets.
    """
    cfg = PROVIDERS.get(provider)
    if not cfg:
        return ""
    for candidate in (
        st.session_state.get(f"api_key_{provider}", ""),
        st.session_state.get(f"api_key_w_{provider}", ""),
        os.getenv(cfg["env_key"], ""),
    ):
        if (candidate or "").strip():
            return candidate.strip()
    try:
        candidate = st.secrets.get(cfg["env_key"], "")
    except Exception:
        candidate = ""
    return (candidate or "").strip()


def get_api_key(provider: str) -> str:
    """Return the API key for the given provider from session state.

    Keys are entered via the sidebar and live only in Streamlit session state.
    Raises ValueError if no key is found.
    """
    cfg = PROVIDERS.get(provider)
    if not cfg:
        raise ValueError(f"Unknown provider: {provider}")

    key = _read_key(provider)
    if key:
        return key

    raise ValueError(
        f"Please enter an API key for {cfg['name']} in the sidebar "
        f"or set {cfg['env_key']} in the .env file."
    )


def test_api_key(provider: str, api_key: str, model: str) -> tuple[bool, str]:
    """Test if the API key works by sending a minimal request.

    Returns (success: bool, message: str).
    """
    cfg = PROVIDERS.get(provider)
    if not cfg:
        return False, f"Unknown provider: {provider}"

    try:
        client = OpenAI(api_key=api_key, base_url=cfg["base_url"])
        tb_kwargs: dict = {}
        if provider == FREE_PROVIDER:
            # gpt-oss reasoning would eat the tiny test budget otherwise.
            tb_kwargs = {"max_tokens": 50, "extra_body": {"reasoning_effort": "low"}}
        else:
            tb_kwargs = {"max_tokens": 5}
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            **tb_kwargs,
        )
        if response.choices:
            return True, f"Key OK — {cfg['name']} / {model}"
        return False, "Empty response from API"
    except openai.AuthenticationError:
        return False, "Invalid API key"
    except openai.RateLimitError:
        return True, "Key OK (rate limited, but auth passed)"
    except openai.APIConnectionError:
        return False, "Cannot connect to API server"
    except openai.BadRequestError as e:
        # Model might not exist or other API error
        return False, f"API error: {str(e)[:100]}"
    except Exception as e:
        return False, f"Error: {str(e)[:100]}"


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

    client = OpenAI(
        api_key=api_key,
        base_url=cfg["base_url"],
        default_headers=_opencode_headers(provider),
    )
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


def _analyze_profile_inner(
    profile_text: str,
    job_description: str,
    provider: str,
    model: str,
    prompt: str,
    language: str = "English",
    api_key: str | None = None,
    **extra,
) -> dict:
    """Single-provider attempt. Use analyze_profile() (with fallback) instead."""
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
    client = OpenAI(
        api_key=api_key,
        base_url=cfg["base_url"],
        default_headers=_opencode_headers(provider),
    )
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

    # Non-JSON-mode: try response_format, fall back to text parsing.
    # Providers flagged with skip_json_attempt (their models reject
    # response_format with 400) go straight to the text call.
    if not cfg.get("skip_json_attempt"):
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
    # Text-only path: cap output tokens to protect free-tier TPM budgets.
    text_kwargs: dict = {"max_tokens": 1500} if cfg.get("skip_json_attempt") else {}
    if provider == FREE_PROVIDER:
        # gpt-oss models "think" before answering; without this the
        # reasoning eats the token budget and content comes back empty.
        text_kwargs["extra_body"] = {"reasoning_effort": "low"}
    response = client.chat.completions.create(
        model=model,
        temperature=0.3,
        messages=messages,
        **text_kwargs,
    )
    elapsed = time.time() - start
    log.info("API response received in %.1fs (text fallback)", elapsed)
    raw = response.choices[0].message.content
    result = _parse_json_from_text(raw)
    return _guard_language(result, provider, api_key, cfg, model, language)


# ---------------------------------------------------------------------------
# Primary -> fallback routing: Gemini first (owner key), Groq free on ANY
# Gemini failure (missing key, 429, 400, ...). Callers keep passing
# provider="groq_free" — routing is transparent to every flow
# (Analyzer, CV Builder, STAR, Auto Match).
# ---------------------------------------------------------------------------
PRIMARY_PROVIDER = "gemini"

# OpenCode Zen free tier is blocked for external clients (FreeTierError),
# so it stays OUT of the chain unless explicitly enabled (paid key).
# Set ENABLE_OPENCODE=1 in .env/Secrets to re-enable it.
_ZEN_ENABLED = os.getenv("ENABLE_OPENCODE", "").strip().lower() in (
    "1",
    "true",
    "yes",
)

# ---------------------------------------------------------------------------
# User-facing notices: worker threads can't touch Streamlit UI, so fallback
# events are queued here and rendered later by render_provider_notices().
# ---------------------------------------------------------------------------
_NOTICES: list[str] = []
_NOTICES_LOCK = threading.Lock()


def notify_user(code: str) -> None:
    """Queue a user-facing notice code (translated at render time)."""
    with _NOTICES_LOCK:
        _NOTICES.append(code)


def consume_notices() -> list[str]:
    """Return and clear all queued notice codes (UI thread only)."""
    with _NOTICES_LOCK:
        items = list(_NOTICES)
        _NOTICES.clear()
        return items


def _configured_model(env_name: str, default: str) -> str:
    """Model override via env var or Streamlit Secret, else default."""
    override = (os.getenv(env_name, "") or "").strip()
    if override:
        return override
    try:
        override = (st.secrets.get(env_name, "") or "").strip()
    except Exception:
        override = ""
    return override or default


def configured_gemini_model() -> str:
    """Gemini model for the primary slot: GEMINI_MODEL env/secret, else default.

    gemini-2.5-flash has a far bigger free quota than the 3.8-flash
    (20 req/day), so it is the default primary.
    """
    return _configured_model("GEMINI_MODEL", "gemini-2.5-flash")


def configured_cerebras_model() -> str:
    """Cerebras model for the fallback slot: CEREBRAS_MODEL env/secret."""
    return _configured_model("CEREBRAS_MODEL", "gpt-oss-120b")


# ---------------------------------------------------------------------------
# Provider cooldowns: free tiers are tiny and Zen free models may be blocked
# for external clients (MissingSessionID), so once a provider reports a
# hard failure there is no point retrying it on every vacancy.
# Process-wide timestamps (monotonic clock); worker threads share them safely.
# ---------------------------------------------------------------------------
_COOLDOWNS: dict[str, float] = {}


def _cooldown_active(name: str) -> bool:
    return time.monotonic() < _COOLDOWNS.get(name, 0.0)


def _register_failure(name: str, exc: Exception) -> None:
    """Set a cooldown after a provider failure, sized by failure type."""
    text = str(exc).lower()
    status = getattr(exc, "status_code", None)
    if (
        status in (401, 403, 404)
        or "invalid api key" in text
        or "missingsessionid" in text
        or "missing session" in text
        or "freetiererror" in text
        or "can only be used from within" in text
        or "not found" in text
    ):
        # Permanent (bad key / blocked external use / bad model).
        reason, delay = "auth/model error", 86400.0
    elif (
        "perday" in text
        or "per_day" in text
        or "freetier" in text
        or "free_tier" in text
        or "requests per day" in text
        or "daily limit" in text
    ):
        # Daily free-tier quota: refills at UTC midnight.
        now = time.gmtime()
        secs_left = 86400 - (now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec) + 60
        reason, delay = "daily quota exhausted", max(secs_left, 60.0)
    else:
        # Transient (per-minute 429, 5xx, timeouts): short breather.
        reason, delay = "transient error", 90.0
    _COOLDOWNS[name] = time.monotonic() + delay
    log.info("%s cooldown %.0fs (%s)", name, delay, reason)


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
    """Send profile + JD to AI and return structured JSON.

    Chain: Cerebras (owner key) -> OpenCode Zen (if enabled) -> owner
    Gemini key -> free shared Groq key. Raises only if ALL fail.
    """
    if provider == FREE_PROVIDER:
        # 1. Cerebras (owner key) — first by request.
        cer_key = _read_key("cerebras")
        if cer_key and not _cooldown_active("cerebras"):
            try:
                return _analyze_profile_inner(
                    profile_text,
                    job_description,
                    "cerebras",
                    configured_cerebras_model(),
                    prompt,
                    language,
                    api_key=cer_key,
                    **extra,
                )
            except Exception as exc:
                _register_failure("cerebras", exc)
                notify_user("notice_cerebras_fallback")
                log.warning("Cerebras failed (%s), trying OpenCode", exc)
        elif cer_key:
            log.info("Cerebras on cooldown, trying OpenCode")
        # 2. OpenCode Zen (owner key) — only when explicitly enabled,
        # since the free tier is blocked outside OpenCode.
        zen_key = _read_key("opencode_zen")
        if zen_key and _ZEN_ENABLED and not _cooldown_active("opencode_zen"):
            zen_model = DEFAULT_MODEL_BY_PROVIDER.get("opencode_zen", "big-pickle")
            try:
                return _analyze_profile_inner(
                    profile_text,
                    job_description,
                    "opencode_zen",
                    zen_model,
                    prompt,
                    language,
                    api_key=zen_key,
                    **extra,
                )
            except Exception as exc:
                _register_failure("opencode_zen", exc)
                notify_user("notice_zen_fallback")
                log.warning("OpenCode primary failed (%s), trying Gemini", exc)
        elif zen_key and _ZEN_ENABLED:
            log.info("OpenCode on cooldown, trying Gemini")
        # 2. Owner Gemini key.
        gem_key = _read_key(PRIMARY_PROVIDER)
        if gem_key and not _cooldown_active("gemini"):
            gem_model = configured_gemini_model()
            try:
                return _analyze_profile_inner(
                    profile_text,
                    job_description,
                    PRIMARY_PROVIDER,
                    gem_model,
                    prompt,
                    language,
                    api_key=gem_key,
                    **extra,
                )
            except Exception as exc:
                _register_failure("gemini", exc)
                notify_user("notice_gemini_fallback")
                log.warning(
                    "Gemini primary failed (%s), falling back to Groq free", exc
                )
        elif gem_key:
            log.info("Gemini on cooldown, using Groq free directly")
        # 4. Free shared Groq key — last resort, raises on failure.
        return _analyze_profile_inner(
            profile_text,
            job_description,
            provider,
            model,
            prompt,
            language,
            api_key=api_key,
            **extra,
        )
    return _analyze_profile_inner(
        profile_text,
        job_description,
        provider,
        model,
        prompt,
        language,
        api_key=api_key,
        **extra,
    )
