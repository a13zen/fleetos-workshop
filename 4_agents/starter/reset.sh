#!/usr/bin/env bash
# Restore the starter to a clean state: rebuild the ops DB and remove
# anything the agents generated.
set -euo pipefail
cd "$(dirname "$0")"

rm -f data/fleet_ops.db
sqlite3 data/fleet_ops.db < data/schema.sql
echo "✔ rebuilt data/fleet_ops.db"

rm -f MONDAY_BRIEFING.md OPS_PLAN.md briefing.json emails/*.md
rm -rf __pycache__ */__pycache__
echo "✔ removed generated artifacts"
