#!/usr/bin/env bash
set -euo pipefail
# NO-EXTERNAL-DEPS: close block by id; set status=done; move to done/
ID="${1:-}"; MSG="${2:-}"
test -n "$ID" || { echo "usage: $0 <ID> \"commit message\""; exit 2; }
PYBIN="$(command -v python3 || command -v python || true)"
if [ -z "$PYBIN" ]; then echo "[error] python not found"; exit 2; fi
if [ -f "./VERIFY_ALL.sh" ]; then
  echo "[verify] running VERIFY_ALL.sh (if present)"
  bash ./VERIFY_ALL.sh || { echo "[warn] VERIFY_ALL failed; continue? [y/N]"; read -r a; [[ "$a" =~ ^[Yy]$ ]] || exit 1; }
fi
$PYBIN - "$ID" <<'PY'
import sys, os, re, datetime, shutil, pathlib
ID=sys.argv[1]; reg=pathlib.Path("blocks/registry.yaml")
if not reg.exists(): print("[fail] registry missing"); sys.exit(2)
text=reg.read_text(encoding="utf-8")
m=re.search(r"(?ms)^[ \t]*-[ \t]+id:[ \t]*"+re.escape(ID)+r"[^\n]*\n(.*?)(?=^[ \t]*-[ \t]+id:|\Z)",text)
if not m: print(f"[fail] unknown {ID}"); sys.exit(2)
seg=m.group(0)
ts=datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00","Z")
seg_new=re.sub(r"(^[ \t]*status:[ \t]*).*$", r"\1done", seg, count=1, flags=re.M)
if re.search(r"^[ \t]*closed_at:", seg_new, re.M):
    seg_new=re.sub(r"(^[ \t]*closed_at:[ \t]*).*$", rf"\1{ts}", seg_new, count=1, flags=re.M)
else:
    seg_new=re.sub(r"(^[ \t]*status:.*$)", rf"\1\n    closed_at: {ts}", seg_new, count=1, flags=re.M)
start,end=m.span(); reg.write_text(text[:start]+seg_new+text[end:], encoding="utf-8")
src=pathlib.Path(f"blocks/active/{ID}"); dst=pathlib.Path(f"blocks/done/{ID}"); dst.mkdir(parents=True, exist_ok=True)
if src.exists():
    for fn in src.iterdir():
        if fn.is_file(): shutil.copy2(fn, dst/fn.name)
    shutil.rmtree(src, ignore_errors=True)
print(f"[close] blocks/done/{ID}")
PY
if command -v git >/dev/null 2>&1; then
  git add -A || true
  [ -z "$MSG" ] && MSG="chore(block): close ${ID}"
  git commit -m "$MSG" >/dev/null 2>&1 || true
fi
