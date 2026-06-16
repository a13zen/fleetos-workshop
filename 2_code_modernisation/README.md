# Challenge 2 - Modernise Legacy FleetTracker

You have inherited **FleetTracker**: a Flask app first written in 2015 and
patched by a rotating cast ever since. It holds the company's real
maintenance rules - service intervals, overdue thresholds, priority
scoring - tangled up with route handlers, dead code, and a CSV layer that
was meant to be temporary in 2018.

Over the next ~1-2 hours you will use Claude Code to map this unfamiliar
codebase, pin its current behaviour with tests, extract the maintenance
logic into a clean and modern FastAPI service, and wire that service up to
a live dashboard.

## Folder layout

| Folder | Purpose |
| --- | --- |
| `starter/` | **Work here.** Contains `legacy_fleettracker/` (the inherited app) and is where you'll create `fleetos_api/`. All steps below assume you are inside this folder. |
| `dashboard/` | A ready-made FleetOS dashboard. You'll point this at your new API in Step 5. **Don't edit this** - just serve it. |

> 💡 **Built your own FleetOS dashboard in Challenge 1?** Feel free to copy your `starter/` contents over to the bundled `dashboard/` folder so you can keep using your own design in this challenge. Just ask Claude to copy it over for you!

## Who this is for

This is the **intermediate** level challenge. You should be
comfortable reading Python and have a rough sense of what a web API looks
like; you don't need prior Flask or FastAPI experience.

Run this challenge on **Sonnet**. You'll be asking for multi-file refactors
and test generation across a messy codebase - work that benefits from a
stronger reasoning model.

A ready-made dashboard is bundled in `dashboard/` so this challenge stands
alone - you'll wire it up in Step 5.

By the end you'll know how to use Claude Code to map an unfamiliar legacy
codebase, pin its behaviour with characterisation tests before changing
anything, drive a structured refactor with plan mode, and stand up a modern
service that preserves the old logic exactly.

---

## Step 0 - Setup (~5 min)

You'll need [`uv`](https://docs.astral.sh/uv/) - install it with
`curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS/Linux) or
`winget install astral-sh.uv` (Windows), or use the plain-venv fallback
below.

From `starter/`, create one virtual environment for the whole challenge
(legacy app + the new API you'll build), then install and run FleetTracker:

```bash
cd starter
uv venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
python legacy_fleettracker/app.py
```

<details>
<summary><b>No <code>uv</code>?</b> Use a plain venv instead.</summary>

```bash
cd starter
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python legacy_fleettracker/app.py
```
</details>

Open <http://localhost:5000/status> and look at what FleetTracker produces
today. This table is the behaviour you must preserve.

Leave that server running. In a **new terminal**, `cd` back into `starter/`
and start Claude Code there (so it can see the legacy app *and* the new code
you'll write alongside it):

```bash
cd starter
source .venv/bin/activate          # Windows: .venv\Scripts\activate
claude
```

Inside Claude Code:

1. Run `/model` and select **Sonnet**.
2. Run `/init`. Claude will scan the project and generate a `CLAUDE.md` file
   summarising what it found. If prompted for a location, choose
   **Project-level** so it lands here in `starter/`, not at the repo root. For now do not setup skills or hooks, only CLAUDE.md.
   Claude may ask you some questions while this runs, answer these as you'd like.

   > 📝 **Note:** There is already a base `CLAUDE.md` in the `2_code_modernisation/` folder. **Do not change it.** It exists purely to stop Claude from spotting (and spoiling) the planted bugs while `/init` scans the code - Claude is very smart! Leave that file as-is and let `/init` create an update one.

3. Open the generated `CLAUDE.md` and read over it. This is the project memory
   Claude will carry into every future turn.

   > 💡 **Ask yourself:** Is there anything here you could remove the CLAUDE.md which Claude would already know? Remember Claude Code loads the whole file as context.
   > Is there anything you could add that Claude couldn't infer from the code?

### 🔐 About Permissions

As Claude works it will need to run commands (start a server, edit a file, run a script). Each time it does something new, you'll be prompted to approve it. You have three choices:

| Option | What happens |
| --- | --- |
| **Allow once** | Runs this one command. You'll be asked again next time. |
| **Allow for session** | Runs this command for the rest of this Claude Code session without asking again. |
| **Always allow** | Saves the permission to `.claude/settings.local.json` in the current directory, so it persists across future sessions. |

You can review or edit saved permissions at any time by opening `.claude/settings.local.json`, or by running `/permissions` inside Claude Code.

> 💡 For this challenge, just pick **Allow for session** when prompted so you're not interrupted repeatedly.

## Step 1 - Analyse the legacy code (~20 min)

You don't refactor what you don't understand, and you don't trust docs that
predate the code. Start by building your own map: ask Claude to read the
legacy app and produce a Mermaid component diagram of it.

Your prompt should cover:

- which files to read (`legacy_fleettracker/app.py`, `db_utils.py`)
- where to write the output (`diagram.md` at the `starter/` root)
- what to include as nodes - routes, functions, the data layer, the CSV
  data files, the Jinja2 template
- directed edges for every call/dependency, grouped into subgraphs
  (routes / business logic / data layer / files / templates)
- annotations on edges for any intentional quirks (frozen constants,
  disabled routes)
- output guardrail: `diagram.md` must contain **only** the raw Mermaid
  code block - no intro text, no explanation, no trailing commentary

<details>
<summary><strong>🤔 Stuck? Example prompt (click to expand)</strong></summary>

> Read legacy_fleettracker/app.py and legacy_fleettracker/db_utils.py, then write a Mermaid component diagram to diagram.md at the project root (starter/) showing: all routes, all functions, the data layer (db_utils.py), data files (vehicles.csv, service_history.csv), and the Jinja2 template - with directed edges for every call/dependency. Annotate any intentional quirks (e.g. frozen constants, disabled routes) on the relevant edges. Use subgraphs to group routes, business logic, data layer, files, and templates. Write diagram.md containing ONLY the raw Mermaid code block - no introduction, no explanation, no trailing commentary. The file must start with ` ```mermaid ` and end with ` ``` ` and contain nothing else.

</details>
<br>

Open `diagram.md` to see the result. VS Code renders Mermaid in its Markdown
preview (⇧⌘V / Ctrl+Shift+V); otherwise paste the block into
<https://mermaid.live>.

Now turn to the documentation that came with the app. The legacy folder `legacy_fleettracker/`
includes a `README.md` and a `NOTES.txt` left by previous maintainers - but
docs that old rarely match the code. Treat them as evidence to
cross-examine, not facts to trust. Ask Claude to compare what the docs
*claim* against what the code actually *does*.

Your prompt should cover:

- which docs to audit (`legacy_fleettracker/README.md`, `NOTES.txt`)
- the output format - a table with Claim · Reality · Evidence
  (file:line) columns
- a separate inventory of dead code: unreferenced functions/constants,
  commented-out routes, imports that go nowhere

<details>
<summary><strong>🤔 Stuck? Example prompt (click to expand)</strong></summary>

> Compare what legacy_fleettracker/README.md and legacy_fleettracker/NOTES.txt claim against what the code actually does. Produce a table with columns: Claim · Reality · Evidence (file:line). Then list separately: (a) unreferenced functions and constants, (b) commented-out routes, (c) imports that go nowhere.

</details>
<br>

Now dig into the part that matters - the maintenance rules. Ask Claude to
walk you through the three core functions in `app.py`.

Your prompt should cover:

- the three functions to explain: `calc_next_service`, `calc_status`,
  `calc_priority`
- for each one: inputs, rules applied (with exact constants), output,
  and any edge cases or `vehicle_class` special-casing
- a request to flag anywhere two code paths compute the same thing
  differently

<details>
<summary><strong>🤔 Stuck? Example prompt (click to expand)</strong></summary>

> Explain the maintenance logic in legacy_fleettracker/app.py. For each of calc_next_service, calc_status, and calc_priority: list the inputs, the rules applied (with the exact constants), the output, and any edge cases or special-casing by vehicle_class. Point out anywhere two code paths compute the same thing differently.

</details>
<br>

By the end of this step you should be able to answer, in your own words:

- What are the service intervals, and how do they differ by vehicle class?
- What makes a vehicle `overdue` versus `maintenance` versus `retired`?
- How is the priority score (0–100) calculated?
- Where is logic duplicated, and which copy is authoritative?

If you can't answer any of the above, ask Claude!

Read `NOTES.txt` yourself too - Claude will, but you should know what the
last maintainer thought was important.

Finish with `/context`. How much of Sonnet's window did that analysis cost,
and what's filling it?

> 💡 **Tip:** On a larger codebase you'd delegate this to an exploration
> subagent (`@Explore` or the Task tool) so the raw file contents don't
> flood your main context. This app is small enough to do inline, but try it
> if you're curious - then compare `/context` before and after.

## Step 2 - Characterisation tests (~20 min)

This is the **golden dataset** idea from the demo, applied at the function
level: before changing anything, capture the *current* behaviour as
tests - bugs and all. Those outputs become the contract. If the new code
produces the same results for the same inputs, the refactor is
faithful - and if a test fails, you fix the new code, never the test.

Ask Claude to write a characterisation test file that pins down what the
legacy functions return *today*, then run it. The file should sit in a new 
`tests/` folder. Call the new test file `test_legacy_behaviour.py`.

Your prompt should cover:

- the target file: `tests/test_legacy_behaviour.py`
- importing `calc_next_service`, `calc_status`, `calc_priority` from
  `legacy_fleettracker/app.py` (and handling `sys.path` so it works
  from the `starter/` root)
- picking ~6 vehicles from `data/vehicles.csv` that span every
  `vehicle_class`, plus the highest-mileage one and one with no service
  history if any exists
- a fixed `today=date(2025, 11, 1)` so the tests are deterministic
- the golden rule: record outputs **as-is**, don't "fix" anything that
  looks odd
- run `pytest` at the end and show the result

<details>
<summary><strong>🤔 Stuck? Example prompt (click to expand)</strong></summary>

> Write tests/test_legacy_behaviour.py. Import calc_next_service, calc_status and calc_priority from legacy_fleettracker/app.py (handle the sys.path so the import works from the starter/ root). Pick 6 vehicles from data/vehicles.csv covering every vehicle_class plus the highest-mileage one and one with no service history if any exists. For each, assert the exact return values of all three functions using today=date(2025, 11, 1) so the tests are deterministic. Do not "fix" any odd-looking outputs - record them as-is. Then run pytest and show me the result.

</details>
<br>

Make sure all tests pass against the legacy code -- if anything looks odd, don't fix it, record it as-is. You now have an executable specification.

> 💡 **Spotted something odd?** A test output may look like a bug (for example, future-dated service records triggering "maintenance" indefinitely). That is a real bug in the legacy code. Your job right now is to preserve it, not fix it. Your characterisation tests are doing exactly what they should. Fix bugs separately, in a dedicated PR, after the refactor is complete.

## Step 3 - Plan the extraction (~15 min)

You're going to modernise **one slice** end to end - the maintenance
endpoint - not the whole app. Depth over breadth: get the pattern right
once, then it's repeatable.

Run `/plan`, then describe the extraction. Claude will explore, ask
clarifying questions, and produce an implementation plan for you to
review.

Your prompt should cover:

- the destination: a new `fleetos_api/` package alongside
  `legacy_fleettracker/` (so `starter/` contains both)
- the four layers and what belongs in each:
  - `main.py` - FastAPI app, `GET /vehicles` and
    `GET /vehicles/{id}/maintenance`, CORS enabled for `localhost:8000`
  - `maintenance.py` - pure functions only, no I/O, every function
    takes an explicit `today: date` parameter
  - `data_loader.py` - reads the legacy CSVs, returns typed models,
    no business logic
  - `models.py` - Pydantic models for `Vehicle`, `ServiceRecord` and
    the response shapes, with `VehicleClass` / `VehicleStatus` as Enums
- the parity constraint: new functions must produce identical results
  to `calc_next_service` / `calc_status` / `calc_priority` for every
  row in the CSVs
- port the characterisation tests across

<details>
<summary><strong>🤔 Stuck? Example prompt (click to expand)</strong></summary>

> Extract the maintenance logic from legacy_fleettracker/app.py into a new fleetos_api/ package alongside it (so starter/ contains both). Four layers: (1) main.py - FastAPI app with GET /vehicles and GET /vehicles/{id}/maintenance, CORS enabled for localhost:8000; (2) maintenance.py - pure functions only, no I/O, every function takes an explicit today: date parameter; (3) data_loader.py - reads the legacy CSVs and returns typed models, no business logic; (4) models.py - Pydantic models for Vehicle, ServiceRecord, and the response shapes, with VehicleClass and VehicleStatus as Enums. The new functions must produce identical results to calc_next_service / calc_status / calc_priority for every row in the CSVs. Port the characterisation tests across.

</details>
<br>

Review the plan Claude produces. Does each layer have exactly one job? Are
the rules in one place this time? Push back where you disagree. Once you're
happy with the plan, move on to Step 4.

## Step 4 - Execute the refactor (~30 min)

Approve the plan. Claude will typically build the whole package in one pass
and may spawn a **verification subagent** at the end to double-check its own
work - that's normal, just let it finish.

When it's done you should see a new `fleetos_api/` package containing:

- `models.py` - Pydantic models and the `VehicleClass` / `VehicleStatus` enums
- `data_loader.py` - reads the legacy CSVs, returns typed models
- `maintenance.py` - the pure functions, all legacy quirks preserved
- `main.py` - the FastAPI app with `GET /vehicles` and `GET /vehicles/{id}/maintenance`
- `tests/test_fleetos_api.py` - the ported characterisation tests

Claude should also have run `pytest` for you. A result like **36/36 passed**
(18 legacy + 18 ported) means the new code already produces identical
outputs - parity holds. If anything failed, send Claude the error and remind
it: fix the new code, never the test.

Now skim `fleetos_api/maintenance.py` yourself. Is the logic actually
equivalent, or has something been quietly "improved" along the way?

Once parity holds, add focused unit tests for the new module that nail
down the specific rules you uncovered in Step 1.

Your prompt should cover:

- the target file: `fleetos_api/tests/test_maintenance.py`
- the specific rules to pin down - at minimum: the EV
  12-month/40,000 km interval; the 14-day grace window boundary
  (day 14 vs day 15); the 220,000 km retirement threshold; the +10
  commercial priority bump; the priority cap at 100; and a vehicle
  with no service history
- a fixed `today` date for determinism
- run `pytest` and show the result

<details>
<summary><strong>🤔 Stuck? Example prompt (click to expand)</strong></summary>

> Add unit tests in fleetos_api/tests/test_maintenance.py for the new module that cover, at minimum: EV 12-month/40,000 km interval; the 14-day grace window boundary (day 14 vs day 15); the 220,000 km retirement threshold; the +10 commercial priority bump; the priority cap at 100; and a vehicle with no service history. Use a fixed today date. Run pytest and show me the result.

</details>
<br>

> 💡 You may see Pyright/IDE warnings about unresolved imports - there's no
> `pyproject.toml`, so the editor can't find the package, but `pytest`
> resolves it fine. Ignore them.

When you're green, start the API. Ask Claude to run it for you on port
8001 (it will background the process and surface the logs). Just say to Claude: 

> Start the server on port 8001.

Or run the server yourself in a new terminal session:

```bash
uvicorn fleetos_api.main:app --reload --port 8001
```

Visit <http://localhost:8001/docs> and try the endpoints. Compare
`/vehicles` against the legacy `/status` page - same statuses, same
priorities.

Two endpoints is right - you've modernised one slice, not the whole app.
`/report` stays behind for now (it has the drifted maths from Step 1), and
`/history` is a stretch task in Step 7.

## Step 5 - Wire up the dashboard (~15 min)

Serve the bundled dashboard on port 8000. Ask Claude to start it from
`../dashboard` (it will background the process and surface the logs). Just say to Claude:

> Start the dashboard on port 8000 from ../dashboard.

Or run it yourself in a new terminal session:

```bash
cd ../dashboard
python3 -m http.server 8000
```

The bundled dashboard already tries `http://localhost:8001/vehicles` first
and falls back to its static JSON if the API isn't running - so with your
API up on `:8001`, open <http://localhost:8000> and watch the badge in the
page header flip from **Static data** to **Live API**. The dashboard is now
live-backed by logic rescued from a 2015 Flask app.

> 💡 **Dashboard looks the same, or not showing Live API?** Try opening
> <http://localhost:8000> in an incognito window. If you came from Challenge 1
> your previous dashboard may be cached in the browser.

> 💡 **The numbers changed?** Good - that's the point. The static JSON's
> service dates were hand-authored; the live API *computes* them from
> `service_history.csv` using the rules you just extracted. The dashboard
> was showing stale guesses before. Now it isn't.

<details>
<summary><strong>Built your own Challenge 1 dashboard? Click here</strong></summary>

> 📝 The bundled dashboard has a built-in fallback to the live API, but your own build won't. You'll need to point it at the live API yourself.

You should prompt Claude to make this change for you. Your prompt should cover:

- the file to edit: `../dashboard/app.js`
- change `loadVehicles()` to fetch from
  `http://localhost:8001/vehicles` instead of the local JSON file
- the API's field names (`id`, `make`, `model`, `location`,
  `mileage_km`, `status`, `next_service_date`, `priority`) - map or
  rename anything the existing render code expects differently
- ask Claude to report back what changed

<details>
<summary><strong>🤔 Stuck? Example prompt (click to expand)</strong></summary>

> Open ../dashboard/app.js. Change loadVehicles() to fetch from http://localhost:8001/vehicles instead of the local JSON file. The API returns fields named id, make, model, location, mileage_km, status, next_service_date, priority - map or rename anything the existing render code expects differently. Then tell me what changed.

</details>

</details>

## Step 6 - Capture the pattern as a skill (~10 min)

The code is the output of *this* session. The thing you take to the *next*
legacy system is the pattern - so encode it as a Claude Code skill you can
invoke on any inherited codebase.

Your prompt should cover:

- the destination: `.claude/skills/legacy-modernise/SKILL.md`
- voice: imperative, second person - written as instructions *to* Claude
- frontmatter: `name "legacy-modernise"` and a `description` covering
  when to trigger it
- a strict-order methodology with the five phases you just walked
  through: Analyse → Characterise → Plan the four layers → Port and
  verify parity → Retire
- a length cap (under ~60 lines) so it stays scannable

<details>
<summary><strong>🤔 Stuck? Example prompt (click to expand)</strong></summary>

> Create a skill at .claude/skills/legacy-modernise/SKILL.md that captures the methodology we just used, written as instructions to Claude (imperative, second person). Frontmatter: name "legacy-modernise", description covering when to trigger it. Body: a strict-order methodology with these phases: (1) Analyse - map routes/functions/data, cross-examine docs against code, list dead code; (2) Characterise - write golden tests against the legacy functions with a fixed today date, record outputs as-is; (3) Plan the four layers - models / data_loader / pure service functions / FastAPI routes; (4) Port and verify parity - run old and new tests together, fix the new code never the test; (5) Retire - criteria for deleting the legacy path. Keep it under 60 lines.

</details>
<br>

Open the generated `SKILL.md` and read it. Tighten anything vague - this is
written for Claude to follow, so be specific about what "done" looks like at
each phase.

You now have a reusable skill for modernising legacy codebases. Copy it into any future project and run `/legacy-modernise` to execute the full methodology.

## Step 7 - Extend FleetOS API! (optional)

The API is yours now. Use Claude Code to take it further in whatever
direction interests you most. Here are some ideas to spark inspiration:

- **Reconcile `/report`** : the legacy route has its own drifted copy of the priority maths. Point it at your extracted function and diff the output finance's Excel macro relies on.
- **Service history endpoint** : add `GET /vehicles/{id}/history` and surface it in a dashboard detail modal.
- **Priority column** : add a Priority column to the dashboard table, colour-coded 0-100.
- **SQLite migration** : swap the CSV loader for SQLite and write a tiny one-off migration script.
- **Generated client** : generate a TypeScript client from the OpenAPI spec and use it in the dashboard instead of raw `fetch`.
- **Dockerise it** : package `fleetos_api` as a container with a healthcheck.
- **API auth** : add an API-key middleware and have the dashboard send it as a header.
- **Revive `/admin/recalc`** : the commented-out legacy route - implement it properly as a `POST` that returns a recompute summary.
- **Strangler-fig plan** : write an ADR mapping every remaining FleetTracker route to its FleetOS replacement, with a cut-over order.

Describe what you want to build in plain language and let Claude Code figure
out the implementation. The more specific your spec, the closer the first
attempt will land.

---

Ready to go further? **Head to Challenge 3** to configure Claude Code for a
team: connect the ops database via MCP, build parallel subagents with scoped
tools, enforce rules with hooks, and package the lot as a sharable plugin.
