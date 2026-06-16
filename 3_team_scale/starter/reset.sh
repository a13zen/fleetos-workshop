#!/usr/bin/env bash
# Reset Challenge 3 working state.
# The ops database is rebuilt automatically by fleetos_api on startup,
# so we just delete it here along with generated artefacts.
set -euo pipefail
cd "$(dirname "$0")"

rm -f ../fleetos_api/data/fleet_ops.db
rm -f AUDIT.md ../dashboard/audit.json
rm -rf __pycache__ fleetos-toolkit/
find .claude -name "*.md" -path "*/agents/*" -delete 2>/dev/null || true
find .claude -name "*.sh" -path "*/hooks/*" -delete 2>/dev/null || true

echo "✓ Reset complete. Restart the API to rebuild fleet_ops.db."
