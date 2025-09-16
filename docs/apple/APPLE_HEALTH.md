# Apple Health → FHIR vitals

This stage converts Apple Health `export.xml` into a FHIR R4 **transaction Bundle** of `Observation` resources.

## Supported mappings

| HealthKit Type | LOINC | UCUM | Note |
|---|---|---|---|
| HeartRate | 8867-4 | {beats}/min | valueQuantity |
| RestingHeartRate | 40443-4 | {beats}/min | valueQuantity |
| RespiratoryRate | 9279-1 | {breaths}/min | valueQuantity |
| OxygenSaturation | 59408-5 | % | valueQuantity |
| BodyTemperature | 8310-5 | Cel | valueQuantity |
| BodyMassIndex | 39156-5 | kg/m2 | valueQuantity |
| BodyMass | 29463-7 | kg | valueQuantity |
| Height | 8302-2 | m | converts cm→m |
| BloodGlucose | 2339-0 | mg/dL | valueQuantity |
| BloodPressure | 85354-9 | mm[Hg] | combined to components 8480-6/8462-4 |
| StepCount | 41950-7 | 1 | valueInteger |

## Convert

```bash
# Convert Apple export.xml to FHIR Bundle JSON
/repos/health_portal/ops/apple_health/convert.sh ~/Downloads/apple_health/export.xml /tmp/apple_to_fhir.json --subject=Patient/example
```

## Load into local HAPI

```bash
# Post the transaction bundle into HAPI (from the previous patch)
curl -sS -X POST "http://localhost:8080/fhir"   -H "Content-Type: application/fhir+json"   --data-binary @/tmp/apple_to_fhir.json | jq .
```

## Validate with HAPI

```bash
# HAPI $validate on the bundle (optional)
curl -sS -X POST "http://localhost:8080/fhir/$validate"   -H "Content-Type: application/fhir+json"   --data-binary @/tmp/apple_to_fhir.json | jq .issue[]
```

## Notes
- Parser is deterministic and skips unsupported types (reports counts on stdout).
- Subject reference defaults to `Patient/example`; pass `--subject=Patient/{id}` to bind.
- Apple export timestamps are preserved as `effectiveDateTime`.
