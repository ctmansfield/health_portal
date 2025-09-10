#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import yaml, sys
from operator import itemgetter
try:
  with open("blocks/registry.yaml","r",encoding="utf-8") as f:
      data = yaml.safe_load(f) or {}
except Exception:
  print("blocks/registry.yaml missing or unreadable"); sys.exit(0)
for b in sorted(data.get('blocks',[]), key=lambda x: x.get('weight', 9999)):
    deps=",".join(b.get('deps',[]))
    print(f"{b['id']:>6}  [{b.get('status','todo')}]  {b.get('component','?'):>3}  w={b.get('weight')}  deps={deps}  - {b.get('title','')}")
PY
