# RBAC Frontend Matrix — YottaFlex Portfolio Rebalancing System

**Audit Date:** 2026-11-12  
**Target Architecture:** FastAPI Backend (`app/api/`), SQLAlchemy Models (`app/models/`), and Frontend RBAC Implementation (`frontend/src/`)

---

## 1. Executive Summary & Backend Verification

This document establishes the verified Role-Based Access Control (RBAC) matrix for the YottaFlex Portfolio Rebalancing System. It maps the four required business personas to authoritative backend roles, verified API endpoints, and permitted UI operations.

> [!IMPORTANT]
> **Authoritative Security Constraint:** Frontend route guards and role-aware navigation are usability enhancements. Authoritative security is enforced strictly by the FastAPI backend dependencies (`get_current_reviewer`, `PERMITTED_APPROVAL_ROLES`). The frontend never invents roles, claims, or permissions.

---

## 2. Authoritative Backend Roles & Capabilities

The backend authentication subsystem (`app/api/dependencies.py` and `app/services/approval/approval_service.py`) recognizes the following roles:

| Backend Role | Approval & Workflow Authority | Description / Permission Boundary |
|---|---|---|
| `ADMIN` | **Authorized** | Full administrative and governance authority. Can approve, reject, initiate workflows, and access diagnostics. |
| `REVIEWER` | **Authorized** | Fiduciary review authority. Permitted to approve and reject proposals, and inspect proposal-scoped audit trails. |
| `COMPLIANCE_OFFICER` | **Authorized** | Compliance authority recognized by `PERMITTED_APPROVAL_ROLES`. Can execute approval/rejection decisions and inspect audit trails. |
| `PORTFOLIO_MANAGER` | **Authorized** | Operational investment authority recognized by `PERMITTED_APPROVAL_ROLES`. Can initiate rebalancing workflows and evaluate drift. |
| `VIEWER` | **Forbidden (HTTP 403)** | Read-only observation. Rejection by `get_current_reviewer` on all approval and workflow execution endpoints. |

### Development Mock Authentication Tokens (`ENABLE_DEV_MOCK_AUTH=True`)
When running in development mode, the backend provides three standard mock reviewer contexts:
1. `dev-admin-token` &rarr; Role: `ADMIN`, ID: `REV-DEV-ADMIN`, Email: `dev.admin@firm.com`
2. `dev-reviewer-token` &rarr; Role: `REVIEWER`, ID: `REV-DEV-01`, Email: `dev.reviewer@firm.com`
3. `dev-viewer-token` &rarr; Role: `VIEWER`, ID: `REV-DEV-VIEWER`, Email: `dev.viewer@firm.com`

---

## 3. Business Persona to Backend Role Mapping

| Business Persona | Mapped Backend Role | Primary Business Objective | UI Workspace Access |
|---|---|---|---|
| **Customer / Account Holder** | `VIEWER` | View personal portfolio market value, holdings, current vs. target allocation, drift status, and latest recommendation summary. | Customer Portal (`/customer/overview`, `/customer/holdings`, `/customer/recommendations`, `/customer/activity`) |
| **Operations Analyst** | `PORTFOLIO_MANAGER` (or `ADMIN` in dev) | Analyze portfolio drift, inspect positions, generate deterministic rebalancing recommendations, and simulate post-trade allocations. | Analyst Workspace (`/analyst/dashboard`, `/analyst/portfolios`, `/analyst/drift`, `/analyst/proposals`) |
| **Risk / Compliance Reviewer** | `REVIEWER` (or `COMPLIANCE_OFFICER` / `ADMIN`) | Independent governance review of proposed rebalance orders against investor IPS constraints; approve, reject with mandatory reason, and inspect audit logs. | Compliance Desk (`/compliance/queue`, `/compliance/proposals/:id`, `/compliance/policy-checks`, `/compliance/audit`) |
| **System Administrator** | `ADMIN` | Operational oversight, backend connectivity health verification, reference data validation, and technical diagnostics. | Administration Console (`/admin/overview`, `/admin/reference-data`, `/admin/data-quality`, `/admin/diagnostics`) |

---

## 4. Feature & API Permission Matrix

| Feature / Business Action | Required Backend Role | Backend Endpoint | HTTP Method | Customer (`VIEWER`) | Analyst (`PORTFOLIO_MANAGER`) | Reviewer (`REVIEWER`) | Admin (`ADMIN`) |
|---|---|---|---|:---:|:---:|:---:|:---:|
| **Portfolio Valuation** | Any / Open | `/api/v1/portfolios/{id}/valuation` | `GET` | ✅ Read | ✅ Read | ✅ Read | ✅ Read |
| **Portfolio Drift Analysis** | Any / Open | `/api/v1/portfolios/{id}/drift` | `GET` | ✅ Read | ✅ Read | ✅ Read | ✅ Read |
| **Generate Proposal** | Open / System | `/api/v1/portfolios/{id}/rebalance/proposals` | `POST` | ❌ Blocked | ✅ Create | ❌ Read-Only | ✅ Create |
| **Run Orchestrated Workflow** | Permitted Roles | `/api/v1/workflows` | `POST` | ❌ 403 Forbidden | ✅ Execute | ❌ Read-Only | ✅ Execute |
| **Query Workflow Details** | Open / System | `/api/v1/workflows/{id}` | `GET` | ✅ Read | ✅ Read | ✅ Read | ✅ Read |
| **Approve Proposal** | Permitted Roles | `/api/v1/proposals/{id}/approve` | `POST` | ❌ 403 Forbidden | ❌ Disallowed (Dual-Key) | ✅ Approve | ✅ Approve |
| **Reject Proposal** | Permitted Roles | `/api/v1/proposals/{id}/reject` | `POST` | ❌ 403 Forbidden | ❌ Disallowed (Dual-Key) | ✅ Reject | ✅ Reject |
| **Proposal Audit Trail** | Open / System | `/api/v1/proposals/{id}/audit` | `GET` | ✅ Read-Own | ✅ Read | ✅ Read | ✅ Read |
| **Policy Semantic Search** | Open / System | `/api/v1/policies/search` | `POST` | ❌ Hidden | ✅ Search | ✅ Search | ✅ Search |
| **Policy Grounded Q&A** | Open / System | `/api/v1/policies/ask` | `POST` | ❌ Hidden | ✅ Query | ✅ Query | ✅ Query |
| **System Health Diagnostics**| Open / System | `/health` | `GET` | ❌ Hidden | ❌ Hidden | ❌ Hidden | ✅ Inspect |
| **User Management** | *Unsupported* | None | — | ❌ Unsupported | ❌ Unsupported | ❌ Unsupported | ❌ Unsupported |

---

## 5. Documented Gaps & Unsupported Capabilities

In strict adherence to the project guidelines, the following capabilities are documented as unsupported by the existing backend and are NOT fabricated:
1. **No User Administration Endpoints (`/api/v1/users`):** The backend does not provide user creation, password management, or role assignment endpoints. All identities are supplied via external IdP Bearer tokens or development mock tokens.
2. **No Multi-Portfolio List Endpoint (`GET /api/v1/portfolios`):** The backend queries portfolios strictly by `portfolio_id`. Portfolios are selected via verified portfolio references.
3. **No Global Audit Feed (`GET /api/v1/audit`):** Audit records are strictly proposal-scoped (`/api/v1/proposals/{id}/audit`). A global system-wide activity log does not exist in the backend.
4. **No Customer-Specific Auth Scope:** The backend treats all Bearer tokens as `ReviewerContext`. The Customer persona is safely realized using the `VIEWER` role with mutation actions blocked and scoped to read-only portfolio analysis.
