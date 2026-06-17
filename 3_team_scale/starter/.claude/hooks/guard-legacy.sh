#!/usr/bin/env bash
input=$(cat)
path=$(printf '%s\n' "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)
if [[ $? -ne 0 || -z "$path" ]]; then
  printf '%s\n' '{"decision":"block","reason":"Hook: failed to parse tool input — blocking as precaution."}'
  exit 0
fi
if [[ "$path" == *"legacy_fleettracker/"* ]]; then
  printf '%s\n' '{"decision":"block","reason":"legacy_fleettracker/ is frozen for audit - edits are blocked by team policy. Propose the change in fleetos_api/ instead."}'
  exit 0
fi
exit 0
