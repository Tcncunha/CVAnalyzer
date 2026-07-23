"""
Configuration — paths, constants, providers, and environment setup.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

import i18n

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ---------------------------------------------------------------------------
# Provider Definitions
# ---------------------------------------------------------------------------
PROVIDERS = {
    "opencode_zen": {
        "name": "OpenCode Zen (Free Models)",
        "base_url": "https://opencode.ai/zen/v1",
        "env_key": "OPENCODE_ZEN_API_KEY",
        "json_mode": False,
    },
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "env_key": "GEMINI_API_KEY",
        "json_mode": True,
    },
}

# ---------------------------------------------------------------------------
# Model Definitions (grouped by provider)
# ---------------------------------------------------------------------------
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
}

DEFAULT_PROVIDER = "opencode_zen"
DEFAULT_MODEL = "big-pickle"


# ---------------------------------------------------------------------------
# API Key Retrieval
# ---------------------------------------------------------------------------
def get_api_key(provider: str) -> str:
    """Return the API key for the given provider or raise."""
    cfg = PROVIDERS.get(provider)
    if not cfg:
        raise EnvironmentError(i18n.t("unknown_provider_error", provider=provider))

    key = os.getenv(cfg["env_key"], "").strip()
    if not key:
        env_var = cfg["env_key"]
        raise EnvironmentError(i18n.t("missing_api_key_error", env_var=env_var))
    return key


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROFILES_DIR = PROJECT_ROOT / "src" / "profiles_json"
PROFILES_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# UI Constants
# ---------------------------------------------------------------------------
# Text constants live in i18n.py (translated). Only language-agnostic
# constants stay here.
APP_ICON = "🎯"

# ---------------------------------------------------------------------------
# AI Prompt
# ---------------------------------------------------------------------------
ANALYSIS_PROMPT = """\
You are a senior technical recruiter and career coach with 15+ years of
experience in talent acquisition for top-tier tech companies.

Analyze the following candidate profile against the provided job description.
Provide a thorough, honest, and actionable assessment.

CANDIDATE PROFILE:
\"\"\"
{profile}
\"\"\"

JOB DESCRIPTION:
\"\"\"
{job_description}
\"\"\"

Respond ONLY with a valid JSON object (no markdown, no extra text) using
exactly this schema:
{{
  "overall_score": <integer 0-100>,
  "pontos_fortes": [<string>, ...],
  "lacunas": [<string>, ...],
  "sugestoes_melhoria": [<string>, ...]
}}

Guidelines:
- "overall_score" represents how well the candidate fits the role (0-100).
- "pontos_fortes" lists the candidate's strongest alignment points (3-7 items).
- "lacunas" lists missing skills, experiences, or gaps (2-6 items).
- "sugestoes_melhoria" lists specific, actionable tips to improve the resume \
  for this role (3-6 items).
- Be specific, reference actual content from the profile and job description.
- Write all fields in {language}. Keep the JSON keys exactly as given above \
  (do not translate the keys, only the text values).
"""
