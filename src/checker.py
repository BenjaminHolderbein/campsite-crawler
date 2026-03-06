"""Availability change detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass
class AvailabilityEvent:
    campground_name: str
    facility_id: str
    site_id: str
    date_str: str
    previous_status: str | None
    current_status: str
    booking_url: str = field(default="")


def _parse_date(date_str: str) -> date:
    """Parse a date string like '2026-03-14T00:00:00Z' into a date."""
    return date.fromisoformat(date_str[:10])


def _has_consecutive_nights(dates: dict[str, str], start_date_str: str, nights: int) -> bool:
    """Return True if the site is available for `nights` consecutive nights starting at start_date_str."""
    d = _parse_date(start_date_str)
    for _ in range(nights):
        key = d.strftime("%Y-%m-%dT00:00:00Z")
        if dates.get(key) != "A":
            return False
        d += timedelta(days=1)
    return True


def find_new_openings(
    campground_name: str,
    facility_id: str,
    fresh: dict[str, dict[str, str]],
    stored: dict[str, dict[str, str]],
    booking_url: str = "",
    min_nights: int = 1,
) -> list[AvailabilityEvent]:
    """Return events where a site transitioned to Available ("A").

    Only notifies on * -> "A" transitions to avoid duplicate alerts.
    When min_nights > 1, only emits an event for the check-in date when
    min_nights consecutive nights are available starting from that date.
    """
    events: list[AvailabilityEvent] = []
    for site_id, dates in fresh.items():
        stored_dates = stored.get(site_id, {})
        # Sort dates so we process check-in candidates in chronological order
        # and can skip nights that are part of an already-emitted stay.
        emitted_until: date | None = None
        for date_str in sorted(dates):
            current_status = dates[date_str]
            if current_status != "A":
                continue

            # Skip dates that are interior nights of a stay we already emitted.
            if emitted_until is not None and _parse_date(date_str) < emitted_until:
                continue

            previous_status = stored_dates.get(date_str)
            if previous_status == "A":
                continue

            # For min_nights > 1 verify the full run is available.
            if min_nights > 1 and not _has_consecutive_nights(dates, date_str, min_nights):
                continue

            events.append(
                AvailabilityEvent(
                    campground_name=campground_name,
                    facility_id=facility_id,
                    site_id=site_id,
                    date_str=date_str,
                    previous_status=previous_status,
                    current_status=current_status,
                    booking_url=booking_url,
                )
            )
            emitted_until = _parse_date(date_str) + timedelta(days=min_nights)
    return events
