"""
storage.py
----------
Handles all JSON data persistence.
Loads and saves the application data file safely.
Never crashes on missing, empty, or corrupted data.
"""

import json
import os
import logging
from typing import Any

from config import DATA_FILE

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default data structure used when no data file exists yet.
# ---------------------------------------------------------------------------
_DEFAULT_DATA: dict[str, Any] = {
    "exercises": [],
    "weekly_plan": {
        "Monday": [],
        "Tuesday": [],
        "Wednesday": [],
        "Thursday": [],
        "Friday": [],
        "Saturday": [],
        "Sunday": [],
    },
    "ai_plans": [],
    "settings": {
        "theme": "light",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """
    Recursively merge *override* into *base*.
    Keys present in *base* but missing from *override* are kept.
    This prevents losing default keys when loading an older data file.
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_data() -> dict[str, Any]:
    """
    Load and return the application data dictionary.

    Handles:
    - File not found  → returns default structure.
    - Empty file      → returns default structure.
    - Corrupted JSON  → returns default structure + logs warning.
    - Invalid top-level type → returns default structure.
    """
    if not os.path.exists(DATA_FILE):
        logger.info("data.json not found – using defaults.")
        return dict(_DEFAULT_DATA)

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as fh:
            raw = fh.read().strip()

        if not raw:
            logger.info("data.json is empty – using defaults.")
            return dict(_DEFAULT_DATA)

        loaded: Any = json.loads(raw)

        if not isinstance(loaded, dict):
            logger.warning("data.json root is not a dict – using defaults.")
            return dict(_DEFAULT_DATA)

        # Merge so that any new keys added in future versions are present.
        return _deep_merge(_DEFAULT_DATA, loaded)

    except json.JSONDecodeError as exc:
        logger.warning("data.json is corrupted (%s) – using defaults.", exc)
        return dict(_DEFAULT_DATA)
    except OSError as exc:
        logger.warning("Could not read data.json (%s) – using defaults.", exc)
        return dict(_DEFAULT_DATA)


def save_data(data: dict[str, Any]) -> bool:
    """
    Persist *data* to the JSON file.

    Returns True on success, False on failure.
    Uses an atomic write (temp file + rename) to avoid partial writes.
    """
    tmp_path = DATA_FILE + ".tmp"
    try:
        os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        # Atomic replace (works on POSIX; on Windows os.replace is used).
        os.replace(tmp_path, DATA_FILE)
        return True
    except OSError as exc:
        logger.error("Could not save data.json: %s", exc)
        # Clean up tmp file if it was created.
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return False


def ensure_data_file() -> None:
    """
    Create the data file with default content if it does not exist yet.
    Called once at application start.
    """
    if not os.path.exists(DATA_FILE):
        save_data(_DEFAULT_DATA)
        logger.info("Created new data.json at %s", DATA_FILE)
