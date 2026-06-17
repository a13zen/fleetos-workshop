#!/usr/bin/env bash
input=$(cat)
path=$(printf '%s\n' "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)
if [[ $? -ne 0 || -z "$path" ]]; then
  echo '{"decision":"block","reason":"Hook: failed to parse tool input — blocking as precaution."}'
  exit 0
fi
[[ "$path" == *.py ]] || exit 0
python3 -m py_compile "$path" 2>&1 || exit 2
