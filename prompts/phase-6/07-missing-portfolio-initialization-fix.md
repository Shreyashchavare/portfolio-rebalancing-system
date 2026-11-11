# Phase 6.4.2 — Missing Portfolio Workflow Initialization Fix

Repository: `portfolio-rebalancing-system`

## Objective
Resolve the single failing workflow initiation test without weakening authentication, idempotency, transaction integrity, or existing financial safeguards.

Failing test:
`TestWorkflowInitiationRESTAPI.test_initiate_workflow_missing_portfolio_returns_404`

Expected: HTTP 404
Actual: HTTP 422

Captured log:
`Database concurrency integrity conflict during workflow initialization.`

## Mandatory TDD workflow

1. Inspect the failing test, workflow REST endpoint, WorkflowService initialization, database session lifecycle, and exception handling.
2. Reproduce the existing failure and document RED evidence.
3. Add or refine focused tests before changing production code.
4. Implement the smallest correct fix.
5. Run focused tests and then the entire test suite.

## Required investigation

Determine why a nonexistent portfolio causes WorkflowRun initialization to produce an IntegrityError that is classified as a concurrency conflict.

Verify:
- Portfolio existence is checked using the correct database session and before creating WorkflowRun.
- Missing portfolio returns HTTP 404.
- A genuine idempotency uniqueness race is still handled correctly.
- A foreign-key violation is not mislabeled as an idempotency conflict.
- The transaction is rolled back safely after database errors.
- No orphaned WorkflowRun or RebalanceProposal is created.
- Existing same-key/same-payload idempotency behavior remains intact.
- Same key with a different payload still returns HTTP 409.
- Authentication remains fail-closed.

Do not:
- Change the test to expect 422.
- Catch every IntegrityError and return 404.
- Remove foreign-key constraints.
- Weaken idempotency or transaction handling.
- Change financial calculation logic.
- Introduce unnecessary dependencies or architecture changes.

## Tests required

At minimum:
1. Missing portfolio returns 404.
2. Existing portfolio starts workflow successfully.
3. Repeated identical request does not create a duplicate proposal.
4. Same key with different payload returns 409.
5. Genuine database initialization conflict is handled correctly.
6. No workflow or proposal is left behind after failed initialization.

## Verification

Run:
- Focused workflow initiation tests.
- Full `pytest -q`.
- `git diff --check`.

Record exact test counts and results. Preserve the existing PostgreSQL migration work and do not touch the existing verification container.

Save the prompt and concise RED/GREEN record in:
`prompts/phase-6/07-missing-portfolio-initialization-fix.md`

Maximum time: 120 minutes. Do not commit or push.

Final report must include changed files, root cause, RED/GREEN evidence, full test output, and unresolved limitations.

---

## Execution Record

### 1. Root Cause Analysis
- **Problem Statement:** Calling `POST /api/v1/workflows` with a non-existent `portfolio_id` returned `HTTP 422 Unprocessable Entity` with log `Database concurrency integrity conflict during workflow initialization.` instead of `HTTP 404 Not Found`.
- **Underlying Cause:**
  1. `WorkflowRun.portfolio_id` has a foreign key constraint referencing `portfolio.portfolio_id`.
  2. In `WorkflowService.run_workflow()`, `WorkflowRun` was instantiated and `session.add(workflow_run); session.commit()` was executed before validating that `request.portfolio_id` existed in the `portfolio` table.
  3. When `request.portfolio_id` did not exist, the database rejected the insert with a foreign-key `IntegrityError`.
  4. The exception handler in `WorkflowService.run_workflow()` caught any `IntegrityError` under the assumption that it was caused by an idempotency collision on `uq_workflow_runs_portfolio_request_key`.
  5. The handler then queried for an existing `concurrent_run` matching `(portfolio_id, request_key)`. Because no run existed (the failure was due to a missing parent portfolio, not a duplicate key), `concurrent_run` was `None`, prompting the code to raise `WorkflowExecutionError("Database concurrency integrity conflict during workflow initialization.")`.
  6. In `app/api/v1/workflows.py`, `WorkflowExecutionError` was caught and converted to `HTTP 422 Unprocessable Entity` instead of `HTTP 404 Not Found`.

### 2. RED Evidence
Focused behavioral tests executed before changing production code:
```bash
.\.venv\Scripts\python.exe -m pytest tests/test_workflow_orchestration.py -k "missing_portfolio" -v
```
Output:
```text
FAILED tests/test_workflow_orchestration.py::TestWorkflowInitiationRESTAPI::test_initiate_workflow_missing_portfolio_returns_404 - assert 422 == 404
 + where 422 = <Response [422 Unprocessable Entity]>.status_code
 + and 404 = status.HTTP_404_NOT_FOUND
WARNING app.api.v1.workflows:workflows.py:66 Workflow execution failed for portfolio PORT-NONEXISTENT: Database concurrency integrity conflict during workflow initialization.

FAILED tests/test_workflow_orchestration.py::TestWorkflowInitiationRESTAPI::test_run_workflow_missing_portfolio_raises_portfolio_not_found_error - WorkflowExecutionError: Database concurrency integrity conflict during workflow initialization.

FAILED tests/test_workflow_orchestration.py::TestWorkflowInitiationRESTAPI::test_no_workflow_or_proposal_left_behind_after_missing_portfolio_error - assert 422 == 404
 + where 422 = <Response [422 Unprocessable Entity]>.status_code
 + and 404 = status.HTTP_404_NOT_FOUND

3 failed, 29 deselected, 3 warnings in 1.63s
```

### 3. Implementation Details
Modified `app/services/orchestration/workflow_service.py`:
1. Imported `Portfolio` from `app.models.portfolio`.
2. Added an upfront portfolio existence check before creating or adding a `WorkflowRun`:
   ```python
   # 0. Portfolio existence validation
   portfolio = self.session.get(Portfolio, request.portfolio_id)
   if portfolio is None:
       raise PortfolioNotFoundError(request.portfolio_id)
   ```
3. Hardened the `IntegrityError` handler:
   ```python
   except IntegrityError as exc:
       self.session.rollback()
       # If the portfolio was concurrently removed or missing, raise PortfolioNotFoundError
       if self.session.get(Portfolio, request.portfolio_id) is None:
           raise PortfolioNotFoundError(request.portfolio_id) from exc

       # Concurrent duplicate request race condition
       concurrent_run = (
           self.session.query(WorkflowRun)
           .filter_by(
               portfolio_id=request.portfolio_id,
               request_key=request.request_key,
           )
           .first()
       )
       if concurrent_run:
           return self._handle_existing_run(concurrent_run, request, as_of)
       raise WorkflowExecutionError("Database concurrency integrity conflict during workflow initialization.") from exc
   ```
4. Added focused regression tests to `TestWorkflowInitiationRESTAPI` in `tests/test_workflow_orchestration.py`:
   - `test_run_workflow_missing_portfolio_raises_portfolio_not_found_error`: Verifies direct service exception mapping.
   - `test_no_workflow_or_proposal_left_behind_after_missing_portfolio_error`: Verifies zero orphan `WorkflowRun` or `RebalanceProposal` records exist when initialization fails.

### 4. GREEN Evidence & Invariants Verification
Focused tests:
```bash
.\.venv\Scripts\python.exe -m pytest tests/test_workflow_orchestration.py -k "missing_portfolio" -v
```
Output:
```text
tests/test_workflow_orchestration.py::TestWorkflowInitiationRESTAPI::test_initiate_workflow_missing_portfolio_returns_404 PASSED [ 33%]
tests/test_workflow_orchestration.py::TestWorkflowInitiationRESTAPI::test_run_workflow_missing_portfolio_raises_portfolio_not_found_error PASSED [ 66%]
tests/test_workflow_orchestration.py::TestWorkflowInitiationRESTAPI::test_no_workflow_or_proposal_left_behind_after_missing_portfolio_error PASSED [100%]
================= 3 passed, 29 deselected, 1 warning in 1.11s =================
```

All 6 Minimum Required Test Scenarios Verified:
1. Missing portfolio returns 404: `test_initiate_workflow_missing_portfolio_returns_404` and `test_run_workflow_missing_portfolio_raises_portfolio_not_found_error` (PASSED).
2. Existing portfolio starts workflow successfully: `test_initiate_workflow_success_returns_200` (PASSED).
3. Repeated identical request does not create duplicate proposal: `test_initiate_workflow_idempotent_retry_returns_200_same_workflow` and `test_proposal_generation_invoked_exactly_once` (PASSED).
4. Same key with different payload returns 409: `test_initiate_workflow_idempotency_conflict_returns_409` and `test_same_request_key_different_payload_is_rejected` (PASSED).
5. Genuine database initialization conflict handled correctly: `test_concurrent_integrity_error_during_initialization_recovers_gracefully` (PASSED).
6. No workflow or proposal left behind after failed initialization: `test_no_workflow_or_proposal_left_behind_after_missing_portfolio_error` (PASSED).

### 5. Full Regression Suite Output
```bash
.\.venv\Scripts\python.exe -m pytest -q
```
Output:
```text
461 passed, 1 skipped, 7 warnings in 17.84s
```
- Total tests collected: 462
- Passed: 461
- Skipped: 1 (`tests/test_policy_ingestion_and_vectors.py::TestVectorStoreDatabaseIntegration::test_pgvector_similarity_search_in_database` when pgvector is not available in SQLite)
- Failed: 0

### 6. Code Quality & Constraints Check
- `git diff --check`: 0 errors / 0 trailing whitespace.
- Working tree: No commits, no pushes.
- Docker containers: Untouched existing container `yottaflex-verification-postgres`.
- Financial safety: Holdings never modified; trades never executed; all calculations purely deterministic and proposal-staged.
