# Prompt P4-02 — Deterministic Rebalancing Trade Generation

**AI Tool:** Antigravity  
**Phase:** 4 — Rebalancing Engine  
**Task:** Batch 4.1 — Deterministic Rebalancing Trade Generation

## Prompt

# Phase 4.1 — Deterministic Rebalancing Trade Generation

Repository: `E:\Yottaflex\portfolio-rebalancing-system`

## Objective

Implement a deterministic service that converts portfolio allocation drift into proposed BUY and SELL recommendations.

The service must reuse existing portfolio analytics, financial calculations, models, fee schedules, and constraints. It must not execute or persist actual trades in this batch.

## Step 1 — Inspect Existing Contracts

Before editing, inspect:
- `app/models/holding.py`
- `app/models/instrument.py`
- `app/models/market_price.py`
- `app/models/portfolio.py`
- `app/models/target_allocation.py`
- `app/models/trade.py`
- `app/models/fee_schedule.py`
- `app/models/constraint.py`
- `app/services/portfolio_analytics_service.py`
- `app/schemas/portfolio_analytics.py`
- `synthetic_data/calculations.py`
- Relevant generators and tests.

Confirm exact field names, enum values, active/effective date semantics, and fee matching behavior. Do not guess model fields.

## Step 2 — Define the Trade Generation Contract

Create:
- `app/schemas/rebalancing.py`
- `app/services/rebalancing_service.py`
- `tests/test_rebalancing_service.py`

Implement a service method equivalent to:

`generate_rebalance_trades(portfolio_id, as_of_date)`

Return a deterministic, structured in-memory recommendation result containing:
- Portfolio and as-of date.
- Starting portfolio value.
- Starting cash value.
- Proposed BUY/SELL recommendations.
- Instrument, quantity, price, notional, fee, fee schedule reference, and trade side.
- Remaining cash after proposed trades and fees.
- Unresolved allocation drift / residuals.
- Explicit diagnostics or validation failures.

Use existing Pydantic and service conventions.

## Step 3 — Write Tests First (RED)

Cover at least:

1. Overweight asset class generates SELL recommendations.
2. Underweight asset class generates BUY recommendations.
3. Sell quantity never exceeds the existing holding.
4. Sell quantities are integer multiples of `Instrument.lot_size`.
5. Pro-rata sell allocation across existing positions is deterministic.
6. Existing eligible instruments are preferred for buys.
7. When no eligible instrument is held in an underweight asset class, select the lowest `instrument_id` among active, eligible, non-excluded instruments.
8. Excluded instruments are never recommended for purchase.
9. Buy quantities obey lot-size multiples.
10. Buy sizing accounts for fees, not only trade notional.
11. Missing applicable fee schedule is explicitly reported as a failure/block; never silently assume zero fees.
12. Total buy notional plus buy fees never exceeds starting cash plus net sell proceeds.
13. Cash is not sold as an ordinary instrument.
14. Identical inputs produce identical ordered recommendations.
15. Lot-size rounding leaves explicit residual drift rather than creating fractional-lot trades.
16. Missing prices or unknown price freshness are not silently interpreted as safe.

Demonstrate RED before implementation.

## Step 4 — Implement Deterministic Generation

### A. Reuse existing calculations
Reuse:
- `PortfolioAnalyticsService.get_portfolio_valuation`
- `PortfolioAnalyticsService.get_portfolio_drift`
- `calculate_trade_notional`
- `match_fee_tier`
- `calculate_trade_fee`

### B. SELL generation
- Generate sells from overweight asset classes.
- Never sell more than the current holding quantity.
- Never generate a cash instrument as a normal SELL trade.
- Distribute sells pro-rata across eligible held non-cash positions in the overweight asset class.
- Round quantities down to valid lot-size multiples.
- Use deterministic ordering and deterministic residual handling.
- Never produce negative or zero quantity recommendations.

### C. BUY generation
- Generate buys for underweight asset classes.
- Prefer eligible existing holdings in that asset class.
- If none exist, select the lowest `instrument_id` among active, eligible, non-excluded instruments in that asset class.
- Do not purchase excluded instruments.
- Respect lot-size multiples.
- Calculate fees before finalizing quantities.
- Reserve sufficient cash for both notional and fees.
- Never allow negative simulated cash.

### D. Cash and fees
Cash is represented by existing CASH holdings, not a separate portfolio balance field.
Calculate available cash as: `starting_cash + sell_proceeds - sell_fees - buy_notionals - buy_fees`.
Use the actual applicable fee schedule and existing tier-matching conventions.
If an applicable fee schedule is missing, do not generate an apparently valid zero-fee trade. Return an explicit diagnostic or blocked recommendation.

### E. Price freshness
- Preserve price-age diagnostics.
- Do not treat `is_stale=None` as fresh.
- Do not invent a stale-price threshold or trading calendar.
- If price freshness is unknown, make the uncertainty explicit in the recommendation result.
- Do not silently use missing prices.

### F. Residual allocation
Lot-size rounding can make exact target matching impossible. Preserve and report the remaining drift. Do not violate lot sizes or holding limits merely to force allocation weights to match targets.

---

## RED Execution Record

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_rebalancing_service.py -v
```

Output:
```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.4.2, pluggy-1.7.0 -- E:\Yottaflex\portfolio-rebalancing-system\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: E:\Yottaflex\portfolio-rebalancing-system
configfile: pytest.ini
plugins: anyio-4.16.0
collecting ... collected 0 items / 1 error

=================================== ERRORS ====================================
_____________ ERROR collecting tests/test_rebalancing_service.py ______________
ImportError while importing test module 'E:\Yottaflex\portfolio-rebalancing-system\tests\test_rebalancing_service.py'.
Traceback:
tests\test_rebalancing_service.py:25: in <module>
    from app.services.rebalancing_service import RebalancingService
E   ModuleNotFoundError: No module named 'app.services.rebalancing_service'
=========================== short test summary info ===========================
ERROR tests/test_rebalancing_service.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
============================== 1 error in 0.65s ===============================
```

---

## GREEN Execution Record

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_rebalancing_service.py -v
```

Output:
```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.4.2, pluggy-1.7.0 -- E:\Yottaflex\portfolio-rebalancing-system\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: E:\Yottaflex\portfolio-rebalancing-system
configfile: pytest.ini
plugins: anyio-4.16.0
collecting ... collected 17 items

tests/test_rebalancing_service.py::test_overweight_asset_class_generates_sell PASSED [  5%]
tests/test_rebalancing_service.py::test_underweight_asset_class_generates_buy PASSED [ 11%]
tests/test_rebalancing_service.py::test_sell_quantity_never_exceeds_existing_holding PASSED [ 17%]
tests/test_rebalancing_service.py::test_sell_quantities_are_integer_multiples_of_lot_size PASSED [ 23%]
tests/test_rebalancing_service.py::test_pro_rata_sell_allocation_is_deterministic PASSED [ 29%]
tests/test_rebalancing_service.py::test_existing_eligible_instruments_are_preferred_for_buys PASSED [ 35%]
tests/test_rebalancing_service.py::test_unheld_underweight_asset_class_selects_lowest_instrument_id PASSED [ 41%]
tests/test_rebalancing_service.py::test_excluded_instruments_are_never_recommended_for_purchase PASSED [ 47%]
tests/test_rebalancing_service.py::test_buy_quantities_obey_lot_size_multiples PASSED [ 52%]
tests/test_rebalancing_service.py::test_buy_sizing_accounts_for_fees_and_prevents_overdraft PASSED [ 58%]
tests/test_rebalancing_service.py::test_missing_applicable_fee_schedule_blocks_trade PASSED [ 64%]
tests/test_rebalancing_service.py::test_total_buy_outlay_never_exceeds_available_cash_flow PASSED [ 70%]
tests/test_rebalancing_service.py::test_cash_is_not_sold_as_ordinary_instrument PASSED [ 76%]
tests/test_rebalancing_service.py::test_identical_inputs_produce_identical_ordered_recommendations PASSED [ 82%]
tests/test_rebalancing_service.py::test_lot_size_rounding_leaves_explicit_residual_drift PASSED [ 88%]
tests/test_rebalancing_service.py::test_missing_prices_raise_error PASSED [ 94%]
tests/test_rebalancing_service.py::test_stale_price_uncertainty_is_diagnosed PASSED [100%]

============================= 17 passed in 0.86s ==============================
```

---

## Full Test Suite Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Output:
```
.................................................................................................... [ 33%]
.................................................................................................... [ 67%]
...........................................................................................          [100%]
295 passed, 2 warnings in 5.36s
```

