# Export FHIR → CSV (labs & medications)

## Usage
```bash
make fhir-export \
  FHIR_BASE=http://localhost:8085/fhir \
  FHIR_SUBJECT=Patient/example \
  LABS_CSV=/tmp/labs.csv \
  MEDS_CSV=/tmp/meds.csv
