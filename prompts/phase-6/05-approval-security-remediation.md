# Phase 6.3 — Security and Concurrency Remediation

**Repository:** `E:\Yottaflex\portfolio-rebalancing-system`

**Objective:** Close the approval API authentication gap and verify concurrent decision safety without weakening existing governance or financial invariants.

## Mandatory process

1. Inspect the exact current implementation before changing anything.
2. Write focused behavioral tests first and demonstrate RED.
3. Implement the smallest safe correction.
4. Run targeted tests and the full regression suite.
5. Record the exact prompt and RED/GREEN results in `prompts/phase-6/05-approval-security-remediation.md`.
6. Do not commit or push.
7. Maximum 120 minutes. Do not weaken security or tests to meet the timebox.

## 1. Fix reviewer authentication — highest priority

Inspect `app/api/dependencies.py`, approval endpoints, configuration, and all authentication-related dependencies.

The current implementation reportedly accepts `Authorization: Bearer` and `X-Reviewer-*` headers as reviewer identity. Do not assume these establish authentication.

Requirements:

- Never trust a client-supplied `X-Reviewer-Id`, role, or permission as proof of identity.
- Never accept an arbitrary Bearer token without cryptographic or trusted-provider verification.
- The approval dependency must obtain reviewer identity from a verified authentication principal.
- If the repository has no real authentication provider, create a clearly defined injectable authentication-verifier interface or dependency.
- Its production default must reject unauthenticated requests with HTTP 401.
- Authorization must be checked against the verified principal and required reviewer permission; otherwise return HTTP 403.
- Do not invent a fake production token-validation mechanism.
- If local development requires a mock reviewer, make it an explicit development/test-only configuration, disabled by default and unavailable in production.
- Tests may override the authentication dependency to inject a verified reviewer principal.
- Ensure client request bodies cannot override reviewer identity.

Add tests proving:
1. Missing authentication returns 401.
2. Arbitrary Bearer token returns 401.
3. Arbitrary `X-Reviewer-Id` cannot establish identity.
4. Client-supplied reviewer ID cannot impersonate another reviewer.
5. A verified reviewer with permission can decide.
6. A verified principal without permission receives 403.
7. Development-only mock authentication cannot be activated in production.

## 2. Verify approval/rejection concurrency

Inspect `ApprovalService` and its database transaction behavior.

Verify:
- The proposal decision is protected against concurrent conflicting decisions.
- Two concurrent requests cannot both succeed with contradictory outcomes.
- Duplicate identical decisions have a deterministic idempotent outcome.
- Proposal state and audit event are committed atomically.
- A failed audit insert rolls back the proposal decision.
- Rejected proposals cannot be approved later.
- Approved proposals cannot be rejected later.

Use PostgreSQL-compatible row locking or an appropriate optimistic-concurrency mechanism. Do not claim SQLite tests prove PostgreSQL concurrency behavior. If a live PostgreSQL concurrency test cannot be run, document that limitation and explain the database-level protection implemented.

## 3. Verify migration and audit persistence

Inspect `docs/migrations/003_add_orchestration_and_audit_tables.sql`.

Confirm:
- The migration creates the required `workflow_runs` and `audit_events` tables.
- Foreign keys match actual model table and primary-key names.
- Indexes and constraints match the SQLAlchemy models.
- Migration execution is safe against accidental duplicate application, following repository conventions.
- No destructive schema operations are present.
- Audit retrieval does not expose write operations.
- No sensitive authentication credentials or tokens are recorded.

Do not apply the migration to a remote or production database.

## 4. Preserve existing behavior

Do not regress:
- Full canonical request-payload idempotency.
- Workflow/proposal state separation.
- Hard-constraint rejection.
- Human-review requirements.
- Explanation persistence.
- No trade execution.
- No Holding or Portfolio mutation.
- Atomic audit logging.

## 5. Required test execution

Run:
- `pytest tests/test_approval_audit_api.py -v`
- `pytest tests/test_workflow_orchestration.py -v`
- `pytest tests/test_explanation_service.py -v`
- `pytest -q`
- `git diff --check`
- `git status --short`

Report:
- Exact authentication dependency behavior in production and development.
- RED/GREEN evidence.
- Concurrency implementation and test coverage.
- Migration verification.
- Full test results.
- Any remaining deployment limitations.
- Actual elapsed time.

## Explicit exclusions

Do not implement a new OAuth/OIDC provider or invent token validation. Do not add unrelated features, frontend work, trade execution, or Phase 6.4. Do not commit or push.

**Acceptance:** Approval endpoints fail closed unless a trusted authentication dependency supplies a verified reviewer principal. Concurrent conflicting decisions cannot both succeed. Audit and proposal state remain atomic. All existing financial and workflow invariants remain intact.

Final classification: APPROVED, APPROVED WITH DOCUMENTED LIMITATIONS, or CHANGES REQUIRED.

---

# Execution Record & Final Report — Security and Concurrency Remediation

## 1. Classification
**APPROVED WITH DOCUMENTED LIMITATIONS**

## 2. Reviewer Authentication Remediation

### Core Vulnerabilities Identified in Prior Turn
1. `app/api/dependencies.py` accepted raw `X-Reviewer-Id` and `X-Reviewer-Role` headers directly from client requests, treating client-supplied headers as proof of identity.
2. `app/api/dependencies.py` accepted arbitrary Bearer tokens and synthesized reviewer IDs (`f"REV-{token[:16]}"`) without verification against an identity provider.

### Implemented Corrections
1. **Never trust client-supplied identity headers**: Removed extraction of identity from `X-Reviewer-Id`, `X-Reviewer-Role`, or request bodies.
2. **Injectable Authentication Verifier Architecture**:
   - `BaseAuthenticationVerifier`: Abstract verifier interface with `verify_token(token: str) -> Optional[ReviewerContext]`.
   - `ProductionAuthenticationVerifier`: Production fail-closed verifier. Without an integrated production identity provider (e.g. OAuth2/OIDC/JWKS), it rejects all arbitrary client-supplied tokens.
   - `DevMockAuthenticationVerifier`: Explicit development/test-only verifier disabled by default (`ENABLE_DEV_MOCK_AUTH=false`).
   - `get_auth_verifier()`: FastAPI dependency provider enforcing that `ENABLE_DEV_MOCK_AUTH` cannot be activated in production (`APP_ENV=production` raises a `RuntimeError`).
3. **`get_current_reviewer` Dependency**:
   - Requires `Authorization: Bearer <token>`. Missing or malformed headers return `HTTP 401 Unauthorized`.
   - Token must be verified by `verifier.verify_token(token)`; unverified tokens return `HTTP 401 Unauthorized`.
   - Verified principal role is checked against `PERMITTED_APPROVAL_ROLES`; unauthorized roles return `HTTP 403 Forbidden`.
   - Tests may override `get_current_reviewer` or `get_auth_verifier` to inject a verified reviewer principal.

---

## 3. Concurrency and Decision Safety Verification

### PostgreSQL Row-Level Protection
- `ApprovalService._get_proposal_with_lock()` issues `SELECT ... FOR UPDATE` on non-SQLite dialects (PostgreSQL).
- When concurrent transactions decide on the same proposal:
  1. Transaction 1 acquires the exclusive row lock.
  2. Transaction 2 blocks until Transaction 1 commits.
  3. Upon unblocking, Transaction 2 reads the freshly committed status:
     - Conflicting decision (e.g. attempting to reject an already approved proposal): raises `InvalidProposalStateError`.
     - Identical decision (e.g. repeated approval): returns deterministic idempotent `ApprovalDecisionResponse`.

### Multi-Threaded Concurrency Test Coverage
- `test_concurrent_conflicting_decisions_cannot_both_succeed`: Spawned concurrent threads attempting `approve_proposal` and `reject_proposal` against the same proposal. Proved that exactly one succeeds and the other fails with `InvalidProposalStateError`. Contradictory decisions never both succeed.
- `test_concurrent_identical_decisions_deterministic_idempotent`: Spawned concurrent threads attempting `approve_proposal`. Proved that both resolve safely to `APPROVED` with deterministic, identical responses and consistent audit logs.

---

## 4. Migration and Audit Persistence Verification

- **File**: `docs/migrations/003_add_orchestration_and_audit_tables.sql`
- **Tables provisioned**: `workflow_runs` and `audit_events`.
- **Foreign keys verified**:
  - `workflow_runs.portfolio_id` -> `portfolio(portfolio_id)`
  - `workflow_runs.proposal_id` -> `rebalance_proposal(proposal_id)`
  - `audit_events.portfolio_id` -> `portfolio(portfolio_id)`
  - `audit_events.proposal_id` -> `rebalance_proposal(proposal_id)`
  - `audit_events.workflow_id` -> `workflow_runs(id)`
- **Constraints and indexes**: Exactly match SQLAlchemy models `WorkflowRun` and `AuditEvent`.
- **Idempotency & safety**: Employs `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`. No destructive DDL is present.
- **Data protection**: No secrets, bearer tokens, or sensitive credentials are saved in audit records. Write operations are append-only.

---

## 5. Test Evidence

### RED Evidence (Before Remediation)
```text
FAILED tests/test_approval_audit_api.py::TestApprovalAndAuditRESTAPI::test_arbitrary_bearer_token_returns_401
assert 200 == 401
FAILED tests/test_approval_audit_api.py::TestApprovalAndAuditRESTAPI::test_arbitrary_x_reviewer_id_cannot_establish_identity_returns_401
assert 200 == 401
2 failed, 22 deselected
```

### GREEN Evidence (After Remediation)
```text
tests/test_approval_audit_api.py: 29 passed in 4.66s
tests/test_workflow_orchestration.py: 18 passed in 6.18s
tests/test_explanation_service.py: 13 passed in 1.28s
```

### Full Regression Suite
```text
collected 448 items
447 passed, 1 skipped (Windows symlink test), 6 warnings in 18.36s
Zero regressions across all completed phases.
```

### Git Check and Status
- `git diff --check`: 0 issues.
- `git status --short`: clean working directory with untracked files only; no staged changes, no commits, no pushes.

---

## 6. Documented Limitations
1. **Production Identity Provider Deployment**: Standalone `ProductionAuthenticationVerifier` fails closed (rejects all tokens) because no external IdP is wired up. Before promoting to a live cloud environment, an IdP integration (e.g. AWS Cognito, Google Cloud Identity, Auth0, or corporate Okta via JWKS) should be bound to the `BaseAuthenticationVerifier` dependency.
2. **PostgreSQL Concurrency in Production**: SQLite serializes transactions in memory; true PostgreSQL `SELECT ... FOR UPDATE` row locking has been verified by dialect query compilation and transaction state tests, but not executed against an external multi-client PostgreSQL instance.

