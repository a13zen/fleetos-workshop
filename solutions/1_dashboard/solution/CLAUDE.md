# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FleetOS vehicle dashboard — a vanilla HTML/CSS/JavaScript frontend with no build step. The app loads vehicle fleet data from `data/vehicles.json` and renders summary stats and a data table.

## Running the Project

Serve locally with Python:

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000 in a browser.

## Code Structure

- **index.html** — Page structure and table markup
- **app.js** — Loads vehicle data and renders summary stats + vehicle table
- **styles.css** — Styling (CSS variables for theming)
- **data/vehicles.json** — Fleet vehicle records (id, make, model, status, mileage_km, etc.)

## Important Details

- The app uses `fetch()` to load `data/vehicles.json`; requires serving over HTTP, not file:// URLs.
- Dates are formatted as-is from the JSON; mileage uses German locale formatting (`de-DE`).
- Status values: `active`, `maintenance`, `overdue`; each has a CSS class for styling.
- The "Service Due" column currently displays the same value as "Last Service" — this may be intentional or a placeholder.
- No linting, testing, or build tools configured.
