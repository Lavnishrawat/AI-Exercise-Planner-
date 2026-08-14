"""
progress.py
-----------
Progress calculation logic.
All functions operate on the in-memory data dictionary and return plain
Python values – no Tkinter or I/O here.
"""

import logging
from typing import Any

from config import DAYS_OF_WEEK
from planner import get_all_entries, get_day_entries

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Overall progress
# ---------------------------------------------------------------------------

def calculate_overall_progress(data: dict[str, Any]) -> dict[str, Any]:
    """
    Return a dict summarising the overall workout progress.

    Keys
    ----
    total       : int   – total plan entries across the week.
    completed   : int   – entries marked completed.
    remaining   : int   – entries not yet completed.
    percentage  : float – completion percentage (0.0 – 100.0).
    total_duration_min : int – sum of duration fields for all entries (minutes).
    completed_duration_min : int – sum of duration for completed entries.
    """
    entries = get_all_entries(data)
    total = len(entries)
    completed = sum(1 for e in entries if e.get("completed", False))
    remaining = total - completed
    percentage = (completed / total * 100.0) if total > 0 else 0.0

    total_dur = sum(int(e.get("duration", 0)) for e in entries)
    completed_dur = sum(
        int(e.get("duration", 0)) for e in entries if e.get("completed", False)
    )

    return {
        "total": total,
        "completed": completed,
        "remaining": remaining,
        "percentage": round(percentage, 1),
        "total_duration_min": total_dur,
        "completed_duration_min": completed_dur,
    }


# ---------------------------------------------------------------------------
# Per-day progress
# ---------------------------------------------------------------------------

def calculate_day_progress(data: dict[str, Any], day: str) -> dict[str, Any]:
    """
    Return a progress dict for a single *day*.

    Keys are the same as calculate_overall_progress plus:
    day : str – the day name.
    """
    entries = get_day_entries(data, day)
    total = len(entries)
    completed = sum(1 for e in entries if e.get("completed", False))
    remaining = total - completed
    percentage = (completed / total * 100.0) if total > 0 else 0.0
    total_dur = sum(int(e.get("duration", 0)) for e in entries)
    completed_dur = sum(
        int(e.get("duration", 0)) for e in entries if e.get("completed", False)
    )

    return {
        "day": day,
        "total": total,
        "completed": completed,
        "remaining": remaining,
        "percentage": round(percentage, 1),
        "total_duration_min": total_dur,
        "completed_duration_min": completed_dur,
    }


# ---------------------------------------------------------------------------
# Weekly breakdown
# ---------------------------------------------------------------------------

def calculate_weekly_breakdown(data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Return a list with one progress dict per day (Monday … Sunday).
    """
    return [calculate_day_progress(data, day) for day in DAYS_OF_WEEK]


# ---------------------------------------------------------------------------
# Summary text helpers (for display in the GUI)
# ---------------------------------------------------------------------------

def format_duration(minutes: int) -> str:
    """Convert integer minutes to a human-readable string."""
    if minutes <= 0:
        return "0 min"
    hours, mins = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h {mins}min" if mins else f"{hours}h"
    return f"{mins} min"


def progress_summary_text(data: dict[str, Any]) -> str:
    """Return a short multi-line summary suitable for a label widget."""
    p = calculate_overall_progress(data)
    lines = [
        f"Total exercises planned : {p['total']}",
        f"Completed               : {p['completed']}",
        f"Remaining               : {p['remaining']}",
        f"Completion              : {p['percentage']:.1f}%",
        f"Total planned duration  : {format_duration(p['total_duration_min'])}",
        f"Completed duration      : {format_duration(p['completed_duration_min'])}",
    ]
    return "\n".join(lines)
