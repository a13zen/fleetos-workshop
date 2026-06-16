---
name: legacy-modernise
description: Step-by-step methodology for extracting business logic from a legacy web app into a clean, layered modern service. Trigger when asked to modernise, refactor, or port a legacy codebase to FastAPI (or similar). Covers analysis, characterisation tests, four-layer architecture, parity verification, and retirement criteria.
---

Follow these five phases in strict order. Do not skip ahead.

## Phase 1 — Analyse

1. Read every route handler and list: path, HTTP method, inputs, outputs.
2. Read every non-route function and map call dependencies (who calls whom).
3. Read all data files, config, and `__init__` imports.
4. Cross-examine docs (`README`, `NOTES`, comments) against the code. Produce a table: **Claim · Reality · Evidence (file:line)**.
5. List separately: (a) unreferenced functions and constants, (b) commented-out routes, (c) imports that go nowhere.
6. Write the component diagram to `diagram.md` at the project root using Mermaid; use subgraphs for routes, business logic, data layer, files, and templates.

## Phase 2 — Characterise

1. Write `tests/test_legacy_behaviour.py` importing the legacy functions directly (adjust `sys.path` as needed).
2. Pick test vehicles/records that cover every enum value, the highest-stress case, and edge cases (never-serviced, retired threshold, grace boundary).
3. Use a single fixed `TODAY = date(YYYY, MM, DD)` constant so tests are deterministic.
4. Assert exact return values — **do not round, normalise, or fix odd-looking outputs**. Record quirks as-is; they are the specification.
5. Run `pytest` and confirm all pass before proceeding.

## Phase 3 — Plan the four layers

Present the plan in plan mode before writing any code. The four layers are:

| Layer | File | Rule |
|---|---|---|
| Models | `models.py` | Pydantic models + Enums only; no I/O, no logic |
| Data | `data_loader.py` | File/DB reads only; returns typed models; no business logic |
| Service | `maintenance.py` | Pure functions; all arguments explicit; no I/O |
| Routes | `main.py` | FastAPI app; calls data layer then service layer; CORS |

Document every quirk from Phase 1 that must be preserved (e.g. frozen constants, negative-days guard, month-arithmetic hack).

## Phase 4 — Port and verify parity

1. Implement the four layers bottom-up: models → data_loader → service → routes.
2. Write `tests/test_<package>.py` mirroring the Phase 2 tests: same vehicles, same `TODAY`, same expected values — using the new functions.
3. Run both test files together: `pytest tests/`. **If a parity test fails, fix the new code, never the expected value.**
4. Write focused unit tests (`tests/test_<service>.py`) using synthetic fixtures (no CSV loading) covering each rule independently: each interval type, each status boundary, each priority formula component, the priority cap.
5. Spawn a verifier agent to confirm all tests pass and layers are correctly separated before reporting done.

## Phase 5 — Retire

Delete the legacy entry point only when **all** of the following are true:

- All parity tests pass with no skips.
- The new API is reachable and returns correct data for every legacy endpoint's use-case.
- No external system still calls the legacy routes (check network logs or grep call-sites).
- A `CHANGELOG` entry or PR description documents the intentional quirks that were preserved and why.
