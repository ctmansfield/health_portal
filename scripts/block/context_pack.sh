#!/usr/bin/env bash
set -euo pipefail
ID="${1:-}"; OUT="${2:-blocks/active/${1}/CONTEXT.md}"
test -n "$ID" || { echo "usage: $0 <ID> [output-file]"; exit 2; }
python - <<'PY'
import yaml, sys, os, datetime
ID=os.environ['ID']; OUT=os.environ['OUT']
with open("blocks/registry.yaml","r",encoding="utf-8") as f: data=yaml.safe_load(f)
blk=None
for b in data.get('blocks',[]):
    if b.get('id')==ID: blk=b; break
docs=(blk or {}).get('context',{}).get('docs',[])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT,"w",encoding="utf-8") as out:
    out.write(f"# Context Pack for {ID}\nGenerated: {datetime.datetime.utcnow().isoformat()}Z\n\n")
    for d in docs: out.write(f"- {d}\n")
print("[context] wrote", OUT)
PY
