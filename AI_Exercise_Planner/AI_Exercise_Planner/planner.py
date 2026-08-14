"""
planner.py
----------
Weekly workout planning logic.
Each day holds a list of "plan entries" – lightweight dicts that reference
an exercise by ID and carry their own completion status.
"""

import uuid
import logging
from typing import Any, Optional

from config import DAYS_OF_WEEK

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Plan-entry helpers
# ---------------------------------------------------------------------------

def make_plan_entry(
    exercise_id: str,
    exercise_name: str,
    sets: int = 0,
    reps: int = 0,
    duration: int = 0,
    notes: str = "",
) -> dict[str, Any]:
    """
    Return a new plan-entry dict.

    A plan entry is a lightweight reference to an exercise inside the
    weekly plan.  It stores a snapshot of the key fields so the plan
    still shows meaningful data even if the source exercise is later
    edited or deleted.
    """
    return {
        "entry_id": str(uuid.uuid4()),
        "exercise_id": exercise_id,
        "exercise_name": exercise_name,
        "sets": max(0, int(sets)),
        "reps": max(0, int(reps)),
        "duration": max(0, int(duration)),
        "notes": notes.strip(),
        "completed": False,
    }


# ---------------------------------------------------------------------------
# Weekly plan CRUD
# ---------------------------------------------------------------------------

def _get_day(data: dict[str, Any], day: str) -> list[dict[str, Any]]:
    """Return the entry list for *day*, creating it if absent."""
    plan = data.setdefault("weekly_plan", {})
    if day not in plan or not isinstance(plan[day], list):
        plan[day] = []
    return plan[day]


def get_day_entries(
    data: dict[str, Any], day: str
) -> list[dict[str, Any]]:
    """Return all plan entries for the given day."""
    if day not in DAYS_OF_WEEK:
        logger.warning("get_day_entries: unknown day '%s'", day)
        return []
    return list(_get_day(data, day))


def get_all_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return all plan entries across every day."""
    entries: list[dict[str, Any]] = []
    for day in DAYS_OF_WEEK:
        entries.extend(_get_day(data, day))
    return entries


def add_entry_to_day(
    data: dict[str, Any], day: str, entry: dict[str, Any]
) -> bool:
    """
    Add *entry* to *day*.  Returns True on success, False if day is invalid.
    """
    if day not in DAYS_OF_WEEK:
        logger.warning("add_entry_to_day: unknown day '%s'", day)
        return False
    _get_day(data, day).append(entry)
    logger.debug("Added entry '%s' to %s", entry.get("exercise_name"), day)
    return True


def remove_entry_from_day(
    data: dict[str, Any], day: str, entry_id: str
) -> bool:
    """
    Remove the entry with *entry_id* from *day*.
    Returns True if found and removed.
    """
    if day not in DAYS_OF_WEEK:
        return False
    day_entries = _get_day(data, day)
    original = len(day_entries)
    data["weekly_plan"][day] = [e for e in day_entries if e.get("entry_id") != entry_id]
    removed = len(data["weekly_plan"][day]) < original
    if removed:
        logger.debug("Removed entry_id=%s from %s", entry_id, day)
    return removed


def update_entry_in_day(
    data: dict[str, Any], day: str, entry_id: str, updated: dict[str, Any]
) -> bool:
    """
    Replace the entry matching *entry_id* in *day* with *updated*.
    Preserves entry_id and exercise_id.
    Returns True if found and updated.
    """
    if day not in DAYS_OF_WEEK:
        return False
    day_entries = _get_day(data, day)
    for i, e in enumerate(day_entries):
        if e.get("entry_id") == entry_id:
            updated["entry_id"] = entry_id
            updated["exercise_id"] = e.get("exercise_id", updated.get("exercise_id", ""))
            data["weekly_plan"][day][i] = updated
            return True
    return False


def toggle_entry_completed(
    data: dict[str, Any], day: str, entry_id: str
) -> Optional[bool]:
    """
    Toggle the completed flag of *entry_id* in *day*.
    Returns the new boolean state, or None if the entry was not found.
    """
    if day not in DAYS_OF_WEEK:
        return None
    for entry in _get_day(data, day):
        if entry.get("entry_id") == entry_id:
            entry["completed"] = not entry.get("completed", False)
            return entry["completed"]
    return None


def clear_day(data: dict[str, Any], day: str) -> None:
    """Remove all entries from *day*."""
    if day in DAYS_OF_WEEK:
        data.setdefault("weekly_plan", {})[day] = []


def reset_all_completions(data: dict[str, Any]) -> None:
    """Mark all plan entries across every day as not completed."""
    for day in DAYS_OF_WEEK:
        for entry in _get_day(data, day):
            entry["completed"] = False
