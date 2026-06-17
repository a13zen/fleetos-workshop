#!/usr/bin/env bash
claude -p "/fleet-audit" --permission-mode acceptEdits
grep -q "NO-GO" AUDIT.md && { echo "Audit says NO-GO"; exit 1; }
echo "Audit says GO"
