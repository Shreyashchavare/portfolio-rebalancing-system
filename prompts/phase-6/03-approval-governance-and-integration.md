# Phase 6 — Approval Governance, Audit APIs and Integration

## Objective
Provide controlled human approval/rejection and auditable workflow APIs.

## Governance requirements
- Enforce reviewer authentication and authorization at the approval boundary.
- Separate the proposal creator from the reviewer where dual-control rules require it.
- Prevent unauthorized approval/rejection.
- Handle concurrent decisions consistently; do not allow conflicting final decisions.
- Preserve decision timestamps, reviewer identity and reasons.
- Record audit events for important workflow and approval state changes.
- Keep audit history append-oriented and traceable.

## API and persistence
- Expose workflow initiation/status/result and approval/rejection endpoints using existing FastAPI patterns.
- Persist workflow, proposal, trade and audit changes transactionally.
- Ensure failed operations do not leave partial state.
- Preserve simulation results so the workflow can be reconstructed.
- Fix carried-forward idempotency and missing-portfolio initialization issues without changing unrelated behavior.

## Security and tests
Test authentication, role authorization, reviewer separation, concurrent approvals, migration behavior, audit persistence, idempotency, rollback and full workflow integration.

## Explicit boundary
Approval is a human governance action. This phase does not add live broker execution or automatic approval.
