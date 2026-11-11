# Prompt P4-04 — Post-Trade Simulation, Constraint Gatekeeper, Proposal Persistence and API

**AI Tool:** Antigravity  
**Phase:** 4 — Rebalancing Engine  
**Task:** Batch 4.2 — Post-Trade Simulation, Constraint Gatekeeper, Proposal Persistence and API

## Prompt

# Phase 4.2 — Post-Trade Simulation, Constraint Gatekeeper, Proposal Persistence and API

Repository: `E:\Yottaflex\portfolio-rebalancing-system`

## Objective

Complete the rebalancing workflow by implementing deterministic post-trade simulation, constraint validation, transactional proposal persistence, and a FastAPI endpoint.

Reuse the existing `RebalancingService` and Phase 4.1 trade generation. Do not duplicate financial calculations.

## 1. Inspect Existing Contracts First

Inspect:
- `app/services/rebalancing_service.py`
- `app/schemas/rebalancing.py`
- `app/models/rebalance_proposal.py`
- `app/models/trade.py`
- `app/models/constraint.py`
- `app/models/constraint_instrument.py`
- `app/models/holding.py`
- `app/models/instrument.py`
- `app/models/market_price.py`
- `app/models/portfolio.py`
- `app/models/fee_schedule.py`
- `app/api/v1/analytics.py`
- `app/api/v1/__init__.py`
- `app/database/session.py`
- `app/main.py`
- Relevant model, service, and API tests.

Confirm exact enum values, field names, SQLAlchemy relationships, transaction conventions, and existing database session behavior. Do not invent fields.

## 2. Write Tests First — RED

Create `tests/test_rebalancing_simulation_api.py`.

Cover the following:

### A. Post-Trade Simulation

1. Apply proposed SELL quantities to a copy of existing holdings.
2. Apply proposed BUY quantities to the simulated holdings.
3. Adjust cash for sell proceeds, sell fees, buy notionals, and buy fees.
4. Recalculate post-trade position values and asset-class weights.
5. Recalculate post-trade drift against the applicable target allocation.
6. Verify:
   `post_trade_portfolio_value = pre_trade_portfolio_value - total_executable_fees`
7. Verify simulated cash never becomes negative.
8. Verify lot-size rounding and residual drift are preserved.
9. Verify actual database holdings remain unchanged by simulation.
10. Reject or explicitly flag invalid trade inputs rather than silently applying them.

### B. Constraint Gatekeeper

Evaluate active constraints effective on `as_of_date`, respecting scope and severity.

Cover:

- `EXCLUDED_INSTRUMENT`
- `MAX_POSITION_WEIGHT`
- `MIN_POSITION_WEIGHT`
- `MIN_TRADE_VALUE`
- `MAX_TRADE_VALUE`
- `MIN_TRADE_QUANTITY`
- `MAX_TRADE_QUANTITY`
- `LIQUIDITY_LIMIT`

Requirements:
- Enforce the correct instrument-level or portfolio-level scope.
- Evaluate position-weight constraints against individual instrument positions, not aggregate asset-class weights.
- Evaluate trade-level constraints against each proposed trade.
- Evaluate liquidity against post-trade cash percentage.
- Respect effective dates and open-ended constraints.
- Hard violations must block affected trades and prevent proposal approval.
- Soft violations must be recorded as warnings and must not be silently ignored.
- Excluded instruments must never pass the gatekeeper as executable BUY trades.

If a constraint's meaning or scope cannot be established from the existing model and generator contracts, report the ambiguity rather than inventing semantics.

### C. Proposal Persistence

1. Persist a `RebalanceProposal` with its associated `Trade` records.
2. Link every trade to the correct proposal and portfolio.
3. Persist correct pre-trade and post-trade portfolio values.
4. Persist trade quantities, side, price, notional, fee, fee schedule and status.
5. Use existing lifecycle enums.
6. Clean proposal:
   - `status = PENDING_REVIEW`
   - `review_decision = PENDING`
7. Hard constraint violation:
   - `status = REJECTED`
   - `review_reason` describes the violation.
   - Affected trades have `status = BLOCKED`.
8. Unknown price freshness or other human-review requirement must never automatically approve a proposal.
9. Do not create duplicate proposal or trade records on a failed transaction.

### D. API

Implement:

`POST /api/v1/portfolios/{portfolio_id}/rebalance/proposals`

Requirements:
- Reuse the existing `get_db` dependency and router conventions.
- Accept an optional `as_of_date`.
- Return the persisted proposal, trades, simulation results, validation findings and review status.
- Unknown portfolio: HTTP 404.
- Missing market price: appropriate HTTP 422.
- Invalid request: HTTP 422.
- Unexpected errors: safe HTTP 500 without internal stack traces.
- Do not expose secrets, SQL errors or internal exception details.

Demonstrate RED before production implementation.

## 3. Implementation

### A. Simulation

Implement a deterministic simulation method in `RebalancingService` or a focused helper within the existing service architecture.

Simulation must:
- Operate on an isolated in-memory representation.
- Never update actual Holding or Portfolio records.
- Apply only executable proposed trades.
- Recalculate cash, market value, asset-class allocations and drift.
- Account for all executable transaction fees.
- Preserve Decimal precision.
- Produce explicit residual drift and diagnostics.

Do not calculate simulated values using floating-point arithmetic.

### B. Constraint Validation

Implement a deterministic validation method.

For each applicable constraint:
- Check active status.
- Check effective date range.
- Resolve scope correctly.
- Check HARD and SOFT severity separately.
- Produce structured findings containing constraint ID, constraint type, severity, affected instrument/trade where applicable, and explanation.

Hard violations:
- Must not be approved.
- Mark affected trades BLOCKED.
- Proposal becomes REJECTED.

Soft violations:
- Must be returned as warnings.
- Do not silently discard them.
- Keep the proposal subject to human review.

Do not allow a blocked SELL to finance BUY trades in the simulation. Recalculate cash using executable trades only.

### C. Transactional Persistence

Persist proposal and trade records in one database transaction.

Requirements:
- Use the existing session.
- Commit only after all records are correctly prepared.
- Roll back on any persistence failure.
- Avoid partial proposal/trade records.
- Never update actual holdings during proposal generation.
- Preserve the existing human approval lifecycle.

Do not implement trade execution or automatic approval.

### D. API Integration

Create:
`app/api/v1/rebalancing.py`

Register the router using existing conventions in:
- `app/api/v1/__init__.py`
- `app/main.py`

Keep route handlers thin. Financial logic belongs in the service layer.

## 4. RED/GREEN and Regression Verification

After implementation:

1. Run the new simulation and API tests.
2. Run all Phase 4.1 rebalancing service tests.
3. Run Phase 3 analytics and API tests.
4. Run the full suite:

`.\.venv\Scripts\python.exe -m pytest -q`

Resolve all failures before reporting completion.

## 5. Prompt History

Save this task prompt and concise RED/GREEN execution record in:

`prompts/phase-4/04-post-trade-simulation-constraint-gatekeeper-api.md`

## 6. Strict Scope Constraints

- No new database tables or migrations unless existing models genuinely cannot support a required field. If a schema change appears unavoidable, stop and report the exact gap before modifying it.
- No new dependencies.
- No synthetic dataset regeneration.
- No actual trade execution or broker integration.
- No automatic proposal approval.
- No LLM involvement in financial calculations or constraint validation.
- No unrelated refactoring.
- Do not commit or push.

---

## RED Execution Output

Prior to production implementation, `tests/test_rebalancing_simulation_api.py` was executed, failing at collection due to missing classes and methods:

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.4.2, pluggy-1.7.0 -- E:\Yottaflex\portfolio-rebalancing-system\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: E:\Yottaflex\portfolio-rebalancing-system
configfile: pytest.ini
plugins: anyio-4.16.0
collecting ... collected 0 items / 1 error

=================================== ERRORS ====================================
__________ ERROR collecting tests/test_rebalancing_simulation_api.py __________
ImportError while importing test module 'E:\Yottaflex\portfolio-rebalancing-system\tests\test_rebalancing_simulation_api.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
tests\test_rebalancing_simulation_api.py:28: in <module>
    from app.services.rebalancing_service import (
E   ImportError: cannot import name 'ConstraintViolationError' from 'app.services.rebalancing_service' (E:\Yottaflex\portfolio-rebalancing-system\app\services\rebalancing_service.py)
=========================== short test summary info ===========================
ERROR tests/test_rebalancing_simulation_api.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
========================= 1 warning, 1 error in 1.03s =========================
```

---

## GREEN Execution Output

### 1. New Simulation and API Tests (`test_rebalancing_simulation_api.py`)

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.4.2, pluggy-1.7.0 -- E:\Yottaflex\portfolio-rebalancing-system\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: E:\Yottaflex\portfolio-rebalancing-system
configfile: pytest.ini
plugins: anyio-4.16.0
collecting ... collected 20 items

tests/test_rebalancing_simulation_api.py::test_simulation_applies_sells_and_buys_to_holdings_copy PASSED [  5%]
tests/test_rebalancing_simulation_api.py::test_simulation_cash_accounting_and_value_invariant PASSED [ 10%]
tests/test_rebalancing_simulation_api.py::test_simulation_preserves_lot_rounding_and_residual_drift PASSED [ 15%]
tests/test_rebalancing_simulation_api.py::test_gatekeeper_enforces_excluded_instrument_blocks_buy PASSED [ 20%]
tests/test_rebalancing_simulation_api.py::test_gatekeeper_enforces_max_position_weight_on_individual_positions PASSED [ 25%]
tests/test_rebalancing_simulation_api.py::test_gatekeeper_enforces_trade_value_limits_min_and_max PASSED [ 30%]
tests/test_rebalancing_simulation_api.py::test_gatekeeper_enforces_liquidity_limit_on_post_trade_cash_pct PASSED [ 35%]
tests/test_rebalancing_simulation_api.py::test_persistence_clean_proposal_pending_review PASSED [ 40%]
tests/test_rebalancing_simulation_api.py::test_persistence_unknown_price_freshness_never_auto_approves PASSED [ 45%]
tests/test_rebalancing_simulation_api.py::test_persistence_rollback_on_failure_no_partial_records PASSED [ 50%]
tests/test_rebalancing_simulation_api.py::test_api_create_proposal_success PASSED [ 55%]
tests/test_rebalancing_simulation_api.py::test_api_create_proposal_unknown_portfolio_404 PASSED [ 60%]
tests/test_rebalancing_simulation_api.py::test_api_create_proposal_missing_market_price_422 PASSED [ 65%]
tests/test_rebalancing_simulation_api.py::test_api_create_proposal_with_request_body_as_of_date PASSED [ 70%]
tests/test_rebalancing_simulation_api.py::test_simulation_rejects_or_flags_invalid_trade_input PASSED [ 75%]
tests/test_rebalancing_simulation_api.py::test_gatekeeper_enforces_min_position_weight PASSED [ 80%]
tests/test_rebalancing_simulation_api.py::test_gatekeeper_enforces_trade_quantity_limits_min_and_max PASSED [ 85%]
tests/test_rebalancing_simulation_api.py::test_gatekeeper_respects_effective_dates_and_open_ended_constraints PASSED [ 90%]
tests/test_rebalancing_simulation_api.py::test_api_create_proposal_hard_violation_returns_rejected_proposal PASSED [ 95%]
tests/test_rebalancing_simulation_api.py::test_api_create_proposal_unexpected_error_returns_safe_500 PASSED [100%]

======================= 20 passed, 2 warnings in 1.43s ========================
```

### 2. Phase 4.1 Rebalancing Service Tests (`test_rebalancing_service.py`)

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.4.2, pluggy-1.7.0 -- E:\Yottaflex\portfolio-rebalancing-system\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: E:\Yottaflex\portfolio-rebalancing-system
configfile: pytest.ini
plugins: anyio-4.16.0
collecting ... collected 19 items

tests/test_rebalancing_service.py::test_overweight_asset_class_generates_sell PASSED [  5%]
tests/test_rebalancing_service.py::test_underweight_asset_class_generates_buy PASSED [ 10%]
tests/test_rebalancing_service.py::test_sell_quantity_never_exceeds_existing_holding PASSED [ 15%]
tests/test_rebalancing_service.py::test_sell_quantities_are_integer_multiples_of_lot_size PASSED [ 21%]
tests/test_rebalancing_service.py::test_pro_rata_sell_allocation_is_deterministic PASSED [ 26%]
tests/test_rebalancing_service.py::test_existing_eligible_instruments_are_preferred_for_buys PASSED [ 31%]
tests/test_rebalancing_service.py::test_unheld_underweight_asset_class_selects_lowest_instrument_id PASSED [ 36%]
tests/test_rebalancing_service.py::test_excluded_instruments_are_never_recommended_for_purchase PASSED [ 42%]
tests/test_rebalancing_service.py::test_buy_quantities_obey_lot_size_multiples PASSED [ 47%]
tests/test_rebalancing_service.py::test_buy_sizing_accounts_for_fees_and_prevents_overdraft PASSED [ 52%]
tests/test_rebalancing_service.py::test_missing_applicable_fee_schedule_blocks_trade PASSED [ 57%]
tests/test_rebalancing_service.py::test_total_buy_outlay_never_exceeds_available_cash_flow PASSED [ 63%]
tests/test_rebalancing_service.py::test_cash_is_not_sold_as_ordinary_instrument PASSED [ 68%]
tests/test_rebalancing_service.py::test_identical_inputs_produce_identical_ordered_recommendations PASSED [ 73%]
tests/test_rebalancing_service.py::test_lot_size_rounding_leaves_explicit_residual_drift PASSED [ 78%]
tests/test_rebalancing_service.py::test_missing_prices_raise_error PASSED [ 84%]
tests/test_rebalancing_service.py::test_stale_price_uncertainty_is_diagnosed PASSED [ 89%]
tests/test_rebalancing_service.py::test_blocked_sell_does_not_contribute_proceeds_or_enable_buys PASSED [ 94%]
tests/test_rebalancing_service.py::test_historical_price_flags_requires_human_review PASSED [100%]

============================= 19 passed in 0.94s ==============================
```

### 3. Phase 3 Analytics & API Tests

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.4.2, pluggy-1.7.0 -- E:\Yottaflex\portfolio-rebalancing-system\.venv\Scripts\python.exe
rootdir: E:\Yottaflex\portfolio-rebalancing-system
configfile: pytest.ini
collected 29 items

tests/test_portfolio_analytics_service.py ...............
tests/test_portfolio_analytics_api.py ...............
======================= 29 passed, 2 warnings in 1.30s ========================
```

### 4. Full Test Suite (`pytest -q`)

```
======================= 317 passed, 3 warnings in 5.73s =======================
```

