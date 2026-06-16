# Challenge 1 - Prototype the FleetOS Dashboard

You have inherited an early prototype of the FleetOS vehicle dashboard: a
single HTML page that loads a JSON list of fleet vehicles and renders them in
a table. It currently only partly works.

Over the next 1-2 hours you will explore the codebase with Claude Code, find and
fix what's broken, add a small feature, plan a larger feature, restyle the page to
your taste, and package those design decisions into a reusable and shareable skill.
You are then free to extend the dashboard as you wish!

## Folder layout

| Folder | Purpose |
| --- | --- |
| `starter/` | **Work here.** This is your copy of the codebase. All steps below assume you are inside this folder. |

## Who this is for

This is the **beginner** track. It suits anyone with basic exposure to HTML, CSS, and JavaScript. 
You don't need to be fluent, since Claude will write most of the code, but you should be able to
read a diff and tell whether it does what you asked. You'll need Claude Code installed and authenticated.

Run this challenge using **Sonnet**. It's more than capable for a codebase
this size and keeps the `/context` and `/cost` lessons meaningful.

By the end you'll know the core Claude Code workflow (`/init`, `/context`,
`/cost`, `/plan`), how to steer an agent on a small codebase by describing
symptoms and specifying features precisely, and how to capture your
preferences as a reusable skill that carries across projects.

---

## Step 0 - Setup (~5 min)

Make sure you are inside the 1_dashboard/ folder before commencing. Then run the following commands

```bash
cd starter/ # Enter the start folder
claude # Start up Claude Code
```

Inside Claude Code:

1. Run `/model` and select **Sonnet**.
2. Run `/init`. Claude will scan the project and generate a `CLAUDE.md` file
   summarising what it found. If prompted for a location, choose
   **Project-level** so it lands here in `starter/`, not at the repo root. For now do not setup skills or hooks, only CLAUDE.md.
   Claude may ask you some questions while this runs, answer these as you'd like.

   > 📝 **Note:** There is already a base `CLAUDE.md` in the `1_dashboard/` folder. **Do not change it.** It exists purely to stop Claude from spotting (and spoiling) the planted bugs while `/init` scans the code - Claude is very smart! Leave that file as-is and let `/init` create an update one.

3. Open the generated `CLAUDE.md` and read over it. This is the project memory
   Claude will carry into every future turn.

   > 💡 **Ask yourself:** Is there anything here you could remove from the CLAUDE.md which Claude would already know? Remeber Claude Code loads the whole file as context.
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

## Step 1 - Explore the codebase (~10 min)

Ask Claude Code:

> Explain this codebase to me. What does it do, and how is it structured?

Then run:

- `/context` - how much of the context window is in use, and what's filling it.
- `/cost` - what this session has cost so far.

What other questions could you ask Claude here about the codebase? Try a few others out, e.g.:

- *"Where does the vehicle data come from, and what fields does each record have?"*
- *"Walk me through what happens from page load to the table being rendered."*
- *"If I wanted to add a new column to the table, which files would I need to touch?"*

> 💡 **Try this:** Switch to **Opus** or **Haiku** (via `/model`) for one of the questions above. What difference do you notice in the response quality and speed? **Make sure you switch back to Sonnet once you're done.**

## Step 2 - Find the bugs (~15 min)

Open the dashboard in a browser. Because `app.js` uses `fetch()`, you will
need to serve it over HTTP rather than opening the file directly.

Ask Claude to start the server on port 8000, then visit **http://localhost:8000** in your browser. Just say to Claude:

> Start the server on port 8000.

Alternatively, you can run it manually in a new terminal session (make sure you are in `1_dashboard/starter` before running):
```bash
python3 -m http.server 8000
# then visit http://localhost:8000
```

There are **three bugs** in the page - all visual or data-display issues that
a fleet manager would notice. Don't tell Claude what they are. Instead,
describe what looks wrong on screen and ask it to help you investigate.

Fix them one at a time. After each fix, reload the page and confirm the
behaviour is correct before moving on.

> 💡 **Tip:** Try pasting screenshots directly into Sonnet as it's multimodal! Screenshots are a great way to iterate with Claude on UIs.

<details>
<summary><strong>🤔 Stuck? Hints (click to expand)</strong></summary>

- One bug is about **colour** - look at the status lozenges.
  <details>
  <summary><em>Still stuck?</em></summary>

  Try this prompt:
  > Explore the code for a bug regarding the colour of the status lozenges. Once found, confirm with me to fix it.
  </details>

- One bug is about **layout** - look at the Location column.
  <details>
  <summary><em>Still stuck?</em></summary>

  Try this prompt:
  > There's a bug in the table where the Location column clips text so it's invisible. Find it and fix it so the full text is readable - either by wrapping within the cell or showing an ellipsis, without overflowing into adjacent columns.
  </details>

- One bug is about **data** - compare the column headers to the values beneath them.
  <details>
  <summary><em>Still stuck?</em></summary>

  Try this prompt:
  > Analyse the table for consistent column data and headers. If you find any inconsistency report back and confirm with me to fix it.
  </details>

</details>

## Step 3 - Add a steered feature (~10 min)

Add a **Maintenance Due Soon** widget that highlights vehicles whose
`next_service_date` falls within the next 30 days.

Give Claude a clear spec: where the widget should sit on the page, what it
should show for each vehicle, and how it should be styled relative to the rest
of the dashboard. The more precise your spec, the closer the first attempt
will land.

This widget foreshadows Challenge 2, where you will extract real maintenance
scheduling logic from a legacy application.

<details>
<summary><strong>🤔 Stuck? Example spec (click to expand)</strong></summary>

> Add a "Maintenance Due Soon" panel that sits between the summary stats and the vehicle table. It should list every vehicle whose `next_service_date` is within the next 30 days. For each vehicle show the ID, make/model, and the number of days until service is due. Style it as a card that matches the existing summary stat boxes, but give it an amber/warning accent border so it draws the eye. If no vehicles are due, show "No upcoming maintenance" instead of an empty panel.

</details>
<br>

Once it's on the page, iterate on the design with Claude. Paste a screenshot of the result back in and say what you'd change - this tight feedback loop is the fastest way to refine UI. Try things like *"sort by soonest first"*, *"make overdue ones red"*, or *"show the date as well as days remaining"*. Don't like the result? Just tell Claude to undo it or try a different approach.

## Step 4 - Plan a bigger feature (~10 min)

Pick one:

- A **filter bar** to narrow the table by status or location.
- A **vehicle detail modal** that opens when you click a row.
- A **map placeholder** showing where vehicles are.

Before any code is written, run `/plan` (or press **Shift+Tab** to toggle into plan mode) and describe the feature. Claude will
explore the code, ask clarifying questions, and produce an implementation
plan. Review it, push back where you disagree, then approve and execute.

<details>
<summary><strong>🤔 Stuck? Example spec for the filter bar (click to expand)</strong></summary>

> Add a filter bar that sits directly above the vehicle table. It should contain a status dropdown (All / Active / Maintenance / Overdue) and a free-text location input. Filtering should happen instantly on the client side as the user types or changes the dropdown, with no page reload. The table should update in place, and the summary stat counts should stay reflecting the full fleet (not the filtered subset). Include a "Clear filters" button that resets both controls. Style the bar to match the existing card components so it feels native to the dashboard.

</details>
<br>

If you're up for it, go back and add another - or all three.

## Step 5 - Make the design your own (~10 min)

The starter styling is deliberately plain. Have a conversation with Claude
about what FleetOS should feel like - colour palette, typography, spacing,
visual hierarchy. Industrial? Friendly? High-contrast for in-cab use?

Apply the changes and iterate until you like the result.

<details>
<summary><strong>🤔 Stuck? Example prompts (click to expand)</strong></summary>

**First prompt:**
> Restyle the dashboard with a modern, industrial fleet-ops aesthetic. Use a dark slate background with high-contrast white text so it's readable on a workshop monitor. Pick a single bold accent colour (electric blue or safety orange) for primary actions and active states. Status pills should use traffic-light colours (green/amber/red). Increase spacing between cards and table rows so it doesn't feel cramped, and use a clean sans-serif font throughout. Keep the layout structure as it is, only change the visual styling.

**Follow-up iteration:**
> That's close. Make the accent colour slightly less saturated so it's easier on the eyes, add a subtle 1px border to the cards instead of heavy shadows, and bump the table row height up a little so each row is easier to scan.

</details>

## Step 6 - Package your design as a skill (~10 min)

Claude Code **skills** are reusable instruction files that travel with you
across projects. Ask Claude to help you turn the design decisions from Step 5
into a skill saved in the `.claude/` folder inside `starter/`:

```
.claude/skills/fleet-design-system/SKILL.md
```

Capture *principles* - "primary actions use the accent colour; data tables use
14 px tabular figures; status is always shown as a pill" - rather than just a
list of hex codes. The skill should be able to re-style any future FleetOS
surface consistently.

<details>
<summary><strong>🤔 Stuck? Example prompt (click to expand)</strong></summary>

> Look at the styling we just applied in `styles.css` and turn it into a reusable Claude Code skill. Save it to `.claude/skills/fleet-design-system/SKILL.md` here in the starter/ directory. The skill should capture the design *principles* rather than raw CSS: the colour palette and what each colour means, typography rules, spacing scale, how status is displayed (pills with traffic-light colours), and card/table styling conventions. Write it so that a future Claude session could apply this same look to a brand new FleetOS page without ever seeing this stylesheet.

</details>

## Step 7 - Extend FleetOS! (optional - spend as much time here as you like!)

The dashboard is yours now. Use Claude Code to take it further in whatever direction interests you most. Here are some ideas to spark inspiration:

- **Driver leaderboard** : rank drivers by mileage or service compliance; add a podium-style widget above the table.
- **Live clock + shift indicator** : show the current time and whether the depot is in day, evening, or night shift based on the hour.
- **Exportable CSV report** : add a "Download CSV" button that serialises the currently filtered table rows into a file the user can save.
- **Vehicle health score** : compute a 0–100 score per vehicle from mileage, days overdue, and status, and display it as a colour-coded bar in the table.
- **Animated stat counters** : make the summary numbers count up from zero on page load for a more polished first impression.
- **Dark/light mode toggle** : add a toggle button that switches between the current dark theme and a light variant, persisted in `localStorage`.
- **Keyboard navigation** : let users arrow-key through table rows and press Enter to expand a vehicle detail panel inline.
- **Simulated real-time updates** : poll `vehicles.json` every 30 seconds and highlight rows that have changed status since the last fetch.
- **Print-friendly view** : add a `@media print` stylesheet that strips the chrome and formats the table for A4 paper.
- **Localisation** : add a language switcher that translates all labels into German (or another language), keeping data values unchanged.

Describe what you want to build in plain language and let Claude Code figure out the implementation. The more specific your spec, the closer the first attempt will land.

---

Ready to go further? **Head to Challenge 2** to modernise the FleetOS backend : you'll extract a maintenance scheduling algorithm from a legacy Python script, wrap it in a proper REST API, and wire the FleetOS dashboard up to live data.
