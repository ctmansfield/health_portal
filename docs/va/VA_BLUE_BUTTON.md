# VA Blue Button → FHIR (labs + meds)

This tool parses your VA Blue Button .txt report and produces a FHIR R4 transaction Bundle with:
- Observation resources for lab/test results (keeps reference ranges as notes)
- MedicationStatement resources for medications (status mapped heuristically; SIG/reason/quantity as notes)

## Convert

    make va-import \
      VA_BB_TXT=/incoming/VA-Blue-Button-report-CHAD-MANSFIELD-9-7-2025_0112am.txt \
      VA_BB_OUT=/tmp/va_bb_to_fhir.json

## Post to your local HAPI

    make va-post \
      VA_BB_OUT=/tmp/va_bb_to_fhir.json \
      FHIR_BASE=http://localhost:8085/fhir

## Notes
- To bind to a specific patient, add: `--subject=Patient/<id>` to `va-import`.
- If you see HTML instead of JSON on post, verify HAPI is running on the port in FHIR_BASE.
