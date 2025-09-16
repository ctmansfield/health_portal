#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://localhost:8080/fhir}"

echo "Seeding Patient..."
curl -sS -X POST "$BASE/Patient" -H "Content-Type: application/fhir+json" -d @ops/hapi_fhir/samples/patient.json | jq -r '.id' || true

echo "Seeding Observation (BMI)..."
curl -sS -X POST "$BASE/Observation" -H "Content-Type: application/fhir+json" -d @ops/hapi_fhir/samples/observation-bmi.json | jq -r '.id' || true

echo "Seeding MedicationRequest..."
curl -sS -X POST "$BASE/MedicationRequest" -H "Content-Type: application/fhir+json" -d @ops/hapi_fhir/samples/medicationrequest.json | jq -r '.id' || true

echo "Done."
