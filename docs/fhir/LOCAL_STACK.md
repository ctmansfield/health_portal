# Local HAPI FHIR + Postgres

## Start the stack
```bash
make up-hapi
# or:
# docker compose -f ops/hapi_fhir/docker-compose.yml --env-file ops/hapi_fhir/.env up -d
```

Wait until both containers are healthy, then:

## Quick smoke
```bash
curl -fsS http://localhost:8080/fhir/metadata | head -n 20
```

## Create a Patient
```bash
curl -sS -X POST "http://localhost:8080/fhir/Patient"   -H "Content-Type: application/fhir+json"   -d @ops/hapi_fhir/samples/patient.json | jq .
```

## Search Patients
```bash
curl -sS "http://localhost:8080/fhir/Patient?_count=5" | jq '.entry[].resource.name'
```

## Create an Observation (e.g., BMI)
```bash
curl -sS -X POST "http://localhost:8080/fhir/Observation"   -H "Content-Type: application/fhir+json"   -d @ops/hapi_fhir/samples/observation-bmi.json | jq .
```

## Create a MedicationRequest
```bash
curl -sS -X POST "http://localhost:8080/fhir/MedicationRequest"   -H "Content-Type: application/fhir+json"   -d @ops/hapi_fhir/samples/medicationrequest.json | jq .
```

## Submit a Bundle
```bash
curl -sS -X POST "http://localhost:8080/fhir"   -H "Content-Type: application/fhir+json"   -d @ops/hapi_fhir/samples/bundle.json | jq .
```

## Common issues
- Port 8080 already in use → change mapping in compose file.
- Local Postgres running on 5432 → we map DB to 55432 to avoid conflicts.
- `connection refused` → check `docker compose logs -f`.
