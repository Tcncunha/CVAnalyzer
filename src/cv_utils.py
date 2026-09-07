"""Shared helpers for CV parsing/structuring used by cv_builder and cv_export."""

import json
import re

_CV_DEFAULTS = {
    "name": "",
    "title": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin": "",
    "summary": "",
    "skills": [],
    "experience": [],
    "education": [],
    "languages": [],
    "certifications": [],
}


def parse_json_from_text(text: str) -> dict:
    """Extract a JSON object from text that may contain markdown fences.

    Raises json.JSONDecodeError if no JSON object is found.
    """
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group(0))
    raise json.JSONDecodeError("No JSON object found.", text, 0)


def ensure_cv_structure(raw: dict) -> dict:
    """Guarantee every expected CV key exists with the right type."""
    result = {}
    for key, default in _CV_DEFAULTS.items():
        val = raw.get(key, default)
        if isinstance(default, list):
            if not isinstance(val, list):
                val = [str(val)] if val else []
        else:
            val = str(val) if val is not None else ""
        result[key] = val
    return result
