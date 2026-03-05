"""Persist last-known campsite availability to disk."""

from __future__ import annotations

import json
from pathlib import Path

STATE_FILE = Path("state.json")


def load() -> dict[str, dict[str, dict[str, str]]]:
    """Load state from disk. Returns {} if file doesn't exist.

    Structure: {facility_id: {site_id: {date_str: status}}}
    """
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save(state: dict[str, dict[str, dict[str, str]]]) -> None:
    """Write state to disk atomically."""
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE_FILE)


def get_campground_state(
    state: dict[str, dict[str, dict[str, str]]],
    facility_id: str,
) -> dict[str, dict[str, str]]:
    """Return the stored availability for a facility. Returns {} if not yet seen."""
    return state.get(facility_id, {})


def update_campground_state(
    state: dict[str, dict[str, dict[str, str]]],
    facility_id: str,
    availability: dict[str, dict[str, str]],
) -> None:
    """Merge new availability data into state in-place."""
    if facility_id not in state:
        state[facility_id] = {}
    for site_id, dates in availability.items():
        state[facility_id][site_id] = dates
