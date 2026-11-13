# Testing & Evaluation Guide

**Document Reference:** `docs/TESTING_AND_EVALUATION.md`
**Test Standard:** Strict Test-Driven Development (TDD) & Institutional Compliance
**Last Verified:** 2026-11-13

---

## 1. Automated Test Execution Summary

Every layer of the system has been verified using automated regression test suites and compliance verification scripts:

| Test Suite / Quality Gate | Scope | Executed | Passed | Failed | Errors | Execution Time | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Backend Test Suite (`pytest`)** | Full API, DB models, calculations, workflows, RAG, fees | **517** | **517** | 0 | 0 | 148.08s | **100% PASS** |
| **Frontend Test Suite (`vitest`)** | 11 suites across Shell, RBAC, Customer, Workflows, Approvals | **64** | **64** | 0 | 0 | 8.37s | **100% PASS** |
| **TypeScript Static Check (`tsc`)** | Strict static contract typing across all components | **Full** | **0 errors** | 0 | 0 | 5.12s | **100% PASS** |
| **ESLint Static Code Quality** | Static syntax and code cleanliness | **Full** | **0 errors** | 0 | 0 | 3.42s | **100% PASS** |
| **Production Vite Build** | Tree-shaking, minification, and bundling | **Full** | **Clean** | 0 | 0 | 7.06s | **100% PASS** |
| **Mandatory Negative Scenarios** | Sum $\neq 100\%$, excess sells, restricted assets, missing fees, stale prices | **5** | **5** | 0 | 0 | 2.18s | **100% PASS** |
| **Dataset Reproducibility Audit** | Fixed seed `20261022` SHA-256 byte-for-byte check | **26** | **26** | 0 | 0 | 1.84s | **100% PASS** |
| **Full Dataset Scale Audit** | 1.25M market prices, 5,000 instruments, 1,000 portfolios | **12** | **12** | 0 | 0 | 2.31s | **100% PASS** |

---

## 2. Mandatory Negative Scenarios & Compliance Verification

Execute via: `python scripts/verify_negative_scenarios_compliance.py`

1. **Portfolio allocation weights do not sum to 100%:**
   * *Test:* Target allocation for EQUITY corrupted to 55% (sum = 105%).
   * *Behavior:* Shared runtime validation boundary (`validate_target_allocations`) blocks calculation upfront with structured `HTTP 422 InvalidTargetAllocationError`. Zero database corruption; rolled back cleanly.
2. **Proposed trade exceeds available holding quantity:**
   * *Test:* SELL order of 25,700 units requested on holding of 25,200 units.
   * *Behavior:* `TradeSimulator` raises `ValueError: cannot sell unheld instrument` (`HTTP 422`). `TradeGenerator` clamps sell quantities to held lots.
3. **Excluded instrument recommended:**
   * *Test:* Recommendation to purchase `INS-000003` (registered on `EXCLUDED_INSTRUMENT` constraint).
   * *Behavior:* Hard constraint violation triggered (`EXCLUDED_INSTRUMENT`). Trade marked `BLOCKED`, proposal marked `REJECTED`, and unexecutable.
4. **Required fee schedule is missing:**
   * *Test:* All EQUITY fee schedules deactivated in transaction.
   * *Behavior:* Trade marked `BLOCKED` with diagnostic `Missing applicable fee schedule for BUY on INS-000002 (EQUITY)`; proposal marked `REJECTED`.
5. **Stale market price used without warning:**
   * *Test:* Valuation as of 2026-03-01 ($383\text{d}$ gap) and 2025-03-28 ($45\text{d}$ gap) against authoritative DB price date (`2025-02-11`).
   * *Behavior:* Exact price age calculated; position diagnostics attached (`383d STALE` and `45d STALE`); `requires_human_review = True` mandated unconditionally.

---

## 3. Dataset Reproducibility & Integrity Audits

### Deterministic Reproducibility
* Execute via: `python scripts/verify_dataset_reproducibility.py`
* Compares two independent runs using seed `20261022`.
* **Result:** All 26 CSV, JSON, and SQL seed files match byte-for-byte with identical SHA-256 checksums. Ground truth anomalies are strictly isolated.

### Full-Scale Dataset Audit
* Execute via: `python scripts/verify_full_dataset.py`
* Audits the 434.50 MB benchmark dataset in `data/full/`:
  * 1,250,000 market prices
  * 5,000 instruments
  * 1,000 portfolios
  * 5,000 holdings with 100% foreign key referential integrity
  * 4,000 target allocations summing to exactly 100.0000%
  * 5 verified ground truth anomaly test cases

---

## 4. Terminal Verification Commands

Run all verification suites directly from the repository root:

```powershell
# 1. Run full backend pytest regression suite (517 tests)
.\.venv\Scripts\pytest -q

# 2. Run frontend unit and component tests (64 tests across 11 suites)
npm test --prefix frontend -- --run

# 3. Run frontend TypeScript typecheck (0 errors)
npm run typecheck --prefix frontend

# 4. Run frontend ESLint code quality check (0 errors, 0 warnings)
npm run lint --prefix frontend

# 5. Run frontend production build (Clean Vite bundle)
npm run build --prefix frontend

# 6. Execute 5 Mandatory Negative Scenarios & Verification (100% Pass)
.\.venv\Scripts\python scripts\verify_negative_scenarios_compliance.py

# 7. Execute Dataset Reproducibility Audit (100% SHA-256 Match)
.\.venv\Scripts\python scripts\verify_dataset_reproducibility.py

# 8. Execute Full-Scale Dataset Manifest & Integrity Audit (1.25M prices)
.\.venv\Scripts\python scripts\verify_full_dataset.py
```

---

## 5. Live Evaluator Browser Walkthrough

1. **Start Services:** Start PostgreSQL (port 5433), Ollama, FastAPI (`app.main:app`), and Vite (`npm run dev`).
2. **Customer Experience:** Open `http://localhost:5173`. Log in as `REV-DEV-VIEWER`. Review holdings and drift banner. Open **Recommendations** tab to inspect staged orders table. Open **Activity** tab to inspect the 8-stage lifecycle.
3. **Analyst Workflow:** Switch to `REV-DEV-ANALYST`. Navigate to `/workflows` and click **Initiate Workflow**. Watch the 7-stage state machine transition and halt at Stage 7 (Human Review Gate).
4. **Fiduciary Review:** Switch to `REV-DEV-01` (Reviewer). In `/workflows`, click **Approve Proposal & Complete Workflow**.
5. **Audit Verification:** Inspect the Activity tab or Approvals desk to observe the recorded `AUD-...` immutable event.
6. **Re-Test:** Click **Reset to Pending Review** to re-test the human gate.
