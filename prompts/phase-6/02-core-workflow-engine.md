# Phase 6.1 — Core Workflow Engine and Persistence

## Project
YottaFlex Portfolio Rebalancing System

Repository:
`E:\Yottaflex\portfolio-rebalancing-system`

## Objective

Implement a deterministic, testable workflow orchestration foundation that coordinates the existing Phase 3 Portfolio Analytics, Phase 4 Rebalancing Engine and Phase 5 Policy RAG services.

This batch must not implement LLM-based agent reasoning, explanation generation, human approval APIs or trade execution.

Target completion: 90 minutes.
Hard limit: 120 minutes.

Correctness, financial safety and regression tests take priority over the time target.

---

## 1. Mandatory first step: inspect the actual repository

Before implementation:

- Read `prompts/phase-6/01-orchestration-architecture-audit.md`.
- Inspect the current models, schemas, services, database session conventions and tests.
- Verify exact existing public method signatures.
- Inspect the existing proposal lifecycle.
- Inspect the current transaction and exception-handling behavior.
- Do not assume method signatures from previous design examples.

Reuse existing services and conventions.

Do not rewrite Phase 3, 4 or 5 functionality.

## 2. TDD requirements

Follow this sequence internally:

1. Write behavioral tests first.
2. Run the targeted tests and demonstrate RED.
3. Implement the minimum functionality.
4. Run targeted tests and demonstrate GREEN.
5. Run the complete regression suite.
6. Review transaction boundaries, idempotency and financial safety.
7. Run `git diff --check`.

Do not skip RED or GREEN evidence.

## 3. Workflow persistence

Implement a SQLAlchemy `WorkflowRun` model only after confirming it is necessary and compatible with existing model conventions.

Proposed fields:

- id: unique workflow identifier.
- portfolio_id: foreign key to portfolio.
- proposal_id: nullable foreign key to rebalance proposal.
- status: validated workflow status.
- request_key: idempotency key.
- request_payload: validated request metadata.
- result_payload: structured result metadata.
- error_code: safe error classification.
- error_message: sanitized diagnostic.
- started_at.
- completed_at.
- created_at.
- updated_at.

Requirements:

- Add appropriate foreign keys and indexes.
- Add a database uniqueness constraint for the correctly scoped idempotency key.
- Use JSON/JSONB consistently with existing database conventions.
- Maintain SQLite test compatibility.
- Avoid storing secrets or unnecessary raw LLM prompts.
- Follow the existing model export and import conventions.
- Do not add reviewer_id to RebalanceProposal in this batch.

If an existing model already supports the required behavior, reuse it instead of creating a duplicate.

## 4. Workflow status and State pattern

Implement a typed workflow status enum.

Proposed states:

- RECEIVED
- VALIDATING
- ANALYZING
- GENERATING_PROPOSAL
- RETRIEVING_POLICIES
- GENERATING_EXPLANATION
- PENDING_HUMAN_REVIEW
- APPROVED
- REJECTED
- COMPLETED
- FAILED
- REQUIRES_ATTENTION

Define an explicit allowed-transition map.

Requirements:

- Reject invalid transitions.
- Reject transitions from terminal states.
- Never permit a rejected proposal to become approved.
- Do not allow a hard-blocked proposal to become an approvable proposal through workflow transitions.
- Keep workflow status separate from existing RebalanceProposal status.
- Handle policy and LLM failures according to the established safety rules.

Use a centralized transition validator. Do not create unnecessary classes for every state.

## 5. WorkflowContext

Implement a typed context containing the information required to execute the workflow.

Expected information:

- workflow_id
- portfolio_id
- as_of_date
- analytics_result
- proposal_id
- proposal_result
- policy_evidence
- constraint_findings
- warnings
- errors
- requires_human_review

Use existing Pydantic schemas where possible.

Do not put a live SQLAlchemy session or unrestricted database access inside the context.

Do not duplicate financial calculations or proposal generation logic.

## 6. Workflow orchestration

Implement the minimum required components:

- WorkflowService
- WorkflowExecutor
- WorkflowContext
- WorkflowStatus
- Workflow transition validator

Use constructor/dependency injection consistent with existing project conventions.

The workflow must coordinate:

1. Request validation.
2. Portfolio analytics.
3. Deterministic proposal generation and persistence.
4. Policy evidence retrieval.
5. Structured workflow result persistence.

The workflow must call the existing `PortfolioAnalyticsService`, `RebalancingService` and `PolicyRAGService` through their verified public interfaces.

Important: reuse the actual proposal returned by the existing rebalancing service. Never call proposal generation twice for the same workflow.

Do not introduce an unrestricted autonomous agent or arbitrary tool execution.

## 7. Idempotency and failure handling

This is a critical requirement.

Implement safe duplicate-request handling.

Requirements:

- Repeated requests with the same idempotency key and equivalent request data must not create duplicate proposals.
- Reusing an idempotency key with different request data must be rejected.
- Use a database uniqueness constraint and appropriate transaction handling.
- Do not rely only on an in-memory dictionary.
- Handle concurrent duplicate requests safely.
- Do not rerun proposal generation when resuming an existing workflow.
- Preserve a persisted proposal if a later policy retrieval step fails.
- Record a safe workflow failure or attention state.
- Never silently create a second proposal after a partial failure.

If safe resumability cannot be implemented within this batch, explicitly document the limitation and ensure the workflow cannot accidentally duplicate proposal creation.

## 8. Policy retrieval integration

Use the existing PolicyRAGService method and its real request/response contracts.

Requirements:

- Pass the workflow's exact as-of date.
- Preserve policy family, version and effective-date metadata.
- Preserve citation identifiers.
- Capture policy-family conflicts and retrieval warnings.
- Do not treat missing policy evidence as policy compliance.
- Do not invent policy constraints.
- Do not modify the existing RAG implementation.

If policy retrieval fails after proposal creation, retain the proposal and record the workflow's policy-verification failure. Do not silently proceed as though policy verification succeeded.

## 9. Audit history scope

Do not implement the complete AuditService or approval history in this batch.

If workflow transition history is essential for reliable execution, implement only the minimum append-only event persistence needed for workflow transitions.

Otherwise defer AuditEvent and AuditService to Batch 6.3.

Do not introduce duplicate audit mechanisms.

## 10. Testing requirements

Add focused tests covering:

### Workflow lifecycle
- Initial workflow creation.
- Valid transitions.
- Invalid transitions.
- Terminal-state protection.
- Failed workflow handling.

### Service integration
- Analytics invoked correctly.
- Proposal generation invoked exactly once.
- Policy retrieval receives the correct as-of date.
- Workflow result references the correct proposal.
- Existing proposal statuses remain consistent.

### Idempotency
- Same request key and same payload.
- Same request key and different payload.
- Duplicate requests do not generate additional proposals.
- Concurrent duplicate request protection where practical.

### Failure handling
- Analytics failure.
- Proposal-generation failure.
- Policy retrieval failure after proposal creation.
- Database transaction failure.
- Safe error persistence.
- No duplicate proposal on retry.

### Financial safety
- Existing holdings are not modified by orchestration.
- No financial calculations are duplicated.
- No hard constraint is bypassed.
- No blocked proposal is made approvable.
- Existing proposal and trade statuses are preserved.

Use mocks for service orchestration unit tests and existing database test fixtures for persistence tests.

Do not replace meaningful integration tests with mocks.

## 11. Scope restrictions

Do not:

- Modify the deterministic financial calculation algorithms.
- Rewrite PortfolioAnalyticsService.
- Rewrite RebalancingService.
- Rewrite PolicyRAGService.
- Add LLM agent reasoning.
- Add explanation generation.
- Add approval APIs.
- Add reviewer_id.
- Add real trade execution.
- Introduce LangGraph.
- Introduce Kafka or RabbitMQ.
- Introduce microservices.
- Add unnecessary abstractions.
- Change dependencies without demonstrated necessity.
- Apply migrations to a live database.
- Modify unrelated Phase 0–5 functionality.

## 12. Prompt history

Save this exact implementation prompt as:

`prompts/phase-6/02-core-workflow-engine.md`

Include a concise execution record:
- RED test evidence.
- GREEN test evidence.
- Full regression result.
- Files created or modified.
- Known limitations.

Do not create a separate global policy document.

## 13. Final report

Report:

1. Implemented components.
2. Exact public interfaces and method signatures.
3. Workflow state transitions.
4. Idempotency implementation.
5. Transaction and failure-handling behavior.
6. Tests demonstrating RED and GREEN.
7. Full regression result.
8. Files created or modified.
9. `git diff --check` result.
10. Remaining limitations and risks.
11. Actual elapsed time.

Do not commit or push.

Stop after Batch 6.1. Wait for code review before proceeding to Batch 6.2.


---

# Execution Record

## 1. RED Test Evidence
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.4.2, pluggy-1.7.0 -- E:\Yottaflex\portfolio-rebalancing-system\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: E:\Yottaflex\portfolio-rebalancing-system
configfile: pytest.ini
plugins: anyio-4.16.0
collecting ... collected 0 items / 1 error

=================================== ERRORS ====================================
____________ ERROR collecting tests/test_workflow_orchestration.py ____________
ImportError while importing test module 'E:\Yottaflex\portfolio-rebalancing-system\tests\test_workflow_orchestration.py'.
Traceback:
tests\test_workflow_orchestration.py:33: in <module>
    from app.models.workflow_run import WorkflowRun
E   ModuleNotFoundError: No module named 'app.models.workflow_run'
=========================== short test summary info ===========================
ERROR tests/test_workflow_orchestration.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
============================== 1 error in 0.54s ===============================
```

## 2. GREEN Test Evidence
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.4.2, pluggy-1.7.0 -- E:\Yottaflex\portfolio-rebalancing-system\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: E:\Yottaflex\portfolio-rebalancing-system
configfile: pytest.ini
plugins: anyio-4.16.0
collecting ... collected 18 items

tests/test_workflow_orchestration.py::TestWorkflowStateMachine::test_workflow_status_enum_values PASSED [  5%]
tests/test_workflow_orchestration.py::TestWorkflowStateMachine::test_valid_transitions_pipeline PASSED [ 11%]
tests/test_workflow_orchestration.py::TestWorkflowStateMachine::test_invalid_transitions_rejected PASSED [ 16%]
tests/test_workflow_orchestration.py::TestWorkflowStateMachine::test_terminal_state_protection PASSED [ 22%]
tests/test_workflow_orchestration.py::TestWorkflowStateMachine::test_rejected_proposal_cannot_transition_to_approved PASSED [ 27%]
tests/test_workflow_orchestration.py::TestWorkflowPersistence::test_workflow_run_table_and_persistence PASSED [ 33%]
tests/test_workflow_orchestration.py::TestWorkflowPersistence::test_idempotency_database_unique_constraint PASSED [ 38%]
tests/test_workflow_orchestration.py::TestWorkflowOrchestrationService::test_orchestration_executes_pipeline_end_to_end PASSED [ 44%]
tests/test_workflow_orchestration.py::TestWorkflowOrchestrationService::test_proposal_generation_invoked_exactly_once PASSED [ 50%]
tests/test_workflow_orchestration.py::TestWorkflowOrchestrationService::test_proposal_with_hard_violations_transitions_to_rejected PASSED [ 55%]
tests/test_workflow_orchestration.py::TestWorkflowIdempotency::test_same_request_key_same_payload_returns_existing_run_without_duplicate PASSED [ 61%]
tests/test_workflow_orchestration.py::TestWorkflowIdempotency::test_same_request_key_different_payload_is_rejected PASSED [ 66%]
tests/test_workflow_orchestration.py::TestWorkflowFailureHandling::test_analytics_failure_marks_workflow_failed PASSED [ 72%]
tests/test_workflow_orchestration.py::TestWorkflowFailureHandling::test_policy_retrieval_failure_preserves_persisted_proposal PASSED [ 77%]
tests/test_workflow_orchestration.py::TestWorkflowFailureHandling::test_financial_safety_holdings_are_never_mutated PASSED [ 83%]
tests/test_workflow_orchestration.py::TestWorkflowFailureHandling::test_missing_policy_evidence_does_not_fail_workflow_but_flags_human_review PASSED [ 88%]
tests/test_workflow_orchestration.py::TestWorkflowFailureHandling::test_proposal_generation_failure_marks_workflow_failed_without_proposal PASSED [ 94%]
tests/test_workflow_orchestration.py::TestWorkflowFailureHandling::test_concurrent_integrity_error_during_initialization_recovers_gracefully PASSED [100%]

============================= 18 passed in 1.88s ==============================
```

## 3. Full Regression Test Result
```text
================= 405 passed, 1 skipped, 5 warnings in 11.73s =================
```

## 4. Files Created or Modified
### Created
- `app/models/workflow_run.py`: SQLAlchemy `WorkflowRun` entity with `UniqueConstraint("portfolio_id", "request_key")` and status `CheckConstraint`.
- `app/schemas/orchestration.py`: `WorkflowStatus`, `WorkflowRequest`, `WorkflowResponse`, custom error hierarchy (`IdempotencyConflictError`, `InvalidStateTransitionError`, `WorkflowExecutionError`).
- `app/services/orchestration/workflow_state.py`: Centralized transition map, terminal protection, financial safety guard preventing approval of rejected proposals.
- `app/services/orchestration/workflow_context.py`: Strongly typed `WorkflowContext` data bag carrying execution metadata across steps.
- `app/services/orchestration/workflow_executor.py`: Step-level coordinator for portfolio validation, analytics, proposal creation, and policy retrieval.
- `app/services/orchestration/workflow_service.py`: Public entrypoint with idempotency enforcement, state transitions, transaction management, and safe error persistence.
- `app/services/orchestration/__init__.py`: Package export interface.
- `tests/test_workflow_orchestration.py`: 18 behavioral unit/integration tests covering lifecycle, idempotency, failure modes, and financial safety.

### Modified
- `app/models/__init__.py`: Exported `WorkflowRun`.
- `app/schemas/__init__.py`: Exported orchestration schemas and error classes.
- `app/services/__init__.py`: Exported `WorkflowService`, `WorkflowExecutor`, `WorkflowContext`, etc.

## 5. Known Limitations
1. **REST Endpoints**: FastAPI routes (`/api/v1/workflows`) and dependency injection are intentionally deferred to Batch 6.3.
2. **LLM Explanations**: Grounded narrative explanations and citation synthesis are intentionally deferred to Batch 6.2.
3. **Approval Lifecycle & Audit Events**: Human review decisions (`APPROVED`/`REJECTED`) and append-only `AuditEvent` logging are intentionally deferred to Batch 6.3.
4. **PostgreSQL Migration**: DDL migration script `003_add_orchestration_and_audit_tables.sql` will be authored in Batch 6.4. SQLite in-memory DDL is validated via `Base.metadata.create_all`.
