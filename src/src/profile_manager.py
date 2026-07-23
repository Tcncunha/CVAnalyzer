"""
Local JSON-based profile persistence.
"""

import json
import re
from pathlib import Path

from config import PROFILES_DIR


def list_saved_profiles() -> list[str]:
    """Return sorted list of saved profile identifiers (without extension)."""
    return sorted(p.stem for p in PROFILES_DIR.glob("*.json") if p.is_file())


def save_profile(identifier: str, data: dict) -> Path:
    """Persist a profile dictionary to a JSON file."""
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", identifier.strip())
    file_path = PROFILES_DIR / f"{safe_name}.json"
    file_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return file_path


def load_profile(identifier: str) -> dict | None:
    """Load a profile from disk. Returns None if not found."""
    file_path = PROFILES_DIR / f"{identifier}.json"
    if file_path.exists():
        return json.loads(file_path.read_text(encoding="utf-8"))
    return None
