"""ReserveCalifornia availability provider, backed by camply."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from camply.containers import SearchWindow
from camply.search import SearchReserveCalifornia

from .checker import AvailabilityEvent

# Suppress camply's verbose logging
logging.getLogger("camply").setLevel(logging.ERROR)


def get_available_campsites(
    recreation_area_id: int,
    start: date,
    end: date,
    nights: int = 1,
) -> list[AvailabilityEvent] | None:
    """Return available campsites for a ReserveCalifornia recreation area.

    Uses camply to handle auth and API calls. Returns one AvailabilityEvent
    per available campsite/date combination so they flow into the existing
    notifier unchanged.

    nights: minimum consecutive nights required (default 1 = any single night).
    """
    # camply's end_date is exclusive, so add 1 day to include the last check-in night
    window = SearchWindow(start_date=start, end_date=end + timedelta(days=1))
    searcher = SearchReserveCalifornia(
        search_window=window,
        recreation_area=[recreation_area_id],
        nights=nights,
    )
    if searcher.nights < nights:
        return None
    campsites = searcher.get_matching_campsites()

    events: list[AvailabilityEvent] = []
    for site in campsites:
        if site.availability_status != "Available":
            continue
        events.append(
            AvailabilityEvent(
                campground_name=f"{site.recreation_area} — {site.facility_name}",
                facility_id=str(site.facility_id),
                site_id=site.campsite_site_name,
                date_str=site.booking_date.strftime("%Y-%m-%dT00:00:00Z"),
                previous_status=None,  # camply only returns available sites
                current_status="A",
                booking_url=f"https://reservecalifornia.com/park/{site.recreation_area_id}",
            )
        )
    return events
