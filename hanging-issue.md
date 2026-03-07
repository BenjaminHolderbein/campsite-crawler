# Hanging Issue — ReserveCalifornia / camply

## Status: RESOLVED (Option A implemented)

## Symptom
The poller hangs indefinitely on certain ReserveCalifornia campgrounds (varies by run — seen on Sonoma Coast SP, MacKerricher SP). It always checks the first few parks fine, then stalls mid-loop on subsequent iterations.

## Root Cause (confirmed)
camply's HTTP calls in `base_provider.py:make_http_request` pass **no `timeout=`** to `requests.Session.request`:
```python
response = self.session.request(method=method, url=url, data=data, headers=headers)
```
This means any stalled TCP connection or slow DNS hangs forever.

## What Was Tried

### Attempt 1: `patch.object(requests.Session, "request", ...)` inside the call
Did not work — camply's session instances are created before/during `SearchReserveCalifornia.__init__`, so a context-manager patch around `get_matching_campsites()` is too late.

### Attempt 2: Class-level monkey-patch at module import time
```python
requests.Session.request = _request_with_timeout  # injects timeout=30
```
Confirmed via test that the patch IS applied and timeout fires correctly on a test request. BUT the hang persists — likely because the hang happens during DNS resolution or TCP connect *inside* the `SearchReserveCalifornia.__init__` constructor (which calls `find_campgrounds` → `refresh_metadata` → multiple HTTP calls to fetch park metadata). The `requests` timeout parameter covers connect+read but not DNS lookup.

### Attempt 3: ThreadPoolExecutor wall-clock timeout (current code)
```python
with ThreadPoolExecutor(max_workers=1) as pool:
    future = pool.submit(_run_camply, ...)
    campsites = future.result(timeout=60)
```
This should work in theory — `future.result(timeout=60)` returns to the caller after 60s regardless. BUT: Python threads cannot be forcibly killed, so the hung thread lingers in the background. When `ThreadPoolExecutor.__exit__` is called, it calls `shutdown(wait=True)` which **blocks until all threads finish** — defeating the timeout entirely.

## Next Steps to Try

### Option A: `ThreadPoolExecutor(max_workers=1)` with `shutdown(wait=False)`
Don't use it as a context manager — call `pool.shutdown(wait=False)` manually after the timeout so the hung thread is abandoned:
```python
pool = ThreadPoolExecutor(max_workers=1)
future = pool.submit(_run_camply, ...)
try:
    campsites = future.result(timeout=60)
except FuturesTimeoutError:
    pool.shutdown(wait=False)
    raise TimeoutError(...)
pool.shutdown(wait=False)
```

### Option B: `multiprocessing` instead of threading
A subprocess CAN be forcibly killed. Use `multiprocessing.Process` or `concurrent.futures.ProcessPoolExecutor` — killing the process truly interrupts the hung socket:
```python
from concurrent.futures import ProcessPoolExecutor
with ProcessPoolExecutor(max_workers=1) as pool:
    future = pool.submit(_run_camply, ...)
    campsites = future.result(timeout=60)
# On timeout, ProcessPoolExecutor kills the worker process
```
Downside: pickling overhead, but AvailabilityEvent is a dataclass so it should serialize fine.

### Option C: subprocess + JSON
Spawn `uv run python -m src._rc_worker <area_id> <start> <end> <nights>` as a subprocess with a timeout, have it print JSON to stdout, parse it in the parent. Most robust but most code.

## Current State of Code
- [src/reservecalifornia.py](../src/reservecalifornia.py) — uses ThreadPoolExecutor approach (Attempt 3, broken due to `wait=True` on shutdown)
- [src/main.py](../src/main.py) — catches `SystemExit` (camply's no-results exit) and `Exception`
- [config.yaml](../config.yaml) — Manchester SP ID fixed from 586 → 671
