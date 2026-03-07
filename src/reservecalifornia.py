"""ReserveCalifornia availability provider, backed by camply."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import date, timedelta

from camply.containers import SearchWindow
from camply.search import SearchReserveCalifornia

from .checker import AvailabilityEvent

# Suppress camply's verbose logging
logging.getLogger("camply").setLevel(logging.ERROR)

# Wall-clock timeout for the entire camply call (init + HTTP requests).
# camply can hang indefinitely on slow/stalled ReserveCalifornia API responses.
_CAMPLY_WALL_TIMEOUT = 60  # seconds


def _run_camply(recreation_area_id: int, start: date, end: date, nights: int):
    """Run inside a thread so we can enforce a wall-clock timeout."""
    window = SearchWindow(start_date=start, end_date=end + timedelta(days=1))
    searcher = SearchReserveCalifornia(
        search_window=window,
        recreation_area=[recreation_area_id],
        nights=nights,
    )
    if searcher.nights < nights:
        return None
    return searcher.get_matching_campsites()


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
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(_run_camply, recreation_area_id, start, end, nights)
    try:
        campsites = future.result(timeout=_CAMPLY_WALL_TIMEOUT)
    except FuturesTimeoutError:
        pool.shutdown(wait=False)
        raise TimeoutError(
            f"ReserveCalifornia check timed out after {_CAMPLY_WALL_TIMEOUT}s"
        )
    pool.shutdown(wait=False)

    if campsites is None:
        return None

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
