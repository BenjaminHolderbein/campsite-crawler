"""Notification dispatch: ntfy.sh push and stdout."""

from __future__ import annotations

import os

import httpx

from .checker import AvailabilityEvent

NTFY_BASE = "https://ntfy.sh"


def _booking_url(event: AvailabilityEvent) -> str:
    if event.booking_url:
        return event.booking_url
    return f"https://www.recreation.gov/camping/campsites/{event.site_id}"


def _format_message(event: AvailabilityEvent) -> str:
    date_display = event.date_str[:10]
    return (
        f"[CAMPSITE ALERT] {event.campground_name}\n"
        f"Site {event.site_id} is now AVAILABLE on {date_display}\n"
        f"Book now: {_booking_url(event)}"
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
    booking = _booking_url(event)
    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(
                url,
                content=message.encode(),
                headers={
                    "Title": f"Campsite Available: {event.campground_name}",
                    "Priority": "high",
                    "Tags": "camping,tent",
                    "Click": booking,
                    "Actions": f"view, Book Now, {booking}",
                },
            )
    except httpx.RequestError as exc:
        print(f"[notifier] Warning: ntfy.sh push failed: {exc}")
