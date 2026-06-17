#!/usr/bin/env bash
input=$(cat)
path=$(echo "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))")
[[ "$path" == *.py ]] || exit 0
python3 -m py_compile "$path" 2>&1 || exit 2
