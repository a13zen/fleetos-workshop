# Challenge 3 - Run FleetOS like a Team

FleetOS now has a working dashboard and a clean API. The next problem isn't
code - it's *scale*. Three more engineers are joining the FleetOS team next
sprint, and the way you've been driving Claude Code so far (one long chat,
everything in your head) won't survive a team of five.

Over the next ~1 hour you will turn your ad-hoc Claude Code setup into a
**shared, guarded, automated** one: govern Claude's permissions with a
project allowlist, define specialist subagents that run in parallel with
restricted tools, enforce team rules with hooks, bundle everything into a
**plugin** any teammate can install with one command, and run it headless
from a script.

## Folder layout

| Folder | Purpose |
| --- | --- |
| `starter/` | **Work here.** Contains a `.claude/` skeleton and a frozen `legacy_fleettracker/` you must *not* touch. |
| `fleetos_api/` | The FastAPI service from Challenge 2, extended with `/ops/*` endpoints for incident, fuel and depot data. **Don't edit this** - just run it. |
| `dashboard/` | The dashboard from Challenge 1. **Don't edit this** - serve it in Step 5. |

## Who this is for

This is the **advanced** track. **You do not need to have completed
Challenge 1 or 2** - working copies of the dashboard and API are bundled in
this folder, and `reset.sh` builds the database from scratch. You should be
comfortable with the basics of Claude Code (`CLAUDE.md`, `/plan`,
permissions) and happy editing JSON config and small shell scripts.

Everything in this challenge is **core Claude Code** - it works identically
whether you're on the Anthropic API, Amazon Bedrock, or Vertex. No
`ANTHROPIC_API_KEY` is required if your Claude Code is already configured
for Bedrock.

Run this challenge on **Sonnet**.

By the end you'll know how to govern what Claude can do with a
`settings.json` allowlist, how to build a roster of specialist subagents
with least-privilege tools and run them in parallel, how to make team rules
non-negotiable with hooks, how to bundle all of it into a **sharable
plugin** any teammate can install with one command, and how to call that
plugin from a script.

---

## Step 0 - Setup (~5 min)

You'll need [`uv`](https://docs.astral.sh/uv/) (or a plain venv).

```bash
cd starter
uv venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

Start the FleetOS API in its own terminal and leave it running:

```bash
uvicorn --app-dir .. fleetos_api.main:app --port 8001
```

> 📝 **Run this from inside `starter/`.** `--app-dir ..` points one level
> up to where `fleetos_api/` lives - from any other directory it will fail
> with `ModuleNotFoundError: No module named 'fleetos_api'`.

Open <http://localhost:8001/> - it redirects to interactive Swagger docs
showing six endpoints. (The API builds its own ops database on first
startup; run `./reset.sh` any time to clear generated artefacts.)

Now in a **second terminal**, from `starter/`:

```bash
claude
```

Run `/model` and select **Sonnet**. A `CLAUDE.md` is already provided -
skim it, especially the team rule about `legacy_fleettracker/`.

## Step 1 - Govern what Claude can do (~10 min)

The API exposes two kinds of data: maintenance forecasts (`/vehicles`,
`/vehicles/{id}/maintenance`) and operations (`/ops/incidents`,
`/ops/fuel_log`, `/ops/depot_capacity`). Ask Claude a question that needs
both:

> Which vehicles are flagged `overdue` on `:8001/vehicles` *and* have an
> open high-severity incident on `:8001/ops/incidents`? List vehicle ID,
> incident description, and days overdue.

Claude will reach for `Bash` to `curl` both endpoints. Approve it - and
notice that approval was for *all* of Bash, not just `curl`. On a five-
person team, "Claude can run any shell command anyone clicks yes to" is not
a policy. Write one.

Open `.claude/settings.json` (it ships as `{}`) and replace its contents:

<details>
<summary><strong>🤔 Stuck? The settings.json (click to expand)</strong></summary>

```json
{
  "permissions": {
    "defaultMode": "dontAsk",
    "allow": [
      "Bash(curl *localhost:8001*)",
      "Read", "Grep", "Glob", "Edit", "Write", "Task"
    ],
    "deny": ["WebFetch", "WebSearch"]
  }
}
```
</details>
<br>

`defaultMode: "dontAsk"` flips the default from *prompt* to *refuse*: any
tool call that doesn't match an `allow` rule is auto-denied without asking.
The `allow` list is your whole policy. (`deny` is for tools you want
removed from Claude's view *entirely* - here, web access we never need.)

Restart Claude Code, run `/permissions`, and confirm the rules are loaded.
Then test the boundary:

> Start a Python HTTP server on port 9000.

Claude reaches for `Bash(python3 -m http.server 9000)` and is **refused** -
it's not in the allowlist, and `dontAsk` mode auto-denies anything that
isn't. Now ask: *"Fetch `http://localhost:8001/vehicles` with curl."* That
matches the allow rule - Claude runs it and you see the raw JSON. The
policy let through exactly what you specified, and nothing else.

> 📝 **Why not test with `ls` or `python --version`?** Claude Code has a
> built-in set of commands it treats as read-only (`ls`, `cat`, `git log`,
> version checks, etc.) and runs without a prompt **in every mode** -
> `dontAsk` included. So a boundary test needs a command outside that set.
> Starting a server qualifies; checking a version doesn't. The full rule is
> in the [permissions reference](https://code.claude.com/docs/en/permissions#read-only-commands).

> 💡 **Allowlist beats denylist.** You can't enumerate every dangerous
> shell command, but you can enumerate the few you actually need. Note that
> a `deny` rule in Claude Code is **absolute** - it can't carry exceptions.
> `deny: ["Bash"]` plus `allow: ["Bash(curl ...)"]` doesn't mean "Bash off
> except curl"; it means "Bash off, full stop." `dontAsk` + `allow` is how
> you get an allowlist. See the
> [permissions reference](https://code.claude.com/docs/en/permissions) for
> the full rule syntax and precedence.

> ⚠️ **Bash command patterns are brittle.** `Bash(curl *localhost:8001*)`
> matches `curl -s http://localhost:8001/x` and plain
> `curl localhost:8001/x`, but a clever rephrasing
> (`URL=http://localhost:8001/x && curl $URL`) slips past. And it cuts
> both ways: a compound like `curl … | python3 -c …` is checked
> per-subcommand, so the `python3` half is refused even though the curl
> matches. Patterns shape behaviour; for a hard boundary you'd pair this
> with [sandboxing](https://code.claude.com/docs/en/sandboxing) or a
> hook - that's Step 3.

> 📝 **What about MCP?** The cleanest way to give Claude an external system
> isn't `curl` at all - it's an MCP server, configured once in
> `.mcp.json`, that exposes typed tools (e.g. `query_incidents`,
> `book_workshop_bay`). On a managed laptop that's typically a
> **platform-team responsibility**: they vet, host and version the server;
> you consume it. You won't configure one today, but here's what you'd ask
> them for:
>
> ```json
> { "mcpServers": { "fleet-ops": { "url": "https://mcp.internal/fleet-ops" } } }
> ```
>
> Once that exists, the `Bash(curl …)` allowlist entry above gets replaced
> by `mcp__fleet-ops__*` and Claude has real tools instead of shell.

## Step 2 - Build a roster of specialist subagents (~15 min)

You're about to run a pre-release audit of the FleetOS API. That's three
distinct jobs - data correctness, contract testing, security review - and
doing them serially in one chat would take ten minutes and blow through
context. Instead you'll define three **subagents**, each with its own
system prompt and *only the tools it needs*, and run them in parallel.

Create three files under `.claude/agents/`:

| File | Role | Tools it gets |
| --- | --- | --- |
| `db-auditor.md` | Cross-checks `/vehicles` forecasts against `/ops/*` incident & fuel data for inconsistencies | `Bash`, `Read` |
| `contract-tester.md` | Hits every endpoint on `:8001`, verifies status codes & JSON shape | `Bash`, `Read` |
| `security-reviewer.md` | Greps `fleetos_api/` for secrets, injection, missing auth | `Read`, `Grep`, `Glob` *only* |

Each file is Markdown with YAML frontmatter. Ask Claude to scaffold them,
or write the first one yourself to learn the shape:

<details>
<summary><strong>🤔 Stuck? Example agents/security-reviewer.md (click to expand)</strong></summary>

```markdown
---
name: security-reviewer
description: Reviews a Python service for hardcoded secrets, SQL/command injection, missing input validation and missing auth. Read-only - it can inspect code but never run or modify it.
tools: Read, Grep, Glob
---

You are a security reviewer for Python web services. You work read-only:
you may read and search files but never execute or edit anything.

When invoked, inspect the target directory for:
- hardcoded credentials, API keys, tokens
- SQL built by string concatenation / f-strings
- shell or `subprocess` calls with unsanitised input
- endpoints with no auth/authz check
- broad CORS or `debug=True` left on

Report each finding as: **file:line — severity — one sentence**. If you
find nothing in a category, say so explicitly. Do not suggest fixes.
```
</details>
<br>

Restart Claude Code (or run `/agents` to verify they're registered). Now
fire the audit:

> Run a pre-release audit of `../fleetos_api/`. Use the `db-auditor`,
> `contract-tester` and `security-reviewer` subagents **in parallel** and
> combine their findings into a single `AUDIT.md` with one section per
> agent and a traffic-light summary at the top.

Watch the three `Task(...)` calls launch together. When they return, open
`AUDIT.md`.

> 💡 **The lesson here is the `tools:` line.** `security-reviewer` *cannot*
> run `Bash` or call the database even if a malicious docstring in the code
> told it to - its blast radius is defined by config, not by prompt. This
> is the same least-privilege idea you'd apply to IAM roles, expressed in
> four words of frontmatter.

Run `/cost` and compare against what a single serial conversation would
have cost. The subagents each used a *fresh* context, so your main window
is still mostly empty - check `/context` to confirm.

## Step 3 - Make the rules non-negotiable with hooks (~10 min)

Your `CLAUDE.md` already says *"never edit `legacy_fleettracker/` - it's
frozen for audit."* But `CLAUDE.md` is a *request*. A **hook** is a
*guarantee*: a shell command Claude Code runs at a defined lifecycle point,
whose exit code can block the action entirely.

You'll add two hooks in `.claude/settings.json`:

1. **`PreToolUse` on `Edit|Write|MultiEdit`** - block any change to a path
   containing `legacy_fleettracker/`.
2. **`PostToolUse` on `Edit|Write`** - after any `.py` edit, run a syntax
   check and feed failures straight back to Claude.

<details>
<summary><strong>🤔 Stuck? settings.json + the guard script (click to expand)</strong></summary>

`.claude/settings.json`:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          { "type": "command", "command": ".claude/hooks/guard-legacy.sh" }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": ".claude/hooks/py-syntax.sh" }
        ]
      }
    ]
  }
}
```

`.claude/hooks/guard-legacy.sh` (make it executable):
```bash
#!/usr/bin/env bash
input=$(cat)
path=$(echo "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))")
if [[ "$path" == *"legacy_fleettracker/"* ]]; then
  echo '{"decision":"block","reason":"legacy_fleettracker/ is frozen for audit - edits are blocked by team policy. Propose the change in fleetos_api/ instead."}'
  exit 0
fi
exit 0
```

`.claude/hooks/py-syntax.sh`:
```bash
#!/usr/bin/env bash
input=$(cat)
path=$(echo "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))")
[[ "$path" == *.py ]] || exit 0
python3 -m py_compile "$path" 2>&1 || exit 2
```
</details>
<br>

Restart Claude Code, then test the guard:

> There's a typo in `legacy_fleettracker/app.py` line 12 - fix it.

Claude will attempt the edit, the hook will block it, and Claude will read
the reason and re-plan ("I'll apply this in `fleetos_api/` instead"). Then
test the syntax hook by asking for a deliberately broken edit to a `.py`
file in `fleetos_api/` and watch Claude self-correct from the hook output.

> 💡 **Hooks vs. CLAUDE.md:** put *preferences* in `CLAUDE.md` ("we like
> short functions"). Put *invariants* in hooks ("this directory is
> immutable"). The first steers; the second enforces.

> 💡 **This hook covers the file-editing tools.** A determined `sed -i` via
> Bash would slip past it - for production guardrails you'd also inspect
> Bash command strings, or use filesystem permissions that *no* tool can
> bypass. That's an Extend exercise; today the lesson is the mechanism.

## Step 4 - Package it as a sharable plugin (~12 min)

You've now built three things that live in `.claude/`: a permissions
allowlist, three subagents, and two hooks. They work - but only in *this*
checkout. The next engineer who joins gets none of it.

A **plugin** bundles the *logic* - subagents, hooks, *and* a skill that
drives them - into one directory with a manifest. A teammate runs one
install command and gets the whole FleetOS toolkit, in any repo.

> 📝 **Skills and slash commands are the same thing.** You made skills in
> Challenges 1 and 2 (`fleet-design-system`, `legacy-modernise`). Those were
> *passive* - style guides and checklists Claude reads when relevant. The
> skill you write here is *active*: typing `/fleet-audit` runs a workflow
> that orchestrates your subagents. Same file format, different job.

Create the plugin structure alongside `.claude/`. A plugin lives inside a
**marketplace** - a directory with a small manifest listing the plugins it
offers - so you'll create both:

```
fleetos-marketplace/
├── .claude-plugin/
│   └── marketplace.json
└── fleetos-toolkit/
    ├── .claude-plugin/
    │   └── plugin.json
    ├── agents/                       # auto-discovered, no manifest entry needed
    │   ├── db-auditor.md
    │   ├── contract-tester.md
    │   └── security-reviewer.md
    ├── hooks/
    │   ├── hooks.json
    │   ├── guard-legacy.sh
    │   └── py-syntax.sh
    └── skills/
        └── fleet-audit/
            └── SKILL.md
```

Ask Claude to assemble it - it should *move* the agents and hook scripts
you wrote in Steps 2-3 into the plugin (not copy, so there's one source of
truth), write the `/fleet-audit` skill, and generate the two manifests.

<details>
<summary><strong>🤔 Stuck? The manifests + the skill (click to expand)</strong></summary>

`.claude-plugin/marketplace.json` (at the marketplace root):
```json
{
  "name": "fleetos-workshop",
  "owner": { "name": "FleetOS Team" },
  "plugins": [
    { "name": "fleetos-toolkit", "source": "./fleetos-toolkit" }
  ]
}
```

`fleetos-toolkit/.claude-plugin/plugin.json`:
```json
{
  "name": "fleetos-toolkit",
  "version": "0.1.0",
  "description": "FleetOS team toolkit: audit subagents, legacy-freeze guardrails, and /fleet-audit.",
  "author": { "name": "FleetOS Team" },
  "skills": ["./skills/"],
  "hooks": "./hooks/hooks.json"
}
```

`fleetos-toolkit/hooks/hooks.json` (same shape as `.claude/settings.json` from Step 3, but with `${CLAUDE_PLUGIN_ROOT}` so the paths resolve wherever the plugin is installed):
```json
{
  "hooks": {
    "PreToolUse":  [{ "matcher": "Edit|Write|MultiEdit", "hooks": [{ "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/guard-legacy.sh" }] }],
    "PostToolUse": [{ "matcher": "Edit|Write",           "hooks": [{ "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/py-syntax.sh" }] }]
  }
}
```

`fleetos-toolkit/skills/fleet-audit/SKILL.md`:
```markdown
---
name: fleet-audit
description: Pre-release audit of a FleetOS service - data correctness, contract, security. Invoke as /fleet-audit [dir].
---

Run a pre-release audit of `$ARGUMENTS` (default `../fleetos_api`).

Launch the `db-auditor`, `contract-tester` and `security-reviewer`
subagents **in parallel**. Combine their findings into `AUDIT.md` with:

1. A traffic-light summary table (🟢/🟡/🔴 per category) at the top
2. One `##` section per subagent with its raw findings
3. A final `## Release decision` line: **GO** or **NO-GO** with one reason

If any 🔴 finding exists, the decision must be NO-GO.
```
</details>
<br>

Now **prove it's portable** - if your environment allows local plugin
sources. Exit Claude Code, delete the `.claude/agents/` and
`.claude/hooks/` you wrote in Steps 2-3 (the plugin is now the source),
then:

```bash
claude plugin marketplace add ./fleetos-marketplace
claude plugin install fleetos-toolkit@fleetos-workshop
claude
```

Run `/agents` - all three are listed. Type `/fleet-audit` - the full
parallel audit runs. The agents, hooks and skill arrived via one install
command. **That `fleetos-toolkit/` folder is what you hand to the next
engineer.**

> 📝 **Locked down?** If `marketplace add` is refused with a *"source not
> in the approved list"* message, your organisation has set
> `strictKnownMarketplaces` in managed settings - only the platform team's
> catalogue is permitted. **That's fine: the plugin folder is still your
> deliverable.** Skip the install and move to the next box. (Similarly, if
> Steps 2-3's project-level agents/hooks didn't load at all,
> `strictPluginOnlyCustomization` is in force - approved plugins are the
> *only* customisation surface, which makes the folder you just built the
> *only* artefact that matters.) See the
> [managed marketplace restrictions](https://code.claude.com/docs/en/plugin-marketplaces#managed-marketplace-restrictions).

> 📝 **Distribution is the platform team's job.** Whether or not you could
> install it locally, the production path is the same: open a PR against
> your platform team's marketplace repo with this folder. They review and
> publish it, and every laptop in the org gets it via `/plugin install
> fleetos-toolkit` - because that repo is pre-registered on every machine
> via managed settings. You don't create that repo; you contribute to it.
> The local `fleetos-marketplace/` you built is exactly the structure
> they'd host.

> 💡 **Try this:** run `claude plugin details fleetos-toolkit` from a plain
> terminal. You'll see the component inventory and the projected token cost
> the plugin adds to every session - useful when deciding what to ship to
> the whole team.

## Step 5 - Run it headless (~8 min)

The last step takes Claude Code out of the chat entirely. **Headless mode**
(`claude -p`) runs a single prompt non-interactively and prints the result -
which means everything you just did is now scriptable.

From a plain terminal in `starter/` (not inside Claude Code):

```bash
claude -p "/fleet-audit" --permission-mode acceptEdits
cat AUDIT.md
```

The same parallel-subagent audit you ran interactively just produced
`AUDIT.md` from a one-line shell command. Try it again with
`--output-format stream-json` and watch the structured events scroll past -
every tool call, subagent spawn, and hook block you saw in the chat is
available as JSON for your own dashboards.

Now close the loop. Ask Claude (interactively or with another `claude -p`)
to also emit a machine-readable summary:

> Read `AUDIT.md` and write `../dashboard/audit.json` - an array of
> `{category, light, summary}` rows, one per audit section.

Serve the dashboard in a new terminal:

```bash
cd ../dashboard && python3 -m http.server 8000
```

Open <http://localhost:8000>. The fleet table is live from the API on
`:8001`, and the **API Health** card is populated from the audit your
plugin produced. All three layers of the system are now visible on one
page - take a screenshot.

Finally, turn it into a one-line check you could run before every push:

```bash
cat > release-check.sh <<'EOF'
#!/usr/bin/env bash
claude -p "/fleet-audit" --permission-mode acceptEdits
grep -q "NO-GO" AUDIT.md && { echo "❌ Audit says NO-GO"; exit 1; }
echo "✅ Audit says GO"
EOF
chmod +x release-check.sh
./release-check.sh; echo "exit code: $?"
```

That script is a **local pre-push smoke test on code you trust**. Which
brings us to the last lesson:

> ⚠️ **Why this isn't your PR gate yet.** Running `claude -p` against an
> *untrusted* pull request is a different threat model entirely. The PR
> author controls the code under audit, the API responses, and - if you're
> not careful - the skill that does the judging. A safe gate needs the
> plugin pinned to a protected ref, the data source pinned too, every tool
> path-scoped, an ephemeral runner with no secrets, and exit-code-only
> egress. That's a platform-team design exercise, not a workshop step - see
> the [headless mode security guidance](https://docs.claude.com/en/docs/claude-code/headless)
> and the Extend section below.

## Step 6 - Extend! (optional)

- **Harden the legacy-freeze hook** : extend `guard-legacy.sh` to also
  match the `Bash` tool and inspect the command string for
  `legacy_fleettracker/` - or skip the tool layer entirely and `chmod -R
  a-w` the directory.
- **Model arbitrage** : add `model: haiku` to the `contract-tester`
  frontmatter (it's mechanical work) and re-run `/cost` - did the audit
  get cheaper without getting worse?
- **Audit log hook** : a `PreToolUse` matcher on `Bash` that appends every
  `curl` command + timestamp to `api-audit.log` - production agents need
  observability.
- **Stop hook → notify** : add a `Stop` hook to the plugin that posts the
  GO/NO-GO line to a webhook (or `osascript -e 'display notification ...'`
  on macOS).
- **Plugin versioning** : bump `plugin.json` to `0.2.0`, add a
  `CHANGELOG.md`, and treat the toolkit like any other dependency.

---

You've now taken Claude Code from "a chat that edits files" to a
**configured platform**: project permissions governed by `settings.json`,
specialist subagents with scoped tools, hard guardrails via hooks, and the
whole thing bundled as a plugin any teammate installs with one command and
any script runs with one line. That folder is what you hand to the next
four engineers.

Want to go further still? **Head to Challenge 4** (optional - requires a
direct Anthropic API key) to build standalone agents with the Claude Agent
SDK in Python.
