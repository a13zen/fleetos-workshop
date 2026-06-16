#!/usr/bin/env bash
# PreToolUse hook: block any Edit/Write to legacy_fleettracker/.
input=$(cat)
path=$(echo "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))")
if [[ "$path" == *"legacy_fleettracker/"* ]]; then
  echo '{"decision":"block","reason":"legacy_fleettracker/ is frozen for audit - edits are blocked by team policy. Propose the change in fleetos_api/ instead."}'
  exit 0
fi
exit 0
