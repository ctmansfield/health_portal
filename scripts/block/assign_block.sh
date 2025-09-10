#!/usr/bin/env bash
set -euo pipefail
ID="${1:-}"; ASSIGNEE="${2:-}"
test -n "$ID" && test -n "$ASSIGNEE" || { echo "usage: $0 <ID> <assignee>"; exit 2; }
python - <<PY
import yaml, sys, os
ID=os.environ['ID']; ASSIGNEE=os.environ['ASSIGNEE']
with open("blocks/registry.yaml","r",encoding="utf-8") as f: data=yaml.safe_load(f)
for b in data['blocks']:
    if b['id']==ID:
        b['assignee']=ASSIGNEE; break
with open("blocks/registry.yaml","w",encoding="utf-8") as f: yaml.safe_dump(data,f, sort_keys=False)
print("[assign] set assignee", ASSIGNEE, "for", ID)
PY
