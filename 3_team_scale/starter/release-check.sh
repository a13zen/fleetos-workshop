#!/usr/bin/env bash
claude -p "/fleet-audit" --permission-mode default
if [[ ! -f AUDIT.md ]]; then
  echo "Audit says NO-GO: AUDIT.md was not generated"
  exit 1
fi
grep -q "NO-GO" AUDIT.md && { echo "Audit says NO-GO"; exit 1; }
echo "Audit says GO"
