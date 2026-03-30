"""
Verified Events Loader — Loads journalist-verified event timeline
from config/verified_events.yaml for use in visualizations and reports.
"""

from typing import Optional

import yaml

from src.utils.constants import CONFIG_DIR
from src.utils.logger import log

_CACHE: Optional[dict] = None


def load_verified_events() -> dict:
    """Load verified events from YAML config.

    Returns dict with keys: 'events', 'entities'
    """
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    events_path = CONFIG_DIR / "verified_events.yaml"
    if not events_path.exists():
        log.warning(f"Verified events file not found: {events_path}")
        return {"events": [], "entities": {}}

    with open(events_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    _CACHE = data
    log.info(f"Loaded {len(data.get('events', []))} verified events")
    return data


def get_timeline_events() -> list[dict]:
    """Get just the events list, sorted by date."""
    data = load_verified_events()
    events = data.get("events", [])
    return sorted(events, key=lambda e: e.get("date", ""))


def get_event_by_date(date_str: str) -> Optional[dict]:
    """Find a specific event by date string (YYYY-MM-DD)."""
    for event in get_timeline_events():
        if event.get("date") == date_str:
            return event
    return None


def get_key_entities() -> dict:
    """Get the key entities (building, operation, orgs, journalism)."""
    data = load_verified_events()
    return data.get("entities", {})


def get_events_for_phase(phase_name: str) -> list[dict]:
    """Get verified events that impacted a specific phase."""
    return [e for e in get_timeline_events() if e.get("phase_impact") == phase_name]


if __name__ == "__main__":
    events = get_timeline_events()
    for e in events:
        print(f"  [{e['verification']}] {e['date']}: {e['event']}")

    entities = get_key_entities()
    if entities:
        print(f"\nKey entities: {list(entities.keys())}")
