# Phase 6 — Agentic Workflow Engine and Persistence

## Objective
Orchestrate the deterministic portfolio workflow through persisted, traceable workflow runs.

## Consolidated scope
- Audit the existing service contracts and request flow before designing orchestration.
- Define persisted workflow runs, statuses and lifecycle transitions.
- Implement a workflow context that carries portfolio, date, analytics, recommendations, policy evidence, simulation and findings between steps.
- Coordinate existing analytics, rebalancing, constraint and policy-retrieval services.
- Use explicit state transitions rather than hidden agent decisions.
- Make workflow initiation idempotent where required.
- Handle partial failures and retries without duplicating proposals/trades.
- Persist enough information to reconstruct the workflow result.

## Architecture principles
- Reuse existing services; do not duplicate financial calculations.
- Keep deterministic business decisions in ordinary application services.
- Use the LLM only for grounded explanation, not trade generation, constraint evaluation or approval.
- Keep workflow state and audit history explicit.
- Preserve transaction boundaries and existing API conventions.

## Verification
Test valid transitions, invalid transitions, idempotent requests, failure recovery, persistence/reconstruction, policy retrieval integration and audit-history consistency.
