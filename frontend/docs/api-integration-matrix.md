# API Integration Matrix — YottaFlex Frontend

**Audit & Maintenance Date:** 2026-11-12  
**FastAPI Version:** 0.1.0  
**Backend Base URLs:** Direct: `http://localhost:8000`, Vite Proxy: `/api` and `/health`

---

## 1. Verified API Endpoints

| Feature | Actor | Method | Verified Backend Path | Path / Query Parameters | Request Schema | Response Schema | Required Role | UI Usage | Status |
|---|---|---|---|---|---|---|---|---|---|
| **Portfolio Valuation** | Customer, Analyst, Reviewer, Admin | `GET` | `/api/v1/portfolios/{portfolio_id}/valuation` | `portfolio_id` (path, required), `as_of_date` (query, optional `YYYY-MM-DD`) | None | `PortfolioValuationResult` | None (Public) | `ValuationSummaryCards`, `HoldingsTable`, `AssetAllocationChart` | **Integrated** |
| **Portfolio Drift Analysis** | Customer, Analyst, Reviewer, Admin | `GET` | `/api/v1/portfolios/{portfolio_id}/drift` | `portfolio_id` (path, required), `as_of_date` (query, optional `YYYY-MM-DD`) | None | `PortfolioDriftResult` | None (Public) | `DriftAnalysis`, `TargetAllocationChart` | **Integrated** |
| **Rebalance Proposal Generation** | Analyst, Admin | `POST` | `/api/v1/portfolios/{portfolio_id}/rebalance/proposals` | `portfolio_id` (path, required), `as_of_date` (query, optional `YYYY-MM-DD`) | `CreateProposalRequest` (`{ as_of_date?: string }`) | `RebalanceProposalResponse` | None (Route level) | `ProposalGenerator`, `SimulatedAllocationMatrix`, `ProposedTradesTable` | **Ready for Integration** |
| **Workflow Run Initiation** | Analyst, Admin | `POST` | `/api/v1/workflows` | None | `WorkflowRequest` (`{ portfolio_id, request_key, as_of_date?, policy_query? }`) | `WorkflowResponse` | `PERMITTED_APPROVAL_ROLES` (`PORTFOLIO_MANAGER`, `ADMIN`, `REVIEWER`) | `WorkflowRunner`, `BusinessLifecycleStepper` | **Ready for Integration** |
| **Workflow Details Query** | Customer, Analyst, Reviewer, Admin | `GET` | `/api/v1/workflows/{workflow_id}` | `workflow_id` (path, required) | None | `WorkflowResponse` | None (Public) | `WorkflowTracker`, `RecommendationView` | **Ready for Integration** |
| **Proposal Approval** | Reviewer, Admin | `POST` | `/api/v1/proposals/{proposal_id}/approve` | `proposal_id` (path, required) | `ApproveProposalRequest` (`{ notes?: string }`) | `ApprovalDecisionResponse` | `REVIEWER`, `ADMIN`, `COMPLIANCE_OFFICER` | `ProposalApprovalDialog`, `ReviewDecisionBar` | **Ready for Integration** |
| **Proposal Rejection** | Reviewer, Admin | `POST` | `/api/v1/proposals/{proposal_id}/reject` | `proposal_id` (path, required) | `RejectProposalRequest` (`{ reason: string }` - non-empty) | `ApprovalDecisionResponse` | `REVIEWER`, `ADMIN`, `COMPLIANCE_OFFICER` | `ProposalRejectionModal`, `ReviewDecisionBar` | **Ready for Integration** |
| **Proposal Audit Trail** | Customer, Analyst, Reviewer, Admin | `GET` | `/api/v1/proposals/{proposal_id}/audit` | `proposal_id` (path, required) | None | `AuditListResponse` (`{ events: AuditEventResponse[], total_count: number }`) | None (Public) | `ProposalAuditTrail`, `ComplianceAuditLog` | **Ready for Integration** |
| **Policy Semantic Search** | Analyst, Reviewer, Admin | `POST` | `/api/v1/policies/search` | None | `PolicySearchRequest` (`{ query: string, top_k?: number, similarity_threshold?: number }`) | `PolicySearchResponse` | None (Public) | `PolicySearchInspector` | **Ready for Integration** |
| **Policy Grounded Q&A** | Analyst, Reviewer, Admin | `POST` | `/api/v1/policies/ask` | None | `PolicyAskRequest` (`{ query: string }`) | `PolicyAskResponse` | None (Public) | `CompliancePolicyAssistant` | **Ready for Integration** |
| **System Health Check** | Admin, Development | `GET` | `/health` | None | None | `{ status: "healthy" }` | None (Public) | `SystemDiagnosticsTab`, `StatusBanner` | **Integrated** |

---

## 2. Unsupported Endpoints

| Requested Feature | Hypothesized Endpoint | Actual Backend Reality | Handling Strategy |
|---|---|---|---|
| User Management / Role Assignment | `GET/POST /api/v1/users` | Does not exist | Disclose as unsupported; identity derived via external IdP token |
| Multi-Portfolio Worklist | `GET /api/v1/portfolios` | Does not exist | Scoped to verified portfolio identifiers (e.g. `PORT-INV-000001-02`, `PORT-API-01`) |
| Global Audit Log Feed | `GET /api/v1/audit` | Does not exist | Scoped to proposal audit events (`/api/v1/proposals/{id}/audit`) |
| Instrument CRUD | `POST/PUT /api/v1/instruments` | Does not exist | Static reference inspection; mutations not supported |
