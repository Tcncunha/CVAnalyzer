"""
Configuration -- paths, constants, and the AI analysis prompt.
"""

from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths & environment
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load optional default API keys from .env (sidebar keys take priority).
load_dotenv(PROJECT_ROOT / ".env")

PROFILES_DIR = PROJECT_ROOT / "src" / "profiles_json"
PROFILES_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# UI constants
# ---------------------------------------------------------------------------
APP_ICON = "🎯"
APP_VERSION = "Beta 0.0.3"

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
  "pontos_fortes": [<string in {language}>, ...],
  "lacunas": [<string in {language}>, ...],
  "sugestoes_melhoria": [<string in {language}>, ...]
}}

Guidelines:
- "overall_score" represents how well the candidate fits the role (0-100).
- "pontos_fortes" lists the candidate's strongest alignment points (3-7 items).
- "lacunas" lists missing skills, experiences, or gaps (2-6 items).
- "sugestoes_melhoria" lists specific, actionable tips to improve the resume \
  for this role (3-6 items).
- Be specific, reference actual content from the profile and job description.
- LANGUAGE (HARD REQUIREMENT): every text value must be written entirely in \
  {language}. If the source documents are in another language, translate. Do \
  not answer in any other language. Keep the JSON keys exactly as given above \
  (do not translate the keys, only the text values).
"""
