# YottaFlex Portfolio Rebalancing System
# End-to-End Interactive User & Evaluator Guide

**Document Reference:** `docs/USER_GUIDE.md`  
**Application URL:** `http://localhost:5173`  
**API Gateway URL:** `http://127.0.0.1:8000/docs`  

---

## 1. Introduction & Executive Overview

Welcome to the **YottaFlex Portfolio Rebalancing System**! This application is an institutional-grade, policy-constrained wealth management platform designed to:
1. **Continuously Monitor Portfolio Health:** Compare live portfolio holdings against target asset-class allocations.
2. **Detect Allocation Drift:** Identify corridor breaches using deterministic tolerance band calculations.
3. **Generate Trade Orders:** Create lot-sized, cash-solvency-verified trade orders with tiered execution fees.
4. **Enforce Fiduciary Compliance:** Screen orders against hard/soft constraints (`MAX_POSITION_WEIGHT`, `EXCLUDED_INSTRUMENT`, `TURNOVER_LIMIT`) and ground recommendations in policy documents via local FastEmbed vector search and Ollama AI.
5. **Guarantee Human-in-the-Loop Governance:** Stage all recommendations as proposals requiring verified reviewer approval before execution. All decisions are immutably recorded in an append-only audit trail.
6. **Ensure Zero Live Trading Risk:** The system is advisory and simulation-only; custodial accounts are never mutated directly.

---

## 2. Fast Launch Checklist

Before opening the user interface, verify that the local services are running:

### Step 1: Start Database & AI Infrastructure (Docker)
```powershell
# Start PostgreSQL (Port 5433) and Ollama (Port 11434)
docker start yottaflex-local-postgres
docker start yottaflex-ollama
```

### Step 2: Start the FastAPI Backend
```powershell
# Open Terminal 1
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL = "postgresql+psycopg2://postgres:postgres@127.0.0.1:5433/portfolio_rebalancing"
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Health check:* Visit `http://127.0.0.1:8000/health` (returns `{"status": "healthy"}`).

### Step 3: Start the Vite Frontend
```powershell
# Open Terminal 2
cd frontend
npm run dev
```
*Open Browser:* Visit **`http://localhost:5173`**.

---

## 3. Understanding Personas vs. Customer Accounts

A critical design feature of YottaFlex is the clean architectural separation between **Institutional Security Roles (RBAC Personas)** and **Individual Client Wealth Accounts (Customer Profiles)**:

```text
+-----------------------------------------------------------------------------------+
|  TOP-RIGHT CORNER: 4 Institutional RBAC Personas                                  |
|  [ Customer (VIEWER) ]  [ Analyst (PORTFOLIO_MANAGER) ]  [ Reviewer ]  [ Admin ]  |
+-----------------------------------------------------------------------------------+
                                          |
          Controls permissions, mutations, and approval authority
                                          v
+-----------------------------------------------------------------------------------+
|  INSIDE CUSTOMER PORTAL: Customer Account Profile Switcher                        |
|  Profile: [ INV-000001: Dakota Meridian (PORT-INV-000001-02) v ]                  |
|           • INV-000001: Dakota Meridian (Legacy Portfolio 01)                     |
|           • INV-000002: Avery Valence (Conservative Liquidity)                    |
|           • INV-000003: Logan Apex (Growth & Income)                              |
+-----------------------------------------------------------------------------------+
```

### The 4 Institutional RBAC Personas (Top-Right Menu)

| RBAC Persona | Role Code | Target Workstation | Permissions & Capabilities |
| :--- | :--- | :--- | :--- |
| **Customer / Account Holder** | `VIEWER` | Personal Wealth Portal | **Read-Only.** Can inspect personal portfolio valuation, asset allocations, staged recommendations, and lifecycle progress. Cannot approve proposals or stage orders (HTTP 403 Forbidden). |
| **Operations Analyst** | `PORTFOLIO_MANAGER` | Analyst Workspace & Pipelines | **Operational Oversight.** Can monitor drift corridors, initiate 7-stage state machine workflows, and stage proposals. Cannot self-approve proposals (separation of duties). |
| **Risk & Compliance Reviewer** | `REVIEWER` | Governance Desk (`/approvals`) | **Human-in-the-Loop Signoff.** Fiduciary gatekeeper. Evaluates constraint breaches, approves eligible proposals, or rejects proposals with mandatory justification. |
| **System Administrator** | `ADMIN` | Admin Console (`/admin`) | **Master Oversight.** Superuser access across reference tables, data quality diagnostics, system configuration, and audit logs. |

---

## 4. Workstation Walkthrough Guide

### Workstation 1: Customer Account Portal (`/customer` or select Customer Persona)
Designed for client transparency and fiduciary oversight:
1. **Header & Profile Selector:**
   * View investor name (`Dakota Meridian`), account reference (`INV-000001`), and portfolio reference (`PORT-INV-000001-02`).
   * Use the **Profile Dropdown** in the header to switch to other client wealth accounts (e.g., Avery Valence or Logan Apex).
2. **Overview Tab:**
   * High-level allocation cards, total valuation ($436,718.28), cash balance, and target vs. actual weight breakdown charts.
3. **My Portfolio Tab:**
   * Comprehensive security holdings breakdown table showing symbols, asset classes, quantities, unit prices, and staleness age indicators.
4. **Recommendations Tab:**
   * **Drift Alert Banner:** Visual callout when allocations breach policy tolerance corridors (`Portfolio Drift Trigger Detected (DEBT)`).
   * **Staged Trade Orders Table:** Clear breakdown of all staged deterministic orders showing Security Symbol, Asset Class, Action (`BUY`/`SELL`), Quantity, Unit Price, Estimated Value, and Fees.
5. **Activity Tab:**
   * **Central Rebalancing Lifecycle:** Visual 8-stage stepper tracking the lifecycle from Portfolio Selection to Immutable Audit Traceability.
   * **Audit Trail History:** Cryptographic event cards showing reviewer ID, decision (`APPROVE`/`REJECT`), timestamp, and metadata.

---

### Workstation 2: Workflow Orchestration & State Monitoring (`/workflows`)
Designed for managing agentic, multi-stage rebalancing execution:
1. **Initiate Workflow:**
   * Select a target portfolio from the dropdown (e.g., `PORT-INV-000001-02`).
   * Click the primary **`Initiate Workflow`** button.
2. **Execution State Machine Transition Pipeline:**
   * Watch the live stepper progress through 7 stages:
     1. `01 1. Received` $\to$ Passed
     2. `02 2. Validating` $\to$ Passed (Shared allocation 100% check)
     3. `03 3. Drift Analysis` $\to$ Passed (Tolerance corridor evaluation)
     4. `04 4. Proposal & Fees` $\to$ Passed (Lot sizing, fee calculation, cash solvency)
     5. `05 5. FastEmbed RAG` $\to$ Passed (Vector policy retrieval)
     6. `06 6. Grounded Summary` $\to$ Passed (AI explanation synthesis)
     7. `07 7. Human Review` $\to$ **HALTED AT REVIEW GATE** (Deterministic compliance halt)
3. **Stage 7 Human Review Gate:**
   * **If logged in as Viewer/Analyst:** The system displays an institutional policy notice explaining that Reviewer authority is required. In development, click the convenient **`Switch to Reviewer to Approve`** button!
   * **If logged in as Reviewer (`REV-DEV-01`) or Admin:** Click the primary **`Approve Proposal & Complete Workflow`** button.
   * The pipeline will instantly complete, transitioning to **`PIPELINE COMPLETED`** with Stage 7 marked as Passed, and log an audit record.
   * **Re-testing:** Click **`Reset to Pending Review`** to reset the proposal and re-test the gate at any time!

---

### Workstation 3: Governance & Approvals Desk (`/approvals`)
The central control center for fiduciary signoff:
1. **Interactive Proposal Selector:**
   * Select any proposal from the dropdown (e.g. `RB-2026-000002` or `RB-2026-000004`).
2. **Governance Decision Context Metrics:**
   * **Staged Proposal ID:** Target proposal reference.
   * **Review Decision State:** `PENDING_REVIEW`, `APPROVED`, or `REJECTED`.
   * **Total Rebalance Trades:** Number of staged orders and total notional value.
   * **Hard Constraint Evaluation:** Clear indication if the proposal is `CLEARED FOR APPROVAL` or `BLOCKED BY CONSTRAINTS`.
3. **Action Execution:**
   * **Approve Proposal:** Prompts for optional review notes, validates constraint clearance, sets status to `APPROVED`, and writes an immutable audit record.
   * **Reject Proposal:** Opens the rejection dialog requiring a mandatory non-empty justification reason (e.g., "Excessive turnover under current volatility"), sets status to `REJECTED`, and logs the decision.
   * **Reset to Pending Review:** Resets the proposal back to `PENDING_REVIEW` so you can re-run and re-verify approval/rejection flows.

---

### Workstation 4: Portfolio Analytics Desk (`/portfolios`)
Deep-dive quantitative surveillance:
1. **Interactive Portfolio Selector:** Switch between any of the 10 seeded portfolios.
2. **Metric Summary Cards:** Total Market Value, Cash Position, Risk Profile, and Active Drift Trigger.
3. **Holdings Breakdown:** Interactive search filter and asset class dropdown. Displays position age and flags stale market prices ($383\text{d}$ and $45\text{d}$) with warning badges.
4. **Drift Analysis:** Benchmark vs actual percentage weights, corridor tolerance bands ($\pm 5\%$), and drift direction.

---

## 5. Step-by-Step Guided Evaluator Walkthrough

To experience the full end-to-end lifecycle from customer drift detection to approved audit trail:

```mermaid
flowchart TD
    A["1. Customer Views Drift Alert & Staged Orders (Viewer)"] --> B["2. Analyst Runs Workflow Pipeline (/workflows)"]
    B --> C["3. State Machine Halts at Stage 7 Human Gate"]
    C --> D["4. Reviewer Approves Proposal (REV-DEV-01)"]
    D --> E["5. Immutable Audit Event Logged to DB (AUD-...)"]
    E --> F["6. Reset Proposal to Re-test Governance Flow"]
```

### Step 1: Experience the Customer View
1. Select **`REV-DEV-VIEWER`** from the top-right persona dropdown.
2. Navigate to **Customer Portal** (`/customer`).
3. Notice your portfolio valuation ($436,718.28) and drift warning.
4. Click the **Recommendations** tab to view your 5 staged rebalancing orders.
5. Click the **Activity** tab to see Stage 3 (Drift Calculation) in the lifecycle stepper.

### Step 2: Initiate Workflow as an Analyst
1. Switch to **`REV-DEV-ANALYST`** from the top-right dropdown.
2. Navigate to **Workflows** (`/workflows`).
3. Click **`Initiate Workflow`**.
4. Observe Stages 1–6 turning green, and Stage 7 halting with the Amber clock icon: **`HALTED AT REVIEW GATE`**.

### Step 3: Authorize Proposal as Reviewer
1. Switch to **`REV-DEV-01`** (Risk Reviewer).
2. On the **Workflows** page, observe the active button: **`Approve Proposal & Complete Workflow`**.
3. Click it! The badge immediately updates to **`PIPELINE COMPLETED`**.
4. Navigate to **Approvals Desk** (`/approvals`): observe that `RB-2026-000002` is now `APPROVED`.

### Step 4: Verify the Immutable Audit Trail
1. Scroll down to the **Audit Trail** card on the Approvals Desk or in the Customer Portal.
2. Observe the newly created record:
   * **Action:** `APPROVE`
   * **Reviewer:** `REV-DEV-01`
   * **Event ID:** `AUD-...`
   * **Timestamp:** Exact ISO-8601 UTC timestamp.

### Step 5: Test Proposal Reset
1. On the Approvals Desk, click **`Reset to Pending Review`**.
2. Notice the proposal instantly reverts to `PENDING_REVIEW`, clearing the way for subsequent tests or rejections!

---

## 6. Evaluator Frequently Asked Questions (FAQ)

### Q1: Why did proposal RB-2026-000002 show "0 AUDIT EVENTS" initially?
**Answer:** In accordance with institutional dual-key compliance, **audit events in YottaFlex are append-only cryptographic records generated when a human governance decision is rendered** (`POST /api/v1/proposals/{id}/approve` or `POST /api/v1/proposals/{id}/reject`). When starter proposals are first generated or seeded, they wait in `PENDING_REVIEW` until an authorized reviewer acts on them. Once approved or rejected, an audit event is atomically recorded.

### Q2: Why are only 4 users listed in the top-right menu when there are many investors?
**Answer:** The top-right menu is a **Security Role (RBAC) Switcher** representing the 4 institutional system personas: Customer (`VIEWER`), Analyst (`PORTFOLIO_MANAGER`), Reviewer (`REVIEWER`), and Admin (`ADMIN`). To switch between individual client wealth accounts (`INV-000001: Dakota Meridian`, `INV-000002: Avery Valence`, `INV-000003: Logan Apex`, etc.), use the **Profile Dropdown** located inside the Customer Portal header.

### Q3: What happens when an order breaches a Hard Constraint?
**Answer:** Hard constraints (e.g. `MAX_POSITION_WEIGHT = 25%` or `EXCLUDED_INSTRUMENT`) strictly block execution. In `RebalancingService`, the violating trade is marked `BLOCKED`, the proposal is marked `REJECTED`, and the Approvals Desk disables the Approve button, displaying a red alert detailing the breach.

### Q4: Does the system function if Ollama or the local LLM is offline?
**Answer:** Yes! If Ollama is offline or uninstalled, the Policy RAG service automatically activates an offline fallback that delivers deterministic evidence-based citations and summaries directly from the FastEmbed vector store without crashing.

---

## 7. Verification Commands Summary

To independently verify all system components from your terminal:

```powershell
# Run full backend pytest suite (517 passed)
.\.venv\Scripts\pytest -q

# Run full frontend vitest suite (64 passed across 11 suites)
npm test --prefix frontend -- --run

# Run TypeScript type check (0 errors)
npm run typecheck --prefix frontend

# Run ESLint (0 errors, 0 warnings)
npm run lint --prefix frontend

# Verify Negative Financial Scenarios (5/5 passed)
.\.venv\Scripts\python scripts\verify_negative_scenarios_compliance.py

# Verify Dataset Reproducibility (100% SHA-256 match)
.\.venv\Scripts\python scripts\verify_dataset_reproducibility.py

# Verify Full Dataset Scale (1.25M prices)
.\.venv\Scripts\python scripts\verify_full_dataset.py
```

*For the complete evaluation evidence report, see [MASTER_TDD_VALIDATION_REPORT.md](file:///e:/Yottaflex/portfolio-rebalancing-system/docs/MASTER_TDD_VALIDATION_REPORT.md).*

