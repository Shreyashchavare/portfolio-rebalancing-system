# System Overview

## Architecture

YottaFlex is a modular FastAPI backend with a React, TypeScript and Vite frontend. The backend separates deterministic financial calculations, policy retrieval, workflow orchestration, persistence and governance.

- **Frontend:** role-based workspaces for customers, analysts, reviewers and administrators.
- **API:** FastAPI routes under `/api/v1`.
- **Domain services:** portfolio valuation, drift analysis, rebalancing, fee calculation, trade simulation and constraint checks.
- **Policy RAG:** policy documents are chunked, embedded and retrieved for grounded compliance explanations. Ollama (`llama3.2`) can generate narrative explanations; deterministic evidence-based fallback is available.
- **Persistence:** SQLAlchemy relational database; PostgreSQL is the deployment target, with SQLite supported for local demos.
- **Governance:** workflow state transitions, human approval/rejection and append-only audit records.

## Main workflow

1. Select a portfolio and calculate its point-in-time valuation.
2. Compare current holdings with target allocations and calculate drift.
3. Generate proposed buy/sell orders using deterministic financial rules.
4. Simulate trades and evaluate fees, cash solvency and portfolio constraints.
5. Retrieve policy evidence and prepare a grounded explanation.
6. Send the proposal to the human review gate.
7. An authorized reviewer approves or rejects it; the decision is recorded in the audit trail.

No step sends orders to a live broker.

## Core data

The relational model covers investor profiles, portfolios, instruments, holdings, market prices, target allocations, fee schedules, constraints and constraint-instrument mappings. It also stores rebalance proposals, trades, policy documents/chunks, workflow runs and audit events.

Key invariants:
- Financial calculations use decimal values and deterministic rules.
- Allocation and constraint checks are evaluated before a proposal is eligible for review.
- Proposal statuses include `DRAFT`, `PENDING_REVIEW`, `APPROVED` and `REJECTED`.
- Approval/rejection is restricted to authorized reviewer roles; viewers are read-only.
- Audit events are append-only. A pending proposal may correctly have no decision event yet.
- Workflow requests use idempotency keys to prevent duplicate processing.

## Main API routes

| Capability | Route |
|---|---|
| Portfolio valuation | `GET /api/v1/portfolios/{id}/valuation` |
| Portfolio drift | `GET /api/v1/portfolios/{id}/drift` |
| Create proposal | `POST /api/v1/proposals` |
| Read proposal | `GET /api/v1/proposals/{id}` |
| Approve / reject | `POST /api/v1/proposals/{id}/approve` / `reject` |
| Proposal audit | `GET /api/v1/proposals/{id}/audit` |
| Run workflow | `POST /api/v1/workflows` |
| Read workflow | `GET /api/v1/workflows/{id}` |
| Policy search / ask | `/api/v1/policies` routes |

Use `/docs` for current request and response schemas.

## Roles and security

The system distinguishes customer/viewer, analyst/portfolio manager, reviewer/compliance and administrator responsibilities. The backend is the authority for authorization; frontend controls are not a security boundary. Development mock authentication is permitted only in development/test environments. Production must reject mock authentication and unverified tokens.
