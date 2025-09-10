#!/usr/bin/env bash
set -euo pipefail
REG="blocks/registry.yaml"
python - <<'PY'
import yaml, sys
from operator import itemgetter
with open("blocks/registry.yaml","r",encoding="utf-8") as f:
    data = yaml.safe_load(f)
for b in sorted(data['blocks'], key=lambda x: x.get('weight', 9999)):
    print(f"{b['id']:>6}  [{b['status']}]  {b['component']:>3}  w={b.get('weight')}  deps={','.join(b.get('deps',[]))}  - {b['title']}")
PY
