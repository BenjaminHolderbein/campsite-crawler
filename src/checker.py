"""Availability change detection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AvailabilityEvent:
    campground_name: str
    facility_id: str
    site_id: str
    date_str: str
    previous_status: str | None
    current_status: str


def find_new_openings(
    campground_name: str,
    facility_id: str,
    fresh: dict[str, dict[str, str]],
    stored: dict[str, dict[str, str]],
) -> list[AvailabilityEvent]:
    """Return events where a site transitioned to Available ("A").

    Only notifies on * -> "A" transitions to avoid duplicate alerts.
    """
    events: list[AvailabilityEvent] = []
    for site_id, dates in fresh.items():
        for date_str, current_status in dates.items():
            if current_status != "A":
                continue
            previous_status = stored.get(site_id, {}).get(date_str)
            if previous_status != "A":
                events.append(
                    AvailabilityEvent(
                        campground_name=campground_name,
                        facility_id=facility_id,
                        site_id=site_id,
                        date_str=date_str,
                        previous_status=previous_status,
                        current_status=current_status,
                    )
                )
    return events
