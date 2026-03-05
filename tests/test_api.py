"""Tests for api.py helper functions (no network calls)."""

from datetime import date

from src.api import _parse_date, filter_by_dates


def test_parse_date_valid():
    d = _parse_date("2026-03-14T00:00:00Z")
    assert d == date(2026, 3, 14)


def test_parse_date_invalid():
    assert _parse_date("not-a-date") is None
    assert _parse_date("") is None


def test_filter_by_dates_includes_boundary():
    availability = {
        "site-1": {
            "2026-03-13T00:00:00Z": "A",
            "2026-03-14T00:00:00Z": "A",
            "2026-03-15T00:00:00Z": "R",
            "2026-03-16T00:00:00Z": "A",
        }
    }
    result = filter_by_dates(availability, date(2026, 3, 14), date(2026, 3, 15))
    assert "site-1" in result
    assert set(result["site-1"].keys()) == {
        "2026-03-14T00:00:00Z",
        "2026-03-15T00:00:00Z",
    }


def test_filter_by_dates_excludes_site_with_no_dates_in_range():
    availability = {
        "site-1": {"2026-03-10T00:00:00Z": "A"},
    }
    result = filter_by_dates(availability, date(2026, 3, 14), date(2026, 3, 15))
    assert result == {}


def test_filter_by_dates_empty():
    result = filter_by_dates({}, date(2026, 3, 14), date(2026, 3, 15))
    assert result == {}
