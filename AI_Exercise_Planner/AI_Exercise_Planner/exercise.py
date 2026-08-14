"""
exercise.py
-----------
Exercise data model and all exercise-management logic.
Operates on the in-memory data dictionary supplied by storage.py.
"""

import uuid
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exercise schema helpers
# ---------------------------------------------------------------------------

def make_exercise(
    name: str,
    category: str = "Other",
    sets: int = 3,
    reps: int = 10,
    duration: int = 0,
    difficulty: str = "Beginner",
    equipment: str = "No Equipment",
    notes: str = "",
) -> dict[str, Any]:
    """
    Return a new exercise dictionary with all required fields.

    Parameters
    ----------
    name        : Display name.
    category    : One of the EXERCISE_CATEGORIES constants.
    sets        : Number of sets (0 means not applicable).
    reps        : Reps per set (0 means not applicable).
    duration    : Duration in minutes (0 means use sets/reps instead).
    difficulty  : Beginner / Intermediate / Advanced.
    equipment   : Equipment required.
    notes       : Free-text notes.
    """
    return {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "category": category,
        "sets": max(0, int(sets)),
        "reps": max(0, int(reps)),
        "duration": max(0, int(duration)),
        "difficulty": difficulty,
        "equipment": equipment,
        "notes": notes.strip(),
    }


def validate_exercise(data: dict[str, Any]) -> tuple[bool, str]:
    """
    Validate a raw exercise dict coming from user input.

    Returns (True, "") on success or (False, error_message) on failure.
    """
    name = str(data.get("name", "")).strip()
    if not name:
        return False, "Exercise name cannot be empty."
    if len(name) > 100:
        return False, "Exercise name is too long (max 100 characters)."

    try:
        sets = int(data.get("sets", 0))
        reps = int(data.get("reps", 0))
        duration = int(data.get("duration", 0))
    except (ValueError, TypeError):
        return False, "Sets, reps, and duration must be whole numbers."

    if sets < 0 or reps < 0 or duration < 0:
        return False, "Sets, reps, and duration cannot be negative."

    return True, ""


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

def get_all_exercises(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the full exercise list from the data store."""
    return data.get("exercises", [])


def get_exercise_by_id(
    data: dict[str, Any], exercise_id: str
) -> Optional[dict[str, Any]]:
    """Return the exercise with the given ID, or None if not found."""
    for ex in data.get("exercises", []):
        if ex.get("id") == exercise_id:
            return ex
    return None


def add_exercise(data: dict[str, Any], exercise: dict[str, Any]) -> None:
    """Add a new exercise to the data store."""
    if "exercises" not in data or not isinstance(data["exercises"], list):
        data["exercises"] = []
    data["exercises"].append(exercise)
    logger.debug("Added exercise: %s", exercise.get("name"))


def update_exercise(
    data: dict[str, Any], exercise_id: str, updated: dict[str, Any]
) -> bool:
    """
    Replace the exercise matching *exercise_id* with *updated*.
    Returns True if found and updated, False otherwise.
    """
    for i, ex in enumerate(data.get("exercises", [])):
        if ex.get("id") == exercise_id:
            updated["id"] = exercise_id  # preserve the original ID
            data["exercises"][i] = updated
            logger.debug("Updated exercise id=%s", exercise_id)
            return True
    logger.warning("update_exercise: id=%s not found.", exercise_id)
    return False


def delete_exercise(data: dict[str, Any], exercise_id: str) -> bool:
    """
    Remove the exercise with *exercise_id* from the exercise list AND
    from any day in the weekly plan that references it.

    Returns True if the exercise was found and deleted.
    """
    exercises = data.get("exercises", [])
    original_length = len(exercises)
    data["exercises"] = [ex for ex in exercises if ex.get("id") != exercise_id]

    if len(data["exercises"]) == original_length:
        logger.warning("delete_exercise: id=%s not found.", exercise_id)
        return False

    # Also remove from weekly plan.
    weekly = data.get("weekly_plan", {})
    for day, entries in weekly.items():
        weekly[day] = [e for e in entries if e.get("exercise_id") != exercise_id]

    logger.debug("Deleted exercise id=%s", exercise_id)
    return True


def search_exercises(
    data: dict[str, Any],
    query: str = "",
    category: str = "",
    difficulty: str = "",
) -> list[dict[str, Any]]:
    """
    Return exercises matching all supplied filters.
    All comparisons are case-insensitive.
    Empty string means "no filter".
    """
    results = data.get("exercises", [])
    q = query.strip().lower()
    cat = category.strip().lower()
    diff = difficulty.strip().lower()

    if q:
        results = [
            ex for ex in results
            if q in ex.get("name", "").lower()
            or q in ex.get("notes", "").lower()
            or q in ex.get("category", "").lower()
        ]
    if cat:
        results = [ex for ex in results if ex.get("category", "").lower() == cat]
    if diff:
        results = [ex for ex in results if ex.get("difficulty", "").lower() == diff]

    return results
