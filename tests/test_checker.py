"""Tests for checker.py availability change detection."""

from src.checker import AvailabilityEvent, find_new_openings


def test_find_new_openings_detects_available():
    fresh = {"site-1": {"2026-03-14T00:00:00Z": "A"}}
    stored: dict = {}
    events = find_new_openings("Test CG", "12345", fresh, stored)
    assert len(events) == 1
    assert events[0].site_id == "site-1"
    assert events[0].current_status == "A"
    assert events[0].previous_status is None


def test_find_new_openings_no_duplicate_for_already_available():
    fresh = {"site-1": {"2026-03-14T00:00:00Z": "A"}}
    stored = {"site-1": {"2026-03-14T00:00:00Z": "A"}}
    events = find_new_openings("Test CG", "12345", fresh, stored)
    assert events == []


def test_find_new_openings_ignores_reserved():
    fresh = {"site-1": {"2026-03-14T00:00:00Z": "R"}}
    stored: dict = {}
    events = find_new_openings("Test CG", "12345", fresh, stored)
    assert events == []


def test_find_new_openings_reserved_to_available():
    fresh = {"site-2": {"2026-03-15T00:00:00Z": "A"}}
    stored = {"site-2": {"2026-03-15T00:00:00Z": "R"}}
    events = find_new_openings("Test CG", "12345", fresh, stored)
    assert len(events) == 1
    assert events[0].previous_status == "R"
    assert events[0].current_status == "A"


def test_find_new_openings_multiple_sites():
    fresh = {
        "site-1": {"2026-03-14T00:00:00Z": "A"},
        "site-2": {"2026-03-14T00:00:00Z": "R"},
        "site-3": {"2026-03-14T00:00:00Z": "A"},
    }
    stored = {"site-3": {"2026-03-14T00:00:00Z": "A"}}
    events = find_new_openings("Test CG", "12345", fresh, stored)
    assert len(events) == 1
    assert events[0].site_id == "site-1"


def test_event_fields():
    fresh = {"site-99": {"2026-03-14T00:00:00Z": "A"}}
    stored: dict = {}
    events = find_new_openings("Yosemite Valley", "232447", fresh, stored)
    e = events[0]
    assert isinstance(e, AvailabilityEvent)
    assert e.campground_name == "Yosemite Valley"
    assert e.facility_id == "232447"
    assert e.date_str == "2026-03-14T00:00:00Z"
