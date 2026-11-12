# Phase 3 — Simplified, Role-Based Financial Frontend Report

**Project:** YottaFlex — Policy-Constrained Portfolio Rebalancing System  
**Date:** November 12, 2026  
**Status:** Completed  
**Frontend Verification:** 57/57 Vitest Tests Passing (9 test files) | 0 TypeScript Errors | 0 ESLint Warnings  
**Backend Verification:** 507/507 Pytest Passing (100% pass rate in 35.34s)  

---

## Executive Summary

Phase 3 successfully refactored and completed the YottaFlex React + TypeScript frontend into an institutional-grade, role-based financial web application. The frontend integrates directly with the FastAPI backend without synthetic mocks, enforces backend role-based access control (RBAC), supports dual theme modes (Light, Dark, System), provides 4 distinct persona-tailored workspaces, and implements all 16 essential financial and governance capabilities required by the specification.

Importantly, no backend contracts, database schemas, seed data, or business calculation rules were altered. All financial calculations (valuations, drifts, lot-size rounding, tiered fees, cash solvency constraints, trade simulations, and immutable audit logs) remain deterministic and authoritative.

---

## 1. Final Frontend Architecture

### 1.1 Technology Stack & Core Libraries

- **Framework:** React 18.3.1 with TypeScript 5.6.3
- **Build & Development Server:** Vite 6.4.6 with native ESM fast refresh and reverse proxy configurations
- **Styling & Design System:** Tailwind CSS 3.4.17 with CSS variable tokens, class-based dark mode (`darkMode: 'class'`), and typography plugins
- **Server State & Data Fetching:** TanStack React Query v5.62.11 with automatic query deduplication, background re-validation, cache invalidation, and mutation lifecycles
- **Client Routing:** React Router v6.28.0 supporting nested layout routes, index fallbacks, and role/persona route guards (`ProtectedRoute`)
- **Iconography:** Lucide React 0.468.0
- **Data Visualizations:** Recharts 2.15.0 with dynamic SVG styling adapted to active theme tokens
- **Testing:** Vitest 2.1.9, JSDOM, React Testing Library, and `@testing-library/jest-dom`

### 1.2 Directory & Module Organization

```
frontend/src/
├── app/
│   ├── layouts/
│   │   ├── AppLayout.tsx         # Main shell container with header, sidebar, and error boundaries
│   │   ├── Header.tsx            # Sticky header with persona switcher, reviewer role selector, theme toggle
│   │   └── Sidebar.tsx           # Collapsible, role-tailored navigation bar
│   ├── providers/
│   │   ├── AuthContext.ts        # Institutional auth & RBAC context definitions
│   │   ├── AuthProvider.tsx      # Multi-persona & reviewer role state provider with persistence
│   │   ├── QueryProvider.tsx     # TanStack QueryClient provider with 30s stale time defaults
│   │   ├── ThemeContext.ts       # Theme state definition (Light, Dark, System)
│   │   └── ThemeProvider.tsx     # HTML root class synchronizer with OS media query listener
│   └── router/
│       └── index.tsx             # Unified router with public, core, and role-protected routes
├── components/
│   ├── auth/
│   │   └── ProtectedRoute.tsx    # Declarative route guard evaluating backend roles & persona tiers
│   ├── business/
│   │   ├── BusinessWorkflowLifecycle.tsx # 8-stage visual rebalancing lifecycle state stepper
│   │   ├── ProposalAuditHistory.tsx      # Chronological immutable audit trail component (GET /audit)
│   │   └── ProposalDetailsCard.tsx       # Rebalance order breakdown, simulation, and approve/reject actions
│   ├── feedback/
│   │   ├── EmptyState.tsx        # High-clarity empty state placeholders with actions
│   │   ├── ErrorBoundary.tsx     # React component boundary catching unhandled rendering exceptions
│   │   └── StatusBanner.tsx      # Institutional status notices
│   └── ui/
│       ├── Alert.tsx             # Semantic alert banners (info, success, warning, error)
│       ├── Badge.tsx             # Compact status and taxonomy pills
│       ├── Button.tsx            # Accessible buttons with loading spinners and icon adornments
│       ├── Card.tsx              # Surface containers with standardized headers and footers
│       ├── DataTable.tsx         # Generic typed financial data table with sorting and column alignments
│       ├── FinancialMetricCard.tsx # KPI summary card with accent borders and trend badges
│       ├── Modal.tsx             # Accessible dialog with backdrop and escape key dismissal
│       ├── SearchInput.tsx       # Debounced filter search input
│       ├── Skeleton.tsx          # Pulse placeholder loaders
│       ├── Tabs.tsx              # Tab navigation component
│       └── ThemeSelector.tsx     # Segmented theme control (Light / Dark / System)
├── features/
│   ├── admin/
│   │   └── AdminWorkspace.tsx    # System admin console (health, reference data, audit, diagnostics)
│   ├── analyst/
│   │   └── AnalystWorkspace.tsx  # Operations desk (drift analysis, proposal generator, simulation)
│   ├── approvals/
│   │   └── ApprovalsPage.tsx     # Mandatory human review queue, approve/reject modal, audit logger
│   ├── common/
│   │   ├── NotFoundPage.tsx      # 404 Route handling
│   │   └── UnauthorizedPage.tsx  # 403 Forbidden screen with role guidance
│   ├── compliance/
│   │   └── ComplianceWorkspace.tsx # Policy review queue, FastEmbed Q&A, and exception tracking
│   ├── customer/
│   │   └── CustomerWorkspace.tsx # Personal portfolio valuation, allocations, drift, and explanations
│   ├── dashboard/
│   │   └── DashboardPage.tsx     # Dynamic dispatcher rendering role-specific workspace per persona
│   ├── policies/
│   │   └── PoliciesPage.tsx      # Grounded FastEmbed ONNX Q&A and vector similarity search workbench
│   ├── portfolios/
│   │   ├── components/           # Holdings table, drift analysis, charts, metrics, selector
│   │   ├── hooks/                # usePortfolios, usePortfolioValuation, usePortfolioDrift
│   │   ├── services/             # portfolioService API abstractions
│   │   ├── types/                # portfolio TypeScript interfaces
│   │   └── PortfoliosPage.tsx    # Comprehensive portfolio valuation and drift analysis explorer
│   ├── rebalancing/
│   │   └── RebalancingPage.tsx   # Live proposal generation engine, lot rounding, simulation, gatekeeper
│   ├── settings/
│   │   └── SettingsPage.tsx      # Role switcher, theme customization, and API connection status
│   └── workflows/
│       └── WorkflowsPage.tsx     # State machine orchestration monitor & pipeline initiation
├── hooks/
│   ├── useApprovals.ts           # useApproveProposal, useRejectProposal, useProposalAudit
│   ├── useAuth.ts                # useAuth consumer hook
│   ├── useHealth.ts              # useHealth backend health check query hook
│   ├── useRebalancing.ts         # useCreateProposal mutation hook
│   └── useTheme.ts               # useTheme consumer hook
├── services/
│   └── api/
│       ├── approvalService.ts    # POST /approve, POST /reject, GET /audit
│       ├── client.ts             # Axios-based typed HTTP client with bearer tokens & error normalizer
│       ├── endpoints.ts          # Centralized API URI registry
│       ├── health.ts             # GET /health
│       ├── policyService.ts      # POST /policies/ask, POST /policies/search
│       ├── rebalancingService.ts # POST /portfolios/{id}/rebalance/proposals
│       └── workflowService.ts    # POST /workflows, GET /workflows/{id}
└── types/                        # Full Pydantic-to-TypeScript schema type definitions
```

### 1.3 State Management & Data Fetching Strategy

1. **Authentication & Persona State:** Controlled by `AuthProvider`, managing active institutional persona (`CUSTOMER`, `ANALYST`, `COMPLIANCE`, `ADMIN`) and active authenticated reviewer principal (`VIEWER`, `PORTFOLIO_MANAGER`, `REVIEWER`, `COMPLIANCE_OFFICER`, `ADMIN`). State is persisted in `localStorage` (`yottaflex_persona`, `yottaflex_reviewer`) to preserve session context across browser refreshes.
2. **Server State Caching:** Managed with TanStack React Query. Key query caches include:
   - `['portfolio', 'valuation', portfolioId, asOfDate]`
   - `['portfolio', 'drift', portfolioId, asOfDate]`
   - `['proposal', proposalId]`
   - `['audit', proposalId]`
   - `['health']`
   Mutation hooks (`useCreateProposal`, `useApproveProposal`, `useRejectProposal`) perform automatic invalidation of associated queries, ensuring real-time UI synchronicity.
3. **Local Component State:** Transient UI interactions (active tabs, modal open/close, custom portfolio ID typing, rejection reason inputs, Q&A prompts) are managed with React's native `useState` and `useCallback` hooks, preventing unnecessary re-renders.

---

## 2. Role-to-Screen Mapping

The frontend tailors both navigation menus and workspace dashboards to the active institutional role.

| Persona / Role | Accessible Screens | Role-Specific Dashboard | Permitted Actions | Restricted Actions |
|---|---|---|---|---|
| **Customer / Account Holder**<br>`CUSTOMER` (`VIEWER`) | • `/dashboard`<br>• `/portfolios`<br>• `/rebalancing`<br>• `/workflows`<br>• `/settings` | `CustomerWorkspace`<br>Personal portfolio overview, market valuation, asset class allocation vs targets, drift alerts, and rebalance rationales. | • View personal portfolio valuation.<br>• Inspect current vs target asset allocation.<br>• Review proposed rebalance orders.<br>• Read grounded plain-language explanations.<br>• Select light/dark themes. | • Cannot approve or reject proposals (HTTP 403 Forbidden).<br>• Cannot generate new rebalance proposals.<br>• Cannot access admin console (`/admin/*`).<br>• Cannot modify reference data or fee schedules. |
| **Operations Analyst**<br>`ANALYST` (`PORTFOLIO_MANAGER`) | • `/dashboard`<br>• `/portfolios`<br>• `/rebalancing`<br>• `/workflows`<br>• `/settings` | `AnalystWorkspace`<br>Multi-portfolio drift surveillance, trigger status monitoring, one-click proposal generation, and post-trade cash simulation. | • Select and value any institutional portfolio.<br>• Execute drift surveillance.<br>• Trigger rebalancing proposal generation (`POST /proposals`).<br>• Inspect lot-rounded orders & broker fee calculations.<br>• Verify pre-trade cash solvency & turnover buffers. | • Cannot approve proposals where compliance separation is mandated.<br>• Cannot modify system configurations or security policies. |
| **Risk / Compliance Reviewer**<br>`COMPLIANCE` (`REVIEWER` / `COMPLIANCE_OFFICER`) | • `/dashboard`<br>• `/approvals`<br>• `/policies`<br>• `/rebalancing`<br>• `/settings` | `ComplianceWorkspace`<br>Mandatory governance approval queue, hard constraint breach gatekeeper, FastEmbed policy citations, and audit logs. | • Inspect staged proposals awaiting review.<br>• Authorize and approve valid proposals (`POST /approve`).<br>• Reject non-compliant proposals with mandatory justification (`POST /reject`).<br>• Query policy corpus via FastEmbed ONNX RAG (`POST /policies/ask`).<br>• Inspect immutable audit event logs (`GET /audit`). | • Cannot bypass hard constraint violations.<br>• Cannot directly execute trades in live brokerage accounts.<br>• Cannot access system admin diagnostics. |
| **System Administrator**<br>`ADMIN` (`ADMIN`) | • All application screens:<br>`/dashboard`, `/portfolios`, `/rebalancing`, `/approvals`, `/policies`, `/workflows`, `/admin/*`, `/settings` | `AdminWorkspace`<br>System health probes, OAuth2 identity documentation, reference data catalogs, and data quality diagnostics. | • Probe backend service health (`GET /health`).<br>• Inspect reference data (instruments, price feeds, fee tiers).<br>• Override or approve proposals in governance queue.<br>• Run workflow state machine tests.<br>• Inspect application diagnostics. | • Strictly bound by deterministic financial rules (cannot force negative cash balance or violate database constraints). |

---

## 3. Role-to-Permission Mapping Based on Actual Backend Authorization

### 3.1 Source of Truth in Backend Dependencies

The backend authorization model defines permitted roles for governance signoffs in `app/api/v1/dependencies.py`:

```python
PERMITTED_APPROVAL_ROLES = {
    "REVIEWER",
    "ADMIN",
    "COMPLIANCE_OFFICER",
    "PORTFOLIO_MANAGER",
}
```

The role `VIEWER` is strictly excluded from `PERMITTED_APPROVAL_ROLES`.

### 3.2 Frontend Enforcement Architecture

1. **Route-Level Protection (`ProtectedRoute.tsx`):**
   - Routes like `/approvals`, `/compliance/*`, `/analyst/*`, and `/admin/*` verify that the active persona and reviewer role match the permitted set.
   - If unauthorized, users are smoothly redirected to `/unauthorized` with an explanatory message indicating their current role and which roles possess authorization.
2. **Component & Action-Level Gating (`useAuth` hook):**
   - Exposes boolean flags `canApprove`, `canSimulate`, `isAdmin`, `isCompliance`, `isAnalyst`, `isCustomer`.
   - In `ApprovalsPage.tsx` and `ProposalDetailsCard.tsx`, the "Approve Proposal" and "Reject Proposal" buttons are disabled and flagged with role-specific alert notices when `canApprove` is false.
3. **Backend HTTP 403 Handling:**
   - Even if client-side controls are bypassed, any approve/reject call executed under role `VIEWER` transmits the header `X-Reviewer-Role: VIEWER`, causing FastAPI to reject the request with `HTTP 403 Forbidden` (`{"detail": "Reviewer does not possess approval authority"}`).
   - The frontend error normalizer intercepts the 403 and renders a non-crashing alert explaining the permission rejection.
4. **Header Switcher for Operational Testing:**
   - The header provides an instantaneous persona dropdown (`Customer Portal`, `Analyst Desk`, `Compliance Desk`, `Admin Console`) and a reviewer role selector (`ADMIN`, `REVIEWER`, `PORTFOLIO_MANAGER`, `COMPLIANCE_OFFICER`, `VIEWER`). This enables verification of authorization boundaries without needing external login infrastructure.

---

## 4. Shared Components and Role-Specific Components

### 4.1 Shared UI Components (`frontend/src/components/ui/`)

- `Alert`: Semantic notice banners supporting 4 levels (info, success, warning, error) with Lucide icon adornments.
- `Badge`: Compact status and asset classification pills supporting variants (brand, success, warning, danger, neutral, navy).
- `Button`: Standardized accessible button supporting variants (primary, secondary, outline, ghost, danger), 3 sizes (sm, md, lg), loading spinners, and icon slots.
- `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`: Consistent rounded surface containers with subtle borders and dark-mode elevation.
- `DataTable`: Generic TypeScript table with custom cell rendering, column alignment (left, center, right), and empty-data state handling.
- `FinancialMetricCard`: High-density metric display card featuring large numeric values, trend/status badges, subtitles, and accent borders.
- `Modal`: Accessible dialog supporting focus trap, escape-to-close, title, description, and action footers.
- `SearchInput`: Debounced search filter input with search icon adornment and clear button.
- `Skeleton`: Shimmer pulse placeholder loader used across tables and chart cards during initial data fetching.
- `ThemeSelector`: Segmented control switching between Light, Dark, and System modes.

### 4.2 Shared Business Components (`frontend/src/components/business/`)

- `BusinessWorkflowLifecycle`: Comprehensive 8-stage visual pipeline stepper mapping each phase of the financial lifecycle (Portfolio Selection → Holdings Valuation → Drift Calculation → Trade Recommendation → Post-Trade Simulation → Compliance Review → Governance Decision → Immutable Audit Trail).
- `ProposalDetailsCard`: Comprehensive card breaking down proposed trades, pre/post trade cash values, tiered broker fees, constraint findings, and live approve/reject action modals.
- `ProposalAuditHistory`: Self-contained component connected to `useProposalAudit` that fetches and renders chronological audit records from `GET /api/v1/proposals/{id}/audit`.

### 4.3 Role-Specific Workspaces (`frontend/src/features/`)

- `CustomerWorkspace`: Non-administrative view focused on personal holdings, total valuation, asset class distribution, target corridor comparisons, and plain-language policy explanations.
- `AnalystWorkspace`: Multi-portfolio analysis desk equipped with drift surveillance tools, trigger thresholds, one-click proposal generation, and in-memory post-trade cash simulation.
- `ComplianceWorkspace`: Dedicated queue for pending proposals, automated constraint gatekeeper reports (highlighting HARD vs SOFT breaches), and FastEmbed ONNX policy Q&A.
- `AdminWorkspace`: Administrative overview featuring health check probes (`/health`), OAuth2 identity governance documentation, reference data catalogs, and data quality diagnostics.

---

## 5. API Integration Mapping

All frontend features integrate directly with backend REST API endpoints.

| Feature / Screen | Backend Endpoint | Method | Request Payload / Params | Response Data Utilized | Loading & Error States |
|---|---|---|---|---|---|
| **System Health**<br>(Admin & Header) | `/health` | `GET` | None | `{ status: "healthy", timestamp, version }` | Loading spinner on refresh button; `OFFLINE` badge on connection failure. |
| **Portfolio Valuation**<br>(Portfolios, Customer, Analyst, Rebalancing) | `/api/v1/portfolios/{id}/valuation` | `GET` | Query: `as_of_date` | `{ portfolio_id, total_market_value, positions: [...], asset_classes: [...] }` | Skeleton card placeholders during query; interactive retry button on network error. |
| **Portfolio Drift Analysis**<br>(Portfolios, Customer, Analyst, Rebalancing) | `/api/v1/portfolios/{id}/drift` | `GET` | Query: `as_of_date` | `{ drifts: [...], rebalance_trigger: { status, rebalance_required, triggered_asset_classes } }` | Inline drift percentage indicators; warning alert if rebalance required. |
| **Proposal Generation**<br>(Analyst, Rebalancing) | `/api/v1/portfolios/{id}/rebalance/proposals` | `POST` | Query: `as_of_date`<br>Body: `{}` | `{ proposal_id, status, trades: [...], simulation: {...}, constraint_findings: [...] }` | Disabled button with loading spinner; error alert banner displaying backend validation failures. |
| **Proposal Approval**<br>(Approvals, Compliance) | `/api/v1/proposals/{id}/approve` | `POST` | Headers: `X-Reviewer-Id`, `X-Reviewer-Role`<br>Body: `{ notes?: string }` | `{ proposal_id, status: "APPROVED", reviewer_id, reviewed_at }` | Confirmation modal; success banner with audit timestamp; 403 handling for VIEWER role. |
| **Proposal Rejection**<br>(Approvals, Compliance) | `/api/v1/proposals/{id}/reject` | `POST` | Headers: `X-Reviewer-Id`, `X-Reviewer-Role`<br>Body: `{ reason: string }` | `{ proposal_id, status: "REJECTED", reviewer_id, reviewed_at, review_reason }` | Mandatory reason textarea with client-side validation; success banner; 403 handling for VIEWER role. |
| **Proposal Audit Trail**<br>(Approvals, Compliance, Customer) | `/api/v1/proposals/{id}/audit` | `GET` | None | `{ events: [{ event_id, action, decision, actor_id, timestamp, reason }], total_count }` | Skeleton loaders; empty state banner ("Zero audit events recorded") if proposal has no prior decisions. |
| **FastEmbed Policy Q&A**<br>(Policies, Compliance) | `/api/v1/policies/ask` | `POST` | Body: `{ query, as_of_date, top_k }` | `{ answer, retrieval_status, citations: [...], retrieved_chunks: [...] }` | Loading spinner on "Retrieve & Answer"; citation badges with document chunk excerpts; offline fallback notice. |
| **Policy Vector Search**<br>(Policies) | `/api/v1/policies/search` | `POST` | Body: `{ query, as_of_date, top_k }` | `{ results: [{ chunk_id, document_title, content, similarity_score }] }` | Search spinner; ranked chunk cards showing cosine similarity score percentages. |
| **Workflow State Machine**<br>(Workflows) | `/api/v1/workflows` | `POST` | Body: `{ portfolio_id, as_of_date, request_key }` | `{ workflow_id, status, request_key, proposal_id, explanation, policy_evidence }` | Button loading state; stage pipeline stepper highlighting active and completed phases; live run list prepend. |
| **Workflow Run Inspection**<br>(Workflows) | `/api/v1/workflows/{id}` | `GET` | None | `{ workflow_id, status, proposal_id, explanation, ... }` | Visual progress indicator showing lifecycle progression. |

---

## 6. Theme Implementation

### 6.1 Architecture & Token System

- **Mode Support:** Dual theme supporting **Light**, **Dark**, and **System** (OS-preference matching via `prefers-color-scheme`).
- **Persistence:** Stored in `localStorage` under `yottaflex_theme`.
- **CSS Strategy:** Configured via Tailwind CSS `darkMode: 'class'`. When dark mode is active, the `'dark'` class is injected into the root `<html>` element.
- **Color Palette & Semantic Tokens:**
  - **Light Mode:** Canvas `bg-slate-50`, card background `bg-white`, borders `border-slate-200`, headings `text-slate-900`, body `text-slate-600`.
  - **Dark Mode:** Canvas `dark:bg-slate-950`, card background `dark:bg-slate-900`, borders `dark:border-slate-800`, headings `dark:text-slate-100`, body `dark:text-slate-400`.
  - **Brand Tokens:** Classic institutional sapphire/navy (`brand-600`: `#2563eb`, `brand-700`: `#1d4ed8`, dark accents `brand-400`: `#60a5fa`).
  - **Financial Accents:** Success/buy `emerald-600`/`emerald-400`, Danger/sell `rose-600`/`rose-400`, Warning/drift `amber-600`/`amber-400`.

### 6.2 Chart Adaptation

All Recharts SVG components (`AssetAllocationChart`, `TargetAllocationChart`) dynamically read theme properties from CSS and pass contrast-safe fills and strokes (`stroke="#94a3b8"`, `tick={{ fill: isDark ? '#94a3b8' : '#64748b' }}`) to guarantee legibility and meet WCAG AA contrast criteria in both themes.

---

## 7. Test Results

### 7.1 Frontend Test Suite

The frontend test suite was executed using Vitest with JSDOM:

```
> yottaflex-frontend@0.1.0 test
> vitest run

Test Files  9 passed (9)
     Tests  57 passed (57)
  Duration  10.18s
```

#### Test Suite Breakdown

1. `src/test/api-client.test.ts` (8 tests):
   - Verified Axios client creation, baseURL configuration, Bearer auth header injection, error response normalization, and endpoint URL generation.
2. `src/test/theme.test.tsx` (6 tests):
   - Verified ThemeProvider mounting, light/dark/system mode toggling, HTML class list synchronization, and localStorage persistence.
3. `src/test/shell.test.tsx` (4 tests):
   - Verified enterprise brand header rendering, role-tailored sidebar navigation items, responsive mobile sidebar behavior, and theme selector placement.
4. `src/test/settings.test.tsx` (7 tests):
   - Verified Settings workstation tabs, role switcher persistence, theme segmented controls, API connection status display, and session reset.
5. `src/test/portfolios.test.tsx` (11 tests):
   - Verified PortfoliosPage mounting, seeded portfolio dropdown selection, custom portfolio ID entry, financial metric KPI cards, holdings table filtering, drift analysis table with rebalance alert, and allocation charts.
6. `src/test/dashboard.test.tsx` (3 tests):
   - Verified dynamic role dispatching to `CustomerWorkspace`, `AnalystWorkspace`, `ComplianceWorkspace`, and `AdminWorkspace`.
7. `src/test/app.test.tsx` (1 test):
   - Verified application root mounting, provider hierarchy, and branding presentation.
8. `src/test/router.test.tsx` (7 tests):
   - Verified core route transitions (`/dashboard`, `/portfolios`, `/rebalancing`, `/approvals`, `/policies`, `/workflows`, `/settings`) and 404 fallback routing.
9. `src/test/rbac.test.tsx` (10 tests):
   - Verified `ProtectedRoute` enforcement, unauthorized access redirection, role permission checks for VIEWER vs REVIEWER/ADMIN, and header role switcher state updates.

### 7.2 Backend Test Suite Confirmation

The backend test suite was run concurrently to verify that no frontend modifications or service abstractions degraded backend behavior:

```
platform win32 -- Python 3.12.10, pytest-8.4.2, pluggy-1.7.0
rootdir: E:\Yottaflex\portfolio-rebalancing-system
configfile: pytest.ini
collected 507 items

============================ 507 passed in 35.34s =============================
```

Pass rate: **100% (507 passed / 0 failed)**.

---

## 8. Remaining Unsupported Backend Capabilities

To avoid fabricating UI features not supported by backend APIs, the following architectural decisions were made:

1. **Portfolio Catalog Listing (`GET /api/v1/portfolios`):**
   - *Backend Status:* No endpoint exists in FastAPI for listing all portfolios in the database.
   - *Frontend Handling:* Implemented `SEEDED_PORTFOLIO_REFERENCES` providing known institutional portfolios from the starter dataset (`PORT-INV-000001-02`, `PORT-INV-000001-01`, `PORT-INV-000002-01`, `PORT-INV-000003-01`), coupled with a custom ID entry input allowing analysts to query any valid portfolio ID in the database.
2. **User Management CRUD:**
   - *Backend Status:* No user-creation, user-deletion, or password-reset endpoints exist. Identity is managed via Bearer token headers and external OAuth2 identity providers.
   - *Frontend Handling:* In `AdminWorkspace.tsx`, the "Users & Roles" tab explicitly documents this architecture: *"In strict compliance with institutional security architecture, YottaFlex does not store raw passwords or provide standalone user-creation forms. Identity authentication and role mapping are provided via enterprise OAuth2/OIDC single sign-on (SSO) and HTTP Bearer tokens."*
3. **Automated Live Market Order Routing:**
   - *Backend Status:* The backend rebalancing engine generates deterministic in-memory trade proposals. It does not connect directly to live brokerage FIX gateways.
   - *Frontend Handling:* Prominently highlighted via the **Zero Live Holding Mutation Invariant** banner across Rebalancing, Approvals, and Portfolios screens.

---

## 9. Known Limitations

1. **JSDOM SVG Layout Warnings in Tests:**
   - In JSDOM test runs, Recharts logs non-fatal warnings (`The width(0) and height(0) of chart should be greater than 0`). This occurs because JSDOM does not calculate CSS bounding boxes. The charts render without error in real browser environments.
2. **Offline LLM Semantic Q&A Fallback:**
   - If the local Ollama daemon is offline or cold, `POST /api/v1/policies/ask` returns status `LLM_UNAVAILABLE` or insufficient evidence. The frontend gracefully detects this and displays the verified chunk excerpts and cosine rankings from the local FastEmbed ONNX vector model.

---

## 10. Instructions for Running the Application

### 10.1 Prerequisites

- Python 3.11+ with virtual environment configured in `.venv/`
- Node.js 18+ and npm
- PostgreSQL running locally on port 5432 (or configured via `.env`)

### 10.2 Starting the Backend

From the repository root:

```powershell
# Activate Python virtual environment
.\.venv\Scripts\Activate.ps1

# Start FastAPI application with Uvicorn
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend API documentation is accessible at `http://127.0.0.1:8000/docs` and health check at `http://127.0.0.1:8000/health`.

### 10.3 Starting the Frontend

From the `frontend/` directory:

```powershell
cd frontend

# Verify dependencies are installed
npm install

# Start Vite development server
npm run dev
```

The frontend will be accessible at `http://localhost:5173`. Vite automatically reverse-proxies `/api` and `/health` requests to `http://127.0.0.1:8000`.

### 10.4 Verifying Key Workflows

1. **Test Role Switching:**
   - In the top header bar, click the **Persona Selector** to toggle between:
     - `Customer Portal` → Personal overview, holdings, target comparisons, and plain-language rebalancing explanations.
     - `Analyst Desk` → Operational dashboard, drift surveillance, and proposal generator.
     - `Compliance Desk` → Review queue, hard constraint evaluation, and FastEmbed policy retrieval.
     - `Admin Console` → System health probes and reference data catalogs.
2. **Test Portfolio Valuation & Drift Analysis:**
   - Navigate to `/portfolios`.
   - Select `PORT-INV-000001-02` (Dakota Meridian Balanced Strategic 2).
   - Observe real-time valuation ($436,718.28), asset allocation breakdown, and allocation drift alerts.
3. **Test Rebalancing Optimization:**
   - Navigate to `/rebalancing`.
   - Click **Run Optimization**.
   - Observe the live generation of lot-sized trade recommendations (e.g. SELL 50 AAPL, BUY 120 BND), tiered broker fees, in-memory simulated post-trade cash, and automated constraint findings (HARD vs SOFT).
4. **Test Governance Approvals & Immutable Audit Logging:**
   - Navigate to `/approvals`.
   - With reviewer role set to `REVIEWER` or `ADMIN`, click **Approve Proposal** or **Reject Proposal** (with required justification).
   - Verify that the action creates an immutable record in the audit trail displayed below.
   - Switch the reviewer role to `VIEWER` in the header and attempt an approval: verify that the action is blocked with an explanatory permission alert.
5. **Test Grounded Policy Retrieval (RAG):**
   - Navigate to `/policies`.
   - On the "Ask Policy" tab, submit the query: *"What are the rules regarding thermal coal and tobacco revenue?"*
   - Verify that the response returns grounded policy citations with exact chunk identifiers (`DOC-ESG-001:chunk-002`).

