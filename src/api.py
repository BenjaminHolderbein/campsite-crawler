"""Recreation.gov API client."""

from __future__ import annotations

import time
from datetime import date, datetime
from typing import Any

import httpx

BASE_URL = "https://www.recreation.gov/api"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def get_availability(
    facility_id: str,
    month_date: date,
    *,
    timeout: float = 15.0,
    max_retries: int = 3,
) -> dict[str, dict[str, str]]:
    """Fetch monthly availability grid for a campground.

    Returns a mapping of site_id -> {date_str -> status_code}.
    Status codes: "A" = available, "R" = reserved, "X" = closed, etc.
    date_str format: "YYYY-MM-DDT00:00:00Z"
    """
    start = datetime(month_date.year, month_date.month, 1)
    url = f"{BASE_URL}/camps/availability/campground/{facility_id}/month"
    params = {"start_date": start.strftime("%Y-%m-%dT00:00:00.000Z")}

    delay = 1.0
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(url, params=params, headers=HEADERS)
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
                campsites: dict[str, Any] = data.get("campsites", {})
                return {
                    site_id: site_data.get("availabilities", {})
                    for site_id, site_data in campsites.items()
                }
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429 and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except httpx.RequestError:
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise

    return {}  # unreachable but satisfies type checker


def filter_by_dates(
    availability: dict[str, dict[str, str]],
    start: date,
    end: date,
) -> dict[str, dict[str, str]]:
    """Filter availability data to only include dates within [start, end]."""
    result: dict[str, dict[str, str]] = {}
    for site_id, dates in availability.items():
        filtered = {
            date_str: status
            for date_str, status in dates.items()
            if _parse_date(date_str) is not None
            and start <= _parse_date(date_str) <= end  # type: ignore[operator]
        }
        if filtered:
            result[site_id] = filtered
    return result


def _parse_date(date_str: str) -> date | None:
    """Parse a recreation.gov date string like '2026-03-14T00:00:00Z'."""
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def search_campgrounds(query: str, *, timeout: float = 15.0) -> list[dict[str, Any]]:
    """Search for campgrounds by name. Returns list of result dicts."""
    url = f"{BASE_URL}/search"
    params = {"q": query, "entity_type": "campground", "size": 10}
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url, params=params, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
