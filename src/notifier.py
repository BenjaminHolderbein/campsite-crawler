"""Notification dispatch: ntfy.sh push and stdout."""

from __future__ import annotations

import os

import httpx

from .checker import AvailabilityEvent

NTFY_BASE = "https://ntfy.sh"


def _format_message(event: AvailabilityEvent) -> str:
    date_display = event.date_str[:10]
    return (
        f"[CAMPSITE ALERT] {event.campground_name}\n"
        f"Site {event.site_id} is now AVAILABLE on {date_display}\n"
        f"Book now: https://www.recreation.gov/camping/campsites/{event.site_id}"
    )


def notify(events: list[AvailabilityEvent], topic: str | None = None) -> None:
    """Print events to stdout and optionally push to ntfy.sh."""
    resolved_topic = topic or os.getenv("NTFY_TOPIC")
    for event in events:
        message = _format_message(event)
        print(message)
        print()
        if resolved_topic:
            _push_ntfy(resolved_topic, event, message)


def _push_ntfy(topic: str, event: AvailabilityEvent, message: str) -> None:
    url = f"{NTFY_BASE}/{topic}"
    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(
                url,
                content=message.encode(),
                headers={
                    "Title": f"Campsite Available: {event.campground_name}",
                    "Priority": "high",
                    "Tags": "camping,tent",
                    "Click": f"https://www.recreation.gov/camping/campsites/{event.site_id}",
                    "Actions": f"view, Book Now, https://www.recreation.gov/camping/campsites/{event.site_id}",
                },
            )
    except httpx.RequestError as exc:
        print(f"[notifier] Warning: ntfy.sh push failed: {exc}")
