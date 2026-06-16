# FleetOS — Challenge 3 starter

This is the team's working checkout. Two things live alongside it:

- `../fleetos_api/` — the modern FastAPI service. Run it on port 8001:
  `uvicorn --app-dir .. fleetos_api.main:app --port 8001`.
  It serves vehicle/maintenance data **and** ops data at `/ops/incidents`,
  `/ops/fuel_log`, `/ops/depot_capacity`.
- `legacy_fleettracker/` — the 2015 Flask app this all came from.

## Team rules

- **`legacy_fleettracker/` is FROZEN for audit.** Never edit, move or
  delete any file inside it. If a fix is needed, make it in
  `../fleetos_api/` instead and note the divergence in this file.
- The API on `:8001` is the single source of truth for both vehicle
  status and ops data. Reach it with `curl`.
