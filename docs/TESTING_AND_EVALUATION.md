# Testing and Evaluation

## Automated validation results

The supplied validation records report:

| Check | Result |
|---|---:|
| Backend pytest | 517 passed |
| Frontend Vitest | 64 passed across 11 files |
| TypeScript typecheck | Passed |
| ESLint | Passed |
| Vite production build | Passed |
| Negative financial scenarios | 5/5 passed (reported) |
| Dataset reproducibility artifacts | 26/26 passed (reported) |
| Full dataset integrity checks | 12/12 passed (reported) |

These are automated tests and scripted checks, not 581 browser-based end-to-end tests. Re-run the live browser-to-API journey before making a new release claim.

## Recommended evaluation

1. Start the backend and frontend using `README.md`.
2. Sign in using a local development persona only if mock authentication is explicitly enabled for local testing.
3. Open a portfolio and verify valuation, holdings and drift.
4. Ask a policy question and confirm retrieved evidence/citations are present.
5. Generate a proposal and inspect staged trades, fees, simulation and constraint results.
6. Sign in as an authorized reviewer and approve or reject the proposal with required notes/reason.
7. Verify proposal status and audit event through the UI/API; refresh and confirm persistence.
8. Verify workflow status and idempotent retry behavior.
9. Confirm a viewer cannot approve/reject and unauthenticated requests are rejected.

Use a dedicated synthetic test database. Do not run reset or destructive operations against valuable data. Confirm reset behavior and ensure prior audit history remains intact.

## Known considerations

- Earlier frontend test output included JSDOM network `AggregateError` messages although tests passed. Mock API requests in component tests and use a real browser for integration verification.
- Recharts reported zero-width/height warnings in JSDOM; verify chart rendering in a browser viewport.
- The production JavaScript bundle exceeded 1 MB after minification; consider route-level code splitting if performance work is in scope.
- React Router future-flag notices are informational.
- Ollama is optional for the documented fallback path; validate retrieval and citations independently of generated prose.

## Before submission

Inspect the Git diff, ensure secrets and local database files are excluded, rerun relevant tests, and verify the live UI-to-API workflow. Keep production authentication fail-closed and retain the no-live-trading boundary.
