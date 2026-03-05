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


def run_once(config: dict) -> int:
    """Run a single check across all campgrounds. Returns count of openings found."""
    dr = config.get("date_range", {})
    start = datetime.strptime(dr["start"], "%Y-%m-%d").date()
    end = datetime.strptime(dr["end"], "%Y-%m-%d").date()
    months = _months_in_range(start, end)

    current_state = state.load()
    total_openings = 0

    for cg in config.get("campgrounds", []):
        name = cg["name"]
        fid = cg["facility_id"]
        print(f"Checking {name} (facility {fid})...", flush=True)

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
            events = checker.find_new_openings(name, fid, fresh, stored)

            if events:
                print(f"  Found {len(events)} new opening(s)!")
                notifier.notify(events)
                total_openings += len(events)
            else:
                available_count = sum(
                    1
                    for dates in fresh.values()
                    for s in dates.values()
                    if s == "A"
                )
                print(f"  No new openings. ({available_count} currently available)")

            state.update_campground_state(current_state, fid, fresh)

        except Exception as exc:
            print(f"  Error fetching {name}: {exc}", file=sys.stderr)

    state.save(current_state)
    return total_openings


def main() -> None:
    parser = argparse.ArgumentParser(description="Poll recreation.gov for campsite availability")
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
        openings = run_once(config)
        sys.exit(0 if openings == 0 else 0)

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
