# Runbook — Report Reissue Workflow

1) Open reissue request with reason.
2) Amend payload; recompute hash; increment `signOut.version`.
3) Preserve prior version in history; notify consumers via webhook/event.
4) Update PDF and patient-mode outputs; archive prior PDFs.
