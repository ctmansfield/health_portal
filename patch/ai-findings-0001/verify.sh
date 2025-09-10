set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
services/healthdb-pg-0001/scripts/psql.sh -c "\i services/healthdb-pg-0001/init/030_ai_findings.sql" >/dev/null
. .venv/bin/activate || true
python jobs/ai_daily_scan.py --dsn "${HP_DSN:-postgresql://health:health_pw@localhost:55432/health}" || true
services/healthdb-pg-0001/scripts/psql.sh -c "SELECT metric,level,round(score,2) AS score,finding_time FROM analytics.ai_findings ORDER BY finding_time DESC LIMIT 5;"
