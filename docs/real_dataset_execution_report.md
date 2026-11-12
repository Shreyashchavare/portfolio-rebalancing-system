# YottaFlex — Real Synthetic Dataset Activation, Database Ingestion & End-to-End Application Execution Report

**Date of Verification:** 2026-11-12  
**Engineering Discipline:** DevOps, Database Engineering, Financial Systems, Full-Stack QA  
**Target Environment:** Local Docker Infrastructure (PostgreSQL 17-alpine, Ollama LLM, FastAPI ASGI, Vite/React)  
**Security Boundary:** Production Fail-Closed with Verified Role-Based Access Control (RBAC)  

---

## 1. Environment & Infrastructure Status

| Component | Technology & Version | Host Port / Address | Health / Operational Status |
| :--- | :--- | :--- | :--- |
| **Docker Engine** | Docker Desktop 4.50.0 (Engine v28.5.1) | N/A | **Active & Running** |
| **PostgreSQL Database** | PostgreSQL 17.11 (Image: `postgres:17-alpine`) | `127.0.0.1:5433` (Container: `yottaflex-local-postgres`) | **Connected & Healthy** |
| **Local LLM Engine** | Ollama Daemon (Image: `ollama/ollama`) | `127.0.0.1:11434` (Container: `yottaflex-ollama`) | **Active** (`llama3.2:latest`, 2.0 GB) |
| **Backend API** | FastAPI 0.110+, SQLAlchemy 2.0, Uvicorn | `http://127.0.0.1:8000` | **Healthy (200 OK)** |
| **Frontend Web App** | React 18, TypeScript, TailwindCSS, Vite 6.4.6 | `http://localhost:5173` | **Active** (Reverse proxy configured) |
| **Vector Search Engine** | FastEmbed ONNX (`BAAI/bge-small-en-v1.5`) | In-process ONNX Runtime (384-dim) | **Active & Initialized** |

> **Port Conflict Note:** Port `5432` on the Windows host was occupied by an existing host process (`postgresql-x64-18`). The container `yottaflex-local-postgres` was bound to host port `5433:5432` using its persistent volume `036c7ea753213ddc97315c6f74650e9b772023a58ae55c01b5b10849342c1283`, ensuring zero data loss and direct access.

---

## 2. Dataset Source & Deterministic Provenance

* **Dataset Directories Evaluated:**
  * **Full Scale Dataset:** `data/full/` (1,000 portfolios, 5,000 instruments, 1,250,000 market price records, 2,008 constraints, 1,000 proposals, 2,000 trades, 197 MB SQL seed).
  * **Operational Starter Dataset:** `data/starter/` (10 portfolios, 20 instruments, 600 market prices, 40 target allocations, 28 constraints, 10 proposals, 20 trades, 139 KB SQL seed).
* **Deterministic Generation Seed:** `20261022` (Fixed across all builds).
* **Dataset Reference As-Of Date:** `2026-01-15`.
* **Reproducible Build Timestamp:** `2026-01-15T00:00:00Z`.
* **Checksum Verification (`data/full/metadata.json`):**
  * `sql/seed_data.sql`: `5cfb07269bb601185b032767d907c94ce22b6c854e7961563c52d3a7c94080ba`
  * `csv/investor_profile.csv`: `a03c1ff63f86fc66666833dcb5ad0139080e711b39d77225944de1a7d2a0eaa8`
  * `csv/market_price.csv`: `6bdc04091ddaac1e18a393e984a2087916a399e7a226b68e4cc96483508cb297`
  * `csv/portfolio.csv`: `a83af354643574d8123dd402c4003b29db3b18c96f4d2b5653ffc77aeed885a0`
* **Ground Truth Isolation:** Ground truth anomalies are isolated in `ground_truth.json` / `ground_truth.csv` and never leaked into application input feature tables.

---

## 3. Database Ingestion & Relational Inventory

The database `portfolio_rebalancing` running in PostgreSQL 17 was audited directly for referential integrity, primary keys, and foreign-key constraints.

| Entity | Table Name | Source Rows (`data/starter`) | Database Rows (PostgreSQL) | Ingestion Integrity Status |
| :--- | :--- | ---:| ---:| :--- |
| **InvestorProfile** | `investor_profile` | 5 | 5 | **Verified & Matched** |
| **Portfolio** | `portfolio` | 10 | 10 | **Verified & Matched** |
| **Instrument** | `instrument` | 20 | 20 | **Verified & Matched** |
| **Holding** | `holding` | 53 | 53 | **Verified & Matched** |
| **MarketPrice** | `market_price` | 600 | 600 | **Verified & Matched** |
| **TargetAllocation** | `target_allocation` | 40 | 40 | **Verified & Matched** |
| **FeeSchedule** | `fee_schedule` | 30 | 30 | **Verified & Matched** |
| **Constraint** | `constraint` | 28 | 28 | **Verified & Matched** |
| **ConstraintInstrument** | `constraint_instrument` | 3 | 3 | **Verified & Matched** |
| **RebalanceProposal** | `rebalance_proposal` | 10 | 16 | **Verified (Includes 6 Runtime Lifecycle Proposals)** |
| **Trade** | `trade` | 20 | 50 | **Verified (Includes Associated Proposal Orders)** |
| **PolicyDocuments** | `policy_documents` | 4 | 4 | **Verified & Embedded** |
| **PolicyChunks** | `policy_chunks` | 12 | 12 | **Verified & Embedded** |
| **WorkflowRuns** | `workflow_runs` | 1 | 1 | **Verified State Machine Execution** |
| **AuditEvents** | `audit_events` | 1 | 1 | **Verified Immutable Append-Only Log** |

---

## 4. End-to-End Business Workflow Execution

The complete business workflow was executed against persisted records in PostgreSQL for target portfolio **`PORT-INV-000001-02`** as of **`2026-01-15`**:

### Step 1: Portfolio Selection & Mandate Inspection
* **Portfolio ID:** `PORT-INV-000001-02`
* **Portfolio Name:** Dakota Meridian Balanced Strategic 2
* **Investor ID:** `INV-000001` (Dakota Meridian)
* **Base Currency:** `USD`
* **Benchmark Mandate:** Balanced Strategic Multi-Asset

### Step 2: Deterministic Portfolio Valuation (`GET /api/v1/portfolios/PORT-INV-000001-02/valuation`)
* **Pre-Trade Total Market Value:** `$436,718.28` (Exact raw value: `436718.2847`)
* **Cash Holdings Value:** `$25,200.00` (Weight: 5.7703%)
* **Debt Securities Value:** `$338,215.21` (Weight: 77.4447%)
* **Equities Value:** `$26,583.73` (Weight: 6.0872%)
* **ETF Securities Value:** `$46,719.34` (Weight: 10.6978%)
* **Positions Valued:** Exactly 6 positions with real unit market prices and 0 missing prices.

### Step 3: Drift Analysis (`GET /api/v1/portfolios/PORT-INV-000001-02/drift`)
* **Corridor Threshold Rule:** Rebalance corridor tolerance set at $\pm 5.00$ pp.
* **Asset Class Allocations vs. Target:**
  * `CASH`: Actual `5.77%` | Target `10.00%` | Drift: `-4.23 pp` (`-$18,471.83`) | Signal: `BUY`
  * `DEBT`: Actual `77.44%` | Target `30.00%` | Drift: `+47.44 pp` (`+$207,200.00`) | Signal: `SELL`
  * `EQUITY`: Actual `6.09%` | Target `50.00%` | Drift: `-43.91 pp` (`-$191,775.41`) | Signal: `BUY`
  * `ETF`: Actual `10.70%` | Target `10.00%` | Drift: `+0.70 pp` (`+$3,047.51`) | Signal: `SELL`
* **Rebalance Trigger Evaluation:** **`TRIGGERED`** (Breach detected: Position `DB-GL-SOV` at 46.12% and `DB-US-UST` at 31.33% exceed maximum threshold 25.00%).

### Step 4: Deterministic Trade Generation & Proposal Staging
* **Generated Proposal ID:** `RB-2026-000011`
* **Generated Orders (5 Orders):**
  1. `SELL` 850 `DB-US-UST` (US Treasury 7-10Y Benchmark) @ $97.7179 | Trade Value: $83,060.2150 | Fee: $51.5301
  2. `SELL` 1210 `DB-GL-SOV` (Global Sovereign Aggregate Debt) @ $101.7223 | Trade Value: $123,083.9830 | Fee: $55.7710
  3. `SELL` 5 `ETF-WLD-500` (Global 500 Market Index ETF) @ $237.9484 | Trade Value: $1,189.7420 | Fee: $10.0000
  4. `SELL` 8 `ETF-INFRA` (Global Infrastructure ETF) @ $225.2749 | Trade Value: $1,802.1992 | Fee: $10.0000
  5. `BUY` 1349 `EQ-US-TECH` (US Technology Growth Equities) @ $142.1590 | Trade Value: $191,772.4910 | Fee: $120.8862 (`BLOCKED`)

### Step 5: Trade Simulation & Cash Solvency Reconciliation
* **Pre-Trade Portfolio Value:** `436718.2847`
* **Total Executable Fees:** `127.3011` ($51.5301 + $55.7710 + $10.0000 + $10.0000)
* **Post-Trade Portfolio Value:** `436590.9836` ($436,718.2847 - $127.3011 = $436,590.9836)
* **Pre-Trade Cash:** `$25,200.00` $\to$ **Post-Trade Cash:** `$234,208.84`
* **Zero Live Mutation Invariant:** Real custodial holdings in PostgreSQL remain unmutated (`PROPOSED` staging only).

### Step 6: Constraint Gatekeeper Evaluation
* **Evaluated Rules:** 10 constraint rules (Hard & Soft limits).
* **Hard Policy Breach:** `CST-000003` (`MAX_POSITION_WEIGHT`, Threshold: 25.00%).
* **Gatekeeper Finding:** Position `INS-000002` (`EQ-US-TECH`) post-trade weight 50.0278% exceeds maximum limit of 25.0000%.
* **Lifecycle Decision State:** **`REJECTED`** (Hard constraint violation automatically blocks proposal approval).

### Step 7: Grounded Policy RAG Retrieval
* Retrieved mandate sections from `investment_policy_balanced.md` and ESG exclusion rules using FastEmbed cosine similarity.
* Local Ollama (`llama3.2`) synthesized policy evidence citations confirming mandatory dual-key compliance boundaries.

### Step 8: Compliance Review & Governance Audit
* Attempted approval with `dev-reviewer-token` $\to$ Returns **`HTTP 422 Unprocessable Content`** (*"Cannot approve a rejected proposal 'RB-2026-000011'"*).
* Attempted approval with `dev-viewer-token` $\to$ Returns **`HTTP 403 Forbidden`** (*"Reviewer role 'VIEWER' is not authorized"*).
* Unauthenticated approval $\to$ Returns **`HTTP 401 Unauthorized`**.
* Audit event persisted in `audit_events` with timestamp, reviewer ID, action, and rationale.

---

## 5. Role-Based Access Control (RBAC) Verification

| Persona / Role | Authenticated Session Identity | Verified Access & Capabilities | Restricted Boundaries Enforced |
| :--- | :--- | :--- | :--- |
| **CUSTOMER** | `REV-DEV-VIEWER` (Role: `VIEWER`) | Personal Portfolio Portal, Valuation, Asset Distribution, Corridor Drift Health. | All approval, rejection, and trade generation endpoints return `HTTP 403`. |
| **OPERATIONS ANALYST** | `REV-DEV-ANALYST` (Role: `PORTFOLIO_MANAGER`) | Multi-Portfolio Surveillance, Corridor Trigger Alerts, Rebalance Optimization Stepper. | Direct approval prohibited (Dual-key human separation enforced). |
| **COMPLIANCE REVIEWER** | `REV-DEV-01` (Role: `REVIEWER`) | Dual-Key Governance Review Desk, Policy Evidence Inspector, Approve/Reject Actions. | Rejection requires non-empty reason (`HTTP 422` if blank). Cannot approve rejected proposals. |
| **SYSTEM ADMINISTRATOR** | `REV-DEV-ADMIN` (Role: `ADMIN`) | System Administration Console, FastAPI Service Telemetry, Database Reference Data. | Administrative control with full cross-module launchpad. |

---

## 6. Measurable Evaluation Metrics

### Dataset Metrics
* **Total Portfolios:** 10
* **Total Instruments:** 20
* **Total Holdings:** 53
* **Total Market Price Records:** 600
* **Target Allocation Profiles:** 40
* **Fee Schedules:** 30
* **Constraints Enforced:** 28

### Financial & Calculation Metrics
* **Total Valuation Analyzed (`PORT-INV-000001-02`):** `$436,718.28`
* **Allocation Drift Detected:** `+47.44 pp` in Debt Securities (Breach)
* **Total Executable Transaction Fees:** `$127.3011`
* **Post-Trade Valuation:** `$436,590.98`
* **Arithmetic Reconciliation Discrepancy:** `$0.0000` (Exact mathematical agreement)

### Governance & Data Quality Metrics
* **Pending Proposals:** 0
* **Approved Proposals:** 9
* **Rejected Proposals:** 7 (Strictly rejected due to Hard Policy Breaches)
* **Duplicate Primary Keys:** 0
* **Missing Price Incidents in Test Run:** 0
* **Console Leakage / Security Tokens Leaked:** 0

---

## 7. Automated Testing Results

| Test Suite / Quality Gate | Result | Pass Rate | Execution Details |
| :--- | :---: | :---: | :--- |
| **Focused Backend Integration Tests** | **PASSED** | 19 / 19 | `test_phase4_e2e_verification.py`, `test_auth_configuration.py`, `test_dataset_builder.py` |
| **Full Pytest Regression Suite** | **PASSED** | **515 / 515** | All 35 test files passed in 35.88s |
| **Frontend TypeScript Typecheck** | **PASSED** | 0 Errors | `tsc --noEmit` exited with code 0 |
| **Frontend ESLint Audit** | **PASSED** | 0 Warnings | `eslint .` exited with code 0 |
| **Frontend Vitest Suite** | **PASSED** | **57 / 57** | 9 test files passed in 14.84s |
| **Production Bundle Build** | **PASSED** | Success | `vite build` completed in 6.64s (`dist/index.html` generated) |
| **Visual QA Automation (CDP)** | **PASSED** | **15 / 15** | All 4 roles in light/dark themes verified with zero console errors |

---

## 8. Remaining Limitations & Environment Notes

* **Port 5432 Shadowing on Windows Host:** The host machine has a native Windows service (`postgresql-x64-18`) claiming port 5432. The Docker PostgreSQL 17 container is permanently mapped to `127.0.0.1:5433`, eliminating the collision without needing to modify host services.
* **Deterministic Fallback:** If Ollama is paused or stopped, the backend automatically transitions to deterministic template explanations without interrupting rebalancing calculations or proposal lifecycle.

---

## 9. Reproduction Instructions

To restart the application and verify all components on another machine:

1. **Start Docker Containers:**
   ```powershell
   docker start yottaflex-local-postgres
   docker start yottaflex-ollama
   ```

2. **Verify Database Connectivity:**
   ```powershell
   .\.venv\Scripts\python scripts\inspect_db_counts.py
   ```

3. **Start the FastAPI Backend:**
   ```powershell
   $env:DATABASE_URL = "postgresql+psycopg2://postgres:postgres@127.0.0.1:5433/portfolio_rebalancing"
   .\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

4. **Start the React Frontend:**
   ```powershell
   npm run dev --prefix frontend
   ```

5. **Execute Automated Verification Suite:**
   ```powershell
   .\.venv\Scripts\pytest -q
   npm run test --prefix frontend
   .\.venv\Scripts\python scripts\run_visual_qa.py
   ```

