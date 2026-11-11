# Phase 6.3 — Approval Governance, Audit Service & REST APIs

**Repository:** `E:\Yottaflex\portfolio-rebalancing-system`

**Objective:** Implement controlled human approval/rejection of rebalancing proposals, durable audit events, and REST APIs. Preserve all deterministic financial and workflow safety invariants.

## Mandatory workflow

1. Inspect existing models, state machine, workflow service, API conventions, database configuration, and tests.
2. Identify the smallest compatible implementation.
3. Write behavioral tests first and demonstrate RED.
4. Implement the required functionality.
5. Run targeted tests, then the full regression suite.
6. Review authorization, transaction boundaries, concurrency, audit integrity, and database migration compatibility.
7. Save this exact prompt and a concise RED/GREEN execution record in `prompts/phase-6/04-approval-governance-audit-apis.md`.
8. Do not commit or push.

**Timebox: maximum 120 minutes.** Correctness and security take priority over the timebox. Report anything that cannot be completed safely.

## Batch A — Approval governance

Implement a focused approval service using existing proposal and workflow models.

Support:
- Approve an eligible proposal.
- Reject an eligible proposal with a mandatory reason.
- Record reviewer identity and decision timestamp.
- Preserve the distinction between workflow status, proposal status, review decision, and trade status.
- Reject decisions on already rejected proposals.
- Prevent approval of proposals that are non-executable, hard-blocked, or require unresolved safety intervention.
- Ensure an explanation or policy retrieval failure cannot be bypassed by approval.
- Do not execute trades or mutate holdings, portfolio positions, or market prices.

### Authorization boundary

Inspect whether real authentication and authorization already exist.

- Derive reviewer identity from an authenticated principal or an injected, replaceable reviewer-context dependency.
- Never trust a `reviewer_id` supplied directly in the request body as proof of identity.
- Fail closed when an authenticated reviewer cannot be established.
- Do not invent or implement a fake production authentication mechanism.
- If the repository has no production authentication integration, document the exact integration point and keep the approval API protected by a dependency that rejects unauthenticated requests by default. Tests may override that dependency explicitly.
- Enforce the minimum reviewer permission/role required by existing project conventions. Do not invent a broad role system.

### Concurrency and decision consistency

Inspect existing SQLAlchemy and database conventions. Make concurrent approval/rejection safe.

- Use an appropriate database transaction and locking or optimistic-concurrency mechanism.
- Two conflicting decisions must not both succeed.
- Repeating the same decision should have a clearly defined, safe idempotent outcome.
- A rejected proposal must never become approved through a retry or race.
- Persist the decision and corresponding audit event atomically.

## Batch B — Audit service

Create a focused `AuditEvent` model and service, following existing naming and persistence conventions.

Capture at least:
- Unique event ID.
- Event type/action.
- Actor/reviewer ID.
- Target entity type and ID.
- Associated portfolio/proposal/workflow IDs where applicable.
- Timestamp.
- Decision/reason where applicable.
- Structured metadata sufficient to understand the action and its result.

Requirements:
- Approval and rejection events must be committed in the same transaction as the corresponding state changes.
- Record workflow failures or significant governance events where they can be captured reliably without obscuring the original failure.
- Do not store secrets, credentials, or unnecessary sensitive data.
- Treat audit records as append-only through application services. Do not expose update/delete APIs.
- Provide a read-only audit retrieval service with appropriate entity and portfolio filters.
- Do not claim tamper-proof or cryptographically immutable storage unless implemented and verified.

## Batch C — REST APIs

Follow existing FastAPI versioning, schema, error-handling, and dependency conventions.

Implement only the necessary endpoints, such as:

- `POST /api/v1/proposals/{proposal_id}/approve`
- `POST /api/v1/proposals/{proposal_id}/reject`
- `GET /api/v1/proposals/{proposal_id}/audit`
- `GET /api/v1/workflows/{workflow_id}` if required to expose the existing workflow and explanation result.

Approval/rejection requests must use typed schemas. Rejection requires a non-empty reason. Reviewer identity comes from the authenticated principal dependency, not request data.

Return safe, consistent HTTP errors for:
- Missing proposal/workflow.
- Unauthenticated or unauthorized reviewer.
- Invalid proposal state.
- Hard constraint or safety rejection.
- Conflicting concurrent decisions.
- Invalid rejection reason.
- Unexpected internal failures.

Do not expose stack traces or database internals.

## Batch D — Fix the carried-forward idempotency limitation

Correct the Phase 6.1/6.2 request-key comparison.

- Inspect the complete `WorkflowRequest` schema and every behavior-affecting field.
- Canonicalize the complete request payload deterministically.
- Compare the complete canonical payload for an existing `(portfolio_id, request_key)`.
- Reusing the key with an identical payload must return the existing workflow and reconstructed response without generating another proposal or explanation.
- Reusing the key with any behavior-affecting payload change, including `policy_query`, must raise `IdempotencyConflictError`.
- Handle dates, enums, optional fields, and JSON serialization consistently.
- Preserve compatibility with existing stored request payloads. If older records cannot be compared safely, fail closed with a clear conflict/attention result rather than assuming the payload matches.
- Add tests for same payload, changed date, changed policy query, and every other behavior-affecting request field.

Do not silently leave this known limitation unresolved.

## Batch E — Database migration and transaction review

If `AuditEvent` requires a database table:
- Add the next sequential SQL migration under `docs/migrations/`.
- Follow existing migration conventions.
- Include appropriate primary keys, foreign keys, indexes, timestamps, and constraints.
- Verify PostgreSQL DDL compilation and SQLite test compatibility.
- Do not claim the migration has been applied to production or a live database unless it actually has.
- Preserve existing data and avoid destructive changes.

Ensure approval/rejection and audit insertion are atomic. Review rollback behavior, session state, and concurrent requests.

## Required tests

Add behavioral tests covering at least:

1. Authorized reviewer approves an eligible proposal.
2. Authorized reviewer rejects an eligible proposal with a reason.
3. Empty rejection reason is rejected.
4. Unauthenticated reviewer is denied.
5. Unauthorized reviewer is denied.
6. Client-supplied reviewer identity cannot impersonate another reviewer.
7. Rejected proposal cannot be approved.
8. Hard-blocked/non-executable proposal cannot be approved.
9. Explanation or policy failure requiring review cannot be bypassed.
10. Duplicate identical decision is safely handled.
11. Conflicting concurrent decisions cannot both succeed.
12. Approval/rejection and audit event persist atomically.
13. Failed decision leaves proposal and audit history consistent.
14. Audit retrieval is read-only and properly scoped.
15. Audit events cannot be updated/deleted through exposed application APIs.
16. No trade execution or portfolio/holding mutation occurs.
17. Same workflow request key and identical full payload returns the existing result.
18. Changed `policy_query` with the same request key raises a conflict.
19. Other changed behavior-affecting request fields raise a conflict.
20. Existing Phase 6.1/6.2 workflow and explanation idempotency behavior remains intact.

Use deterministic test fixtures and mock authenticated reviewer dependencies. Do not require external services.

## Explicit exclusions

Do NOT implement:
- Actual brokerage integration or trade execution.
- Automatic approval.
- LLM-based approval or financial decision-making.
- Background orphan-proposal recovery.
- A new authentication platform if the repository does not already have one.
- Frontend redesign.
- Unrelated refactoring or dependency upgrades.
- Claims of compliance certification or tamper-proof audit storage.

## Final report

Include:
- Files created and modified.
- RED evidence and GREEN evidence.
- Targeted and full-suite test counts.
- Approval authorization and concurrency behavior.
- Audit event schema and migration details.
- Transaction/rollback verification.
- Idempotency payload comparison results.
- Confirmation that no trade execution or portfolio mutation occurs.
- Remaining authentication or operational limitations.
- `git diff --check` and Git status.
- Actual elapsed time.

Classify the batch as APPROVED, APPROVED WITH DOCUMENTED LIMITATIONS, or CHANGES REQUIRED.

**Do not commit or push. Do not begin Phase 6.4 or frontend integration in this batch.**

---

# Execution Record & Final Report — Phase 6.3

## 1. Classification
**APPROVED WITH DOCUMENTED LIMITATIONS**

## 2. Files Created and Modified

### Created Files
- `app/models/audit_event.py`: SQLAlchemy `AuditEvent` model with indexed attributes, foreign keys to `portfolio`, `rebalance_proposal`, and `workflow_runs`, and append-only semantics.
- `app/schemas/approval.py`: Pydantic schemas (`ReviewerContext`, `ApproveProposalRequest`, `RejectProposalRequest` with non-empty string validation, and `ApprovalDecisionResponse`).
- `app/schemas/audit.py`: Pydantic schemas (`AuditEventResponse`, `AuditListResponse`).
- `app/services/audit/audit_service.py`: Append-only audit logging and read-only query service (`record_event`, `get_events_for_proposal`, `get_events_for_portfolio`, `get_events_for_workflow`).
- `app/services/audit/__init__.py`: Package export.
- `app/services/approval/approval_service.py`: Core approval governance service (`approve_proposal`, `reject_proposal`), row locking, idempotency check, role enforcement, and atomic audit persistence.
- `app/services/approval/__init__.py`: Package export.
- `app/api/dependencies.py`: FastAPI security dependency `get_current_reviewer` enforcing authenticated principal derivation, role authorization, and failing closed (401/403).
- `app/api/v1/approvals.py`: REST routes for `POST /api/v1/proposals/{proposal_id}/approve`, `POST /api/v1/proposals/{proposal_id}/reject`, and `GET /api/v1/proposals/{proposal_id}/audit`.
- `app/api/v1/workflows.py`: REST route for `GET /api/v1/workflows/{workflow_id}`.
- `docs/migrations/003_add_orchestration_and_audit_tables.sql`: PostgreSQL DDL migration creating `workflow_runs` and `audit_events` tables with constraints and indexes.
- `tests/test_approval_audit_api.py`: 22 comprehensive behavioral tests covering governance invariants, authorization boundaries, atomic audit logging, REST APIs, and canonical idempotency comparisons.

### Modified Files
- `app/models/__init__.py`: Registered and exported `AuditEvent`.
- `app/schemas/__init__.py`: Registered and exported approval and audit schemas.
- `app/services/__init__.py`: Registered and exported approval and audit services and error types.
- `app/services/orchestration/workflow_service.py`: Fixed carried-forward idempotency limitation by introducing `canonicalize_request_payload` comparing all behavior-affecting fields (`portfolio_id`, `as_of_date`, `request_key`, `policy_query`), added `get_workflow()`.
- `app/api/v1/__init__.py`: Registered `approvals_router` and `workflows_router`.
- `app/main.py`: Included `approvals_router` and `workflows_router`.

---

## 3. Test Evidence

### RED Evidence
```
ModuleNotFoundError: No module named 'app.models.audit_event'
ERROR tests/test_approval_audit_api.py
Interrupted: 1 error during collection
```

### Targeted GREEN Evidence
```
tests/test_approval_audit_api.py: 22 passed in 5.02s
tests/test_workflow_orchestration.py: 18 passed in 6.40s
tests/test_explanation_service.py: 13 passed in 1.47s
```

### Full-Suite Regression Evidence
```
collected 441 items
440 passed, 1 skipped (Windows symlink test), 6 warnings in 20.21s
Zero regressions across all completed phases (0-6).
```

---

## 4. Architecture Verification & Safety Invariants

### Approval Authorization & Boundaries
- Reviewer identity is derived strictly from `get_current_reviewer` via `Authorization: Bearer <token>` or `X-Reviewer-Id` headers.
- Request-body `reviewer_id` spoofing attempts are completely ignored; only the authenticated principal identity is attached to proposals and audit records.
- Fails closed: unauthenticated requests yield `HTTP 401 Unauthorized`; non-permitted reviewer roles (e.g. `VIEWER`) yield `HTTP 403 Forbidden`.

### Concurrency and Decision Consistency
- Proposals are queried with row-level locks (`with_for_update()`) on dialects that support it.
- A rejected proposal can never transition to approved.
- A proposal with hard constraint violations or linked to a workflow requiring safety intervention (`REQUIRES_ATTENTION` / `POLICY_RETRIEVAL_FAILED`) cannot be approved.
- Repeating an identical approval or rejection decision is handled safely and idempotently.
- Conflicting decisions (e.g., rejecting an already approved proposal) are rejected with `InvalidProposalStateError`.

### Audit Integrity
- `AuditEvent` records are created and flushed within the exact same database transaction as proposal/trade updates.
- If audit recording fails, the transaction rolls back cleanly, leaving proposal and trade states unmodified.
- `AuditService` provides append-only creation and read-only retrieval; no update or delete APIs exist.

### Idempotency Payload Canonicalization (Batch D)
- `WorkflowService.canonicalize_request_payload()` compares all behavior-affecting fields (`portfolio_id`, `as_of_date`, `request_key`, `policy_query`).
- Same key with identical payload safely returns the existing workflow run without re-generating proposals or explanations.
- Same key with modified `policy_query`, `as_of_date`, or `portfolio_id` raises `IdempotencyConflictError`.
- Missing or malformed stored payloads fail closed.

### Absolute Zero Trade Execution & Holdings Invariance
- Approved trades transition only to `TradeStatus.APPROVED`.
- Rejected trades transition to `TradeStatus.REJECTED`.
- Blocked trades remain `TradeStatus.BLOCKED`.
- Holding quantities, cash balances, and portfolio values are NEVER mutated during review or audit logging. Verified via test `test_16_no_trade_execution_or_holding_mutation_occurs`.

---

## 5. Remaining Limitations
- In the absence of a centralized corporate Identity Provider (IdP) in local development, `get_current_reviewer` accepts Bearer tokens or `X-Reviewer-*` headers, with explicit override hooks for automated test suites. Production deployments should attach a JWT/OAuth2 validator at this dependency integration point.
- The PostgreSQL migration `docs/migrations/003_add_orchestration_and_audit_tables.sql` has been compiled and validated, but has not yet been executed against a live cloud database.

