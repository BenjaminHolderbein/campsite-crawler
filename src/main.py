"""Entry point: polling loop for campsite availability."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from . import api, checker, notifier, state
from . import reservecalifornia as rc

load_dotenv()


def _load_config(path: str = "config.yaml") -> dict:
    config_path = Path(path)
    if not config_path.exists():
        print(f"Error: config file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(config_path) as f:
        return yaml.safe_load(f)


def _months_in_range(start: date, end: date) -> list[date]:
    """Return the first-of-month dates covering [start, end]."""
    months = []
    current = date(start.year, start.month, 1)
    while current <= end:
        months.append(current)
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return months


def _poll_recreation_gov(config: dict, current_state: dict, start: date, end: date) -> int:
    months = _months_in_range(start, end)
    min_nights = (end - start).days + 1
    total = 0
    for cg in config.get("recreation_gov", []):
        name = cg["name"]
        fid = cg["facility_id"]
        print(f"[rec.gov] Checking {name}...", flush=True)
        try:
            fresh: dict[str, dict[str, str]] = {}
            for month in months:
                month_data = api.get_availability(fid, month)
                filtered = api.filter_by_dates(month_data, start, end)
                for site_id, dates in filtered.items():
                    if site_id not in fresh:
                        fresh[site_id] = {}
                    fresh[site_id].update(dates)

            stored = state.get_campground_state(current_state, fid)
            events = checker.find_new_openings(name, fid, fresh, stored, min_nights=min_nights)

            if events:
                print(f"  Found {len(events)} new opening(s)!")
                notifier.notify(events)
                total += len(events)
            else:
                available_count = sum(
                    1 for dates in fresh.values() for s in dates.values() if s == "A"
                )
                print(f"  No new openings. ({available_count} currently available)")

            state.update_campground_state(current_state, fid, fresh)

        except Exception as exc:
            print(f"  Error: {exc}", file=sys.stderr)
    return total


def _poll_reserve_california(config: dict, current_state: dict, start: date, end: date) -> int:
    total = 0
    nights = (end - start).days + 1
    for cg in config.get("reservecalifornia", []):
        name = cg["name"]
        area_id = int(cg["recreation_area_id"])
        state_key = f"rc:{area_id}"
        print(f"[ReserveCalifornia] Checking {name}...", flush=True)
        try:
            available = rc.get_available_campsites(area_id, start, end, nights=nights)
            if available is None:
                print(f"  Skipped (max stay shorter than {nights} nights)")
                continue

            # Build fresh availability map: site_id -> date_str -> "A"
            fresh: dict[str, dict[str, str]] = {}
            for event in available:
                if event.site_id not in fresh:
                    fresh[event.site_id] = {}
                fresh[event.site_id][event.date_str] = "A"

            stored = state.get_campground_state(current_state, state_key)
            # Preserve booking_url per site from the fresh events
            url_map = {e.site_id: e.booking_url for e in available}

            new_events = checker.find_new_openings(name, state_key, fresh, stored)
            # Restore booking_url (find_new_openings doesn't have it)
            for e in new_events:
                e.booking_url = url_map.get(e.site_id, "")

            if new_events:
                print(f"  Found {len(new_events)} new opening(s)!")
                notifier.notify(new_events)
                total += len(new_events)
            else:
                print(f"  No new openings. ({len(available)} currently available)")

            state.update_campground_state(current_state, state_key, fresh)

        except Exception as exc:
            print(f"  Error: {exc}", file=sys.stderr)
    return total


def run_once(config: dict) -> int:
    """Run a single check across all campgrounds. Returns count of openings found."""
    dr = config.get("date_range", {})
    start = datetime.strptime(dr["start"], "%Y-%m-%d").date()
    end = datetime.strptime(dr["end"], "%Y-%m-%d").date()

    current_state = state.load()
    total = 0
    total += _poll_recreation_gov(config, current_state, start, end)
    total += _poll_reserve_california(config, current_state, start, end)
    state.save(current_state)
    return total


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Poll recreation.gov and ReserveCalifornia for campsite availability"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single check and exit (useful for cron jobs)",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    args = parser.parse_args()
    config = _load_config(args.config)

    if args.once:
        run_once(config)
        sys.exit(0)

    interval = config.get("poll_interval_seconds", 60)
    print(f"Starting campsite poller (interval: {interval}s). Press Ctrl+C to stop.")
    try:
        while True:
            run_once(config)
            print(f"Sleeping {interval}s...", flush=True)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
