# HOWTO — Import FHIR
export PG_DSN="host=localhost port=5432 dbname=health_portal user=postgres"
python3 app/hp_etl/fhir_import.py /path/to/bundle.json PERSON123
psql "$PG_DSN" -c "SELECT analytics.refresh_critical_labs();"
