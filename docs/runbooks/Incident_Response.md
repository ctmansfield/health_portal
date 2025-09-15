# Runbook — Incident Response

1) Triage
- Declare severity (SEV1–SEV4)
- Page on-call; form incident channel

2) Stabilize
- Mitigate immediate impact (scale out, feature flag, revert)
- Capture key logs/metrics; snapshot relevant dashboards

3) Diagnose
- Identify regression window; correlate deploys/changes
- Formulate hypothesis; test in staging if possible

4) Resolve
- Implement fix; verify via runbook checks; communicate status

5) Postmortem
- Timeline, root cause, contributing factors
- Action items with owners and due dates
- Preventive measures (tests, alerts, runbooks)
