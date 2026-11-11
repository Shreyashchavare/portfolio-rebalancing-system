# Phase 6.4.1 — Workflow API, Core Migration & Integration Corrections

**Repository:** `E:\Yottaflex\portfolio-rebalancing-system` 
**Branch:** `main`  
**Mode:** Implementation with tests-first workflow. No commit or push.

## Objective

Resolve the four confirmed Phase 6.4 integration findings:

1. Expose unified workflow initiation through FastAPI.
2. Add the missing baseline PostgreSQL migration for the 11 core tables.
3. Stabilize SQLite concurrency tests.
4. Persist and reconstruct complete post-trade simulation results.

## Mandatory workflow

1. Inspect the current repository and confirm the actual Git status.
2. Run the relevant baseline tests and record the exact failure, if any.
3. Write behavioral tests first and demonstrate RED for each correction.
4. Implement the smallest compatible changes.
5. Run targeted tests, then the complete test suite.
6. Run `git diff --check`.
7. Save this prompt and concise RED/GREEN execution record in `prompts/phase-6/06-integration-stabilization.md`.
8. Do not commit or push.

Do not assume the previous audit's reported Git status is accurate. Resolve its contradiction using actual command output.

## Task 1 — Unified workflow initiation API

Inspect:
- `WorkflowRequest` and `WorkflowResponse`.
- `WorkflowService.run_workflow()`.
- Existing workflow retrieval endpoint.
- FastAPI router conventions and dependency injection.
- Current authentication dependencies.

Implement:

`POST /api/v1/workflows`

The endpoint must:
- Accept the existing typed `WorkflowRequest`.
- Call `WorkflowService.run_workflow()` exactly once.
- Return the existing typed workflow response.
- Reuse existing idempotency and exception handling.
- Return safe HTTP errors for missing portfolios, idempotency conflicts, and unexpected failures.
- Use the existing authenticated-principal boundary. Never trust client-supplied reviewer identity.
- Fail closed where verified authentication is unavailable; do not invent authentication.
- Preserve existing `GET /api/v1/workflows/{workflow_id}` behavior.

Do not duplicate workflow logic inside the route.

Add tests for successful workflow initiation, invalid request, missing portfolio, idempotent retry, changed-payload conflict, authentication failure, and safe internal error handling.

## Task 2 — Baseline PostgreSQL migration

Create:

`docs/migrations/000_create_core_tables.sql`

It must provision the 11 original core tables:

1. `investor_profile`
2. `portfolio`
3. `instrument`
4. `holding`
5. `market_price`
6. `target_allocation`
7. `fee_schedule`
8. `constraint`
9. `constraint_instrument`
10. `rebalance_proposal`
11. `trade`

Requirements:
- Inspect every corresponding SQLAlchemy model and relationship before writing DDL.
- Match exact table names, column names, lengths, precision, nullability, defaults, enums/check constraints, primary keys, foreign keys, and indexes.
- Preserve financial `NUMERIC` precision. Do not use floating-point columns for monetary values.
- Respect foreign-key creation order and resolve circular dependencies if any.
- Quote PostgreSQL reserved identifiers such as `constraint`.
- Match actual ORM definitions; do not invent columns or constraints.
- Ensure migrations 001, 002, and 003 can follow migration 000 in order.
- Do not modify the existing 001–003 migrations unless a proven incompatibility requires it. Document any necessary correction.
- No destructive DDL or data deletion.

Verify PostgreSQL dialect compatibility and, if Docker is available, use a **new disposable PostgreSQL database/container** for migration execution. Do not restart, modify, or delete the existing `yottaflex-verification-postgres` container or its volume.

If live migration execution is not safely possible, report that limitation. Do not claim successful application based only on compilation.

## Task 3 — Stabilize SQLite concurrency tests

Inspect `tests/test_approval_audit_api.py` and the `_create_sqlite_session()` fixture.

The current `StaticPool` configuration shares one SQLite connection across concurrent threads and has caused intermittent `sqlite3.InterfaceError`.

Correct the test design without weakening the concurrency assertions.

Preferred approach:
- Use an isolated temporary file-backed SQLite database for concurrency tests, with independent connections per thread.
- Ensure proper session and connection cleanup.
- Preserve the test asserting exactly one winner for conflicting decisions.
- Preserve deterministic idempotency behavior for identical decisions.
- Do not replace concurrency tests with sequential tests.
- Do not claim SQLite tests prove PostgreSQL row-lock behavior.

Run the concurrency tests repeatedly to check for flakiness. Record the number of successful repetitions.

## Task 4 — Complete simulation persistence and reconstruction

Inspect:
- `PostTradeSimulationResult`.
- `WorkflowContext`.
- `WorkflowService` result serialization.
- `WorkflowExecutor.reconstruct_proposal_response()`.
- Existing proposal and trade persistence.

Correct the incomplete reconstruction of simulation details.

Requirements:
- Persist the original deterministic simulation snapshot in `workflow_run.result_payload`, using JSON-safe serialization.
- Include all available simulation fields, such as simulated positions, asset-class allocations, cash, pre/post-trade values, residual drift, and relevant diagnostics.
- Reconstruct the exact stored simulation response when an existing workflow is requested again.
- Validate stored payloads safely and handle legacy records that lack a simulation snapshot without inventing values.
- Do not rerun proposal generation or simulation unnecessarily on an idempotent retry.
- Do not mutate holdings, portfolio positions, proposals, or trades during reconstruction.

Add tests that compare the original and reconstructed simulation values, verify idempotency, and cover legacy result payloads.

## Required regression tests

Run at least:

- Workflow API tests.
- Approval and audit API tests.
- Workflow orchestration tests.
- Explanation service tests.
- Rebalancing service and simulation API tests.
- Analytics API and service tests.
- Policy RAG tests.
- Full `pytest -q`.

Repeat both concurrency tests at least 10 times if practical.

## Explicit exclusions

Do NOT:
- Integrate an external identity provider.
- Enable development mock authentication in production.
- Execute trades or mutate holdings.
- Modify the existing full synthetic dataset.
- Restart or delete existing Docker containers or volumes.
- Redesign the architecture.
- Add unrelated dependencies.
- Implement frontend work.
- Commit or push.

## Final report

Include:
1. Exact initial Git status and baseline test failure, if any.
2. Files created and modified.
3. RED and GREEN evidence for each task.
4. Workflow endpoint behavior and authorization.
5. Core migration schema alignment and actual database execution status.
6. Repeated concurrency test results.
7. Simulation persistence/reconstruction verification.
8. Targeted and full regression counts.
9. `git diff --check` and final Git status.
10. Unresolved limitations and elapsed time.

Classify the batch as:
- APPROVED
- APPROVED WITH DOCUMENTED LIMITATIONS
- CHANGES REQUIRED

**Maximum 120 minutes. Stop and report if a safe implementation cannot be completed within the timebox. Do not commit or push.**

---

## Execution Record

### 1. Initial Baseline & Environment Inspection
*(To be populated during execution)*

