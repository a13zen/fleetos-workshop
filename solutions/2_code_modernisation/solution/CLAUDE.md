# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project
Code modernisation challenge: rewrite the legacy Flask fleet tracker (`legacy_fleettracker/`) as a FastAPI service. Python 3.13, managed with `uv`.

## Setup
```
source .venv/bin/activate
```

## Run commands
- Legacy app: `python legacy_fleettracker/app.py` (http://localhost:5000/status)
- FastAPI target: `uvicorn <module>:app --reload`
- Tests: `pytest`

## Critical gotchas (do not get these wrong)
- `/report` uses `OLD_INTERVAL_KM = 25000` intentionally (frozen by Finance). Do NOT change to 30000. CSV column order in /report output is also frozen — a downstream Excel macro depends on it.
- `calc_next_service()` is canonical. The copy inside `report_handler` is explicitly stale — treat them as independent.
- `/admin/recalc` was disabled — leave it disabled.
- EV service interval is hardcoded (40000 km / 12 months per 2021 memo); `SERVICE_INTERVAL_MONTHS_EV` constant is commented out by design.
- `DEBUG = True` is hardcoded in legacy app — must not carry over to the FastAPI rewrite.
- Timezone handling is known-broken for end-of-month dates (February uses a 28-day fallback). Preserve the behaviour, don't fix it.

## Storage
CSV files in `legacy_fleettracker/data/` are the only data source. The MySQL backend was dropped; the SQLite migration in `db_utils.py` was never completed. The modernised app should read from the same CSVs unless the task specifies otherwise.

## Testing
`pytest` + `httpx` are in `requirements.txt`. Use `httpx.AsyncClient` / FastAPI `TestClient` for endpoint tests.
