# Context reader changes

## 1.0.0 — 2026-11-15

Adopt context-v1 ordered intake with a local reader, project initialization,
source-bound capsule registration, and an optional trusted SessionStart reminder.
This project's identity and empty index are initialized; task state is UNSEEDED.
Synthetic examples and offline tests are kept separate from operational context.
The repository workflow checks the reader suite. Verify actual hook callback
delivery on each supported Codex installation before claiming automatic intake.

### Health Portal CI compatibility

The six added reader/tool test files pass Black 26.10.1 (88 columns) and
Ruff 0.17.5 with its current default rules. Python commands invoke the tools
explicitly, so the non-executable files have no shebangs. The hook uses postponed
annotations to retain Python 3.9 syntax compatibility; Python 3.9 runtime was not
executed here. Validation ran on Python 3.12: all 50 offline tests passed and
eight deterministic CLI results matched the preceding version byte for byte.
Annotation and test-expression modernization changes the AST, so this consumer
package does not claim complete AST identity with the canonical source.

These checks cover the new reader files only. The existing Format & Lint job
reported 432 unchanged baseline path entries requiring Black formatting; that
repository-wide gate remains unresolved, and its Ruff step was skipped. No
legacy source, committed virtualenv, or existing check configuration was changed.
