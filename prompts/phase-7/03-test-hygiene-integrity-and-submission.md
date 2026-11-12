# Phase 7 — Test Hygiene, Final Integrity and Submission

## Test quality
- Remove deprecated API usage and resolve dependency warnings where practical.
- Investigate skipped tests rather than leaving security coverage silently disabled.
- Keep tests deterministic and isolated.
- Run focused suites after fixes, then the complete backend/frontend checks.

## Final integrity review
- Verify migration integrity and safe upgrade behavior.
- Verify policy-ingestion path checks occur before file reads.
- Verify per-document failure isolation.
- Verify database seeding and authentication configuration.
- Confirm README and deployment instructions match actual behavior.

## Submission preparation
- Inspect repository status and ensure no secrets, temporary files or generated local databases are accidentally committed.
- Keep a concise reviewer demo and explain the key workflow.
- Record actual test counts and known limitations; do not copy stale results from earlier runs.
- Preserve Git history and avoid unrelated cleanup.

## Completion evidence
The source archive includes a reviewer demo/submission phase and historical test-hygiene records. Exact final counts should be taken from a fresh run of the current checkout.
