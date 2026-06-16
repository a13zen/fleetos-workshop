#!/usr/bin/env bash
# Local pre-push smoke test on code you trust. NOT a CI gate for untrusted PRs -
# see Challenge 3 README, Step 5, "Why this isn't your PR gate yet".
set -euo pipefail
claude -p "/fleet-audit" --permission-mode acceptEdits
grep -q "NO-GO" AUDIT.md && { echo "❌ Audit says NO-GO"; exit 1; }
echo "✅ Audit says GO"
