# FleetOS Workshop — repo guide

This is a four-challenge Claude Code workshop. **Don't work from this root
directory** — each challenge is self-contained and Claude Code should be
started inside that challenge's `starter/` folder.

## Layout

| Folder | Challenge | Start Claude in |
|---|---|---|
| `1_dashboard/` | Beginner — dashboard prototype | `1_dashboard/starter/` |
| `2_code_modernisation/` | Intermediate — legacy refactor | `2_code_modernisation/starter/` |
| `3_team_scale/` | Advanced — subagents, hooks, plugin | `3_team_scale/starter/` |
| `4_agents/` | Bonus — Agent SDK (needs API key) | `4_agents/starter/` |
| `solutions/` | Reference implementations | (read-only) |
| `assets/` | Shared icons | — |

See each challenge's `README.md` for step-by-step instructions.

## When exploring this repo

- **Ignore** `.venv/`, `__pycache__/`, `*.db`, `node_modules/` — they are
  build artefacts, not project files. Use `ls` or `git ls-files` rather
  than recursive glob.
- The root `README.md` has the full challenge table.
- Each `*/starter/` has its own `CLAUDE.md` once `/init` is run there.
