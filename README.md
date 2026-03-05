# Campsite Crawler

Polls recreation.gov for campsite availability and sends a push notification the moment a site opens up.

## How it works

The recreation.gov website uses a public JSON API for its own frontend — no scraping, no auth token required. This tool calls that same API on a configurable interval, compares results against the last known state, and fires a notification only when something new becomes available.

## Setup

**1. Install dependencies**
```bash
uv sync
```

**2. Configure your campgrounds and dates**

Edit `config.yaml`:
```yaml
poll_interval_seconds: 60

campgrounds:
  - name: "Yosemite Valley Campground"
    facility_id: "232447"

date_range:
  # These are check-in dates (nights you want to stay), not check-out dates.
  start: "2026-06-14"
  end: "2026-06-15"
```

To find a facility ID, go to the campground page on recreation.gov — the number in the URL is the ID:
```
https://www.recreation.gov/camping/campgrounds/232447
                                                 ^^^^^^
```

Or use the search helper:
```bash
uv run python -m src.search "Yosemite Valley"
```

**3. Set up push notifications (optional)**

Copy `.env.example` to `.env` and set a topic name. Any unique string works — no account needed.
```bash
cp .env.example .env
# edit .env and set NTFY_TOPIC=your-unique-topic-name
```

Then install the [ntfy app](https://ntfy.sh) on your phone and subscribe to the same topic. Notifications include a **Book Now** button that opens the recreation.gov booking page directly.

## Running

```bash
# Continuous polling (recommended — leave running in a terminal or as a service)
uv run python -m src.main

# Single check and exit (good for cron jobs)
uv run python -m src.main --once

# Use a different config file
uv run python -m src.main --config my-config.yaml
```

## Running as a background service (macOS)

To keep the poller running automatically, create a launchd plist. Replace the paths with your own:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.campsite-crawler</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOU/.local/bin/uv</string>
        <string>run</string>
        <string>--project</string>
        <string>/Users/YOU/campsite-crawler</string>
        <string>python</string>
        <string>-m</string>
        <string>src.main</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/YOU/campsite-crawler</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/campsite-crawler.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/campsite-crawler.log</string>
</dict>
</plist>
```

Save it to `~/Library/LaunchAgents/com.user.campsite-crawler.plist`, then load it:
```bash
launchctl load ~/Library/LaunchAgents/com.user.campsite-crawler.plist
```

## Running tests

```bash
uv run pytest tests/ -v
```
