#!/usr/bin/env bash
set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "[error] GitHub CLI (gh) not found. Install from https://cli.github.com/"
  exit 1
fi

if [[ -z "${GH_REPO:-}" ]]; then
  echo "[error] Set GH_REPO (e.g., export GH_REPO=ctmansfield/health_portal)"
  exit 1
fi

YAML_FILE="${1:-issues/parallel_plan.issues.yaml}"
test -f "$YAML_FILE" || (echo "[error] YAML file not found: $YAML_FILE" && exit 1)

labels=$(awk '/^labels:/{flag=1;next}/^$|^issues:/{flag=0}flag' "$YAML_FILE" | sed 's/^- //g' | tr '\n' ',' | sed 's/,$//')
echo "[info] Repo: $GH_REPO"
echo "[info] Default labels: $labels"

IFS=',' read -r -a arr <<< "$labels"
for lb in "${arr[@]}"; do
  [[ -n "$lb" ]] && gh label create "$lb" --repo "$GH_REPO" --force >/dev/null || true
done

awk 'BEGIN{RS="^- title:"; FS="\n"} NR>1{title=$1; body=""; labels=""
  for(i=2;i<=NF;i++){
    line=$i
    if(line ~ /^    body:/){mode="body"; next}
    if(line ~ /^    labels:/){mode="labels"; next}
    if(mode=="body"){
      sub(/^ {6}/,"",line); body=body line "\n"
    } else if(mode=="labels"){
      if(match(line,/- (.*)/,m)){labels=labels m[1]","}
    }
  }
  gsub(/"|"|^ +/,"",title);
  gsub(/,$/,"",labels);
  print title "|" body "|" labels
}' "$YAML_FILE" | while IFS="|" read -r title body ilabels; do
  echo "[create] $title"
  gh issue create --repo "$GH_REPO" --title "$title" --body "$body" ${ilabels:+--label "$ilabels"} >/dev/null
done

echo "[done] Issues created."
