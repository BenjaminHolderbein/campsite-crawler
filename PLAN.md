# Campsite Availability Notifier — PLAN.md

## Goal

Poll recreation.gov for campsite availability across a configurable list of campgrounds and date ranges. Send a push notification via ntfy.sh immediately when an available site appears.

---

## How Recreation.gov Works

Recreation.gov has an **unofficial but stable API** used by its own frontend. No scraping needed — we call the same JSON endpoints the browser does:

- **Availability endpoint**: `https://www.recreation.gov/api/camps/availability/campground/{facility_id}/month?start_date={YYYY-MM-01T00:00:00.000Z}`
  - Returns a dict of site IDs → date availability maps (`"A"` = available, `"R"` = reserved, `"X"` = closed, etc.)
- **Campground search**: `https://www.recreation.gov/api/search?q={name}&entity_type=campground`
  - Returns facility IDs and metadata for searching campgrounds by name

No auth token required for availability checks (public data). A browser-like `User-Agent` header is sufficient.

---

## Architecture

```
campsite-crawler/
├── PLAN.md
├── README.md
├── pyproject.toml          # uv-managed deps: httpx, pyyaml, python-dotenv
├── .env.example            # ntfy.sh topic config
├── config.yaml             # campgrounds to watch + date ranges
├── src/
│   ├── __init__.py
│   ├── main.py             # entry point: run the polling loop
│   ├── api.py              # recreation.gov API client
│   ├── checker.py          # availability logic: compare current vs. last known state
│   ├── notifier.py         # notification dispatch (ntfy.sh push + stdout)
│   └── state.py            # persist last-known availability to disk (JSON)
└── tests/
    ├── test_api.py
    └── test_checker.py
```

---

## Core Components

### 1. `config.yaml` — What to Watch

```yaml
poll_interval_seconds: 60

campgrounds:
  - name: "Yosemite Valley Campground"
    facility_id: "232447"
  - name: "Big Sur Pfeiffer"
    facility_id: "233116"

date_range:
  start: "2026-03-14"   # next weekend Saturday
  end: "2026-03-15"     # next weekend Sunday
```

The facility ID comes from the recreation.gov URL or the search API.

### 2. `api.py` — Recreation.gov Client

- `get_availability(facility_id, month_date) -> dict[site_id, dict[date, status]]`
  - Fetches the monthly availability grid
  - Handles rate limiting with exponential backoff
  - Filters to only the dates in our range

### 3. `checker.py` — Change Detection

- Loads last-known state from `state.py`
- Compares fresh API data against stored state
- Returns a list of `AvailabilityEvent(campground, site_id, date, previous_status, current_status)`
- Only triggers notifications for `* -> "A"` transitions (something opened up)

### 4. `state.py` — Persistence

- Reads/writes `state.json` to track last seen availability per site per date
- Prevents duplicate notifications across polling cycles

### 5. `notifier.py` — Alerts

Sends via ntfy.sh (configured via `.env`):

- `httpx.post("https://ntfy.sh/{topic}", content=message)` — one API call, no auth needed
- Also always prints to stdout for logging

Message format:
```
[CAMPSITE ALERT] {campground_name}
Site {site_id} is now AVAILABLE on {date}
Book now: https://www.recreation.gov/camping/campsites/{site_id}
```

### 6. `main.py` — Polling Loop

```
while True:
  for each campground in config:
    fetch availability for relevant months
    run checker
    if new openings found:
      dispatch notifications
  sleep(poll_interval_seconds)
```

---

## Execution Model

This plan is executed by a single **orchestrator** that spawns multiple parallel **subagents** — one per component or phase. Each subagent is responsible for implementing its assigned module and verifying its own functionality before signaling completion to the orchestrator.

**Verification requirement:** Every component must be verified functional before the orchestrator moves on. Verification methods (in order of preference):
1. Run the module's unit tests (`uv run pytest tests/`)
2. Run a quick smoke test (e.g., `uv run python -c "from src.api import get_availability; ..."`)
3. Manual check of expected output/behavior

The orchestrator integrates subagent outputs and runs a final end-to-end smoke test after all phases are complete.

---

## Implementation Phases

### Phase 1 — Core Polling (MVP)
- [ ] Set up `pyproject.toml` with dependencies
- [ ] Implement `api.py` with the recreation.gov availability endpoint
- [ ] Implement `checker.py` with state comparison
- [ ] Implement `state.py` for JSON persistence
- [ ] `main.py` polling loop with stdout notifications
- [ ] `config.yaml` with example campgrounds

### Phase 2 — Notifications
- [ ] `notifier.py` with ntfy.sh push support
- [ ] `.env.example` with ntfy topic key

### Phase 3 — Quality of Life
- [ ] `README.md` with setup instructions and how to find facility IDs
- [ ] `--once` flag for a single check (useful for cron jobs)
- [ ] Campground search helper: `python -m src.search "Yosemite"` → prints facility IDs
- [ ] Basic tests for checker logic

### Phase 4 — Optional Enhancements
- [ ] Run as a launchd plist (macOS) or systemd service for always-on monitoring
- [ ] Multiple date ranges per campground
- [ ] Filter by site type (tent-only, RV hookups, etc.)
- [ ] Run as a launchd plist (macOS) for always-on monitoring

---

## Key Technical Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| HTTP client | `httpx` | Sync/async, good timeout handling |
| Config format | YAML | Human-readable, easy to edit |
| Scheduling | `time.sleep` loop | Simple; no scheduler dependency for MVP |
| State storage | JSON file | Zero infrastructure, good enough for one user |
| Notifications | ntfy.sh push | Free, no account, one HTTP call, great mobile app |
| Language | Python | httpx + stdlib; quick to iterate |

---

## Finding Facility IDs

1. Go to recreation.gov and search for a campground
2. Click through to the campground page
3. The URL will be `https://www.recreation.gov/camping/campgrounds/{FACILITY_ID}`
4. Use that number in `config.yaml`

Or use the search helper once Phase 3 is done:
```bash
python -m src.search "Pfeiffer Big Sur"
```

---

## Running It

```bash
# Install deps
uv sync

# Configure
cp .env.example .env
# edit config.yaml with your campgrounds and dates

# Run
uv run python -m src.main

# One-shot check (Phase 3)
uv run python -m src.main --once
```
