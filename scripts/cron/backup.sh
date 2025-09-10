#!/usr/bin/env bash
set -euo pipefail
OUTDIR=/mnt/nas_storage/backups/health
mkdir -p "$OUTDIR"
FN="$OUTDIR/health_$(date +%F).sql"
docker exec -t healthdb pg_dump -U health -d health > "$FN"
ls -1t "$OUTDIR"/health_*.sql | tail -n +15 | xargs -r rm -f
echo "$(date -Is) wrote $(basename "$FN")" >> "$OUTDIR/backup.log"
