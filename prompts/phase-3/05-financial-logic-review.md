# Prompt P3-05 — Final Financial Logic Review & Position Weight Correction

**AI Tool:** Antigravity  
**Phase:** 3 — Core Portfolio Analytics  
**Task:** Batch 3.2 — Final Financial Logic Review (Position vs Asset-Class Weight Disambiguation)

## Prompt

# Phase 3.2 — Final Financial Logic Review (Read-Only Unless Defect Found)

Review:
- `app/services/portfolio_analytics_service.py`
- `app/schemas/portfolio_analytics.py`
- `app/api/v1/analytics.py`
- `app/models/constraint.py`
- `tests/test_portfolio_analytics_api.py`

Verify:

1. `MAX_POSITION_WEIGHT` and `MIN_POSITION_WEIGHT` semantics against the actual Constraint model, generators, and existing project documentation.
2. Confirm whether the evaluator is checking instrument-level weights or asset-class-level weights. It must not confuse the two.
3. Confirm `effective_to=None` means no expiry, if supported by the existing model.
4. Confirm stale-price status `None` remains unknown and is not silently interpreted as fresh.
5. Confirm `as_of_date` behavior and effective constraint filtering.
6. Confirm Decimal comparisons and financial precision.
7. Confirm API exception handling does not hide expected errors or leak internal details.

If all checks pass, make no changes and report evidence with relevant code references.

If a defect exists:
- Add a focused regression test first.
- Demonstrate RED.
- Apply the smallest correction.
- Demonstrate GREEN.
- Run the complete suite with:
  `.\.venv\Scripts\python.exe -m pytest -q`
- Save any additional task-specific prompt and RED/GREEN record under `prompts/phase-3/`.
- Do not modify models, migrations, dependencies, or unrelated code.
- Do not commit or push.

Return a concise review report with findings and test results.

---

## Defect Identified

In `evaluate_rebalance_trigger`, the evaluator was iterating over `valuation.asset_classes` (`AssetClassAllocation`) and comparing `ac.current_weight` to `c.threshold_value`.

However, `MAX_POSITION_WEIGHT` ("Max Single Position Weight", template description: "Maximum allowed weight for any single asset position in the portfolio", generator description: `Portfolio {p_id} single position cap`) governs individual instrument-level positions (`PositionValuation`), NOT aggregated asset-class weights. Evaluating asset-class weights caused false-positive rebalancing triggers whenever an asset class (e.g. EQUITY composed of multiple small holdings) exceeded the position cap.

---

## RED Execution Record

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_portfolio_analytics_api.py -k "test_max_position_weight_evaluates_individual_positions_not_asset_classes" -v
```

Output:
```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.4.2, pluggy-1.7.0 -- E:\Yottaflex\portfolio-rebalancing-system\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: E:\Yottaflex\portfolio-rebalancing-system
configfile: pytest.ini
plugins: anyio-4.16.0
collecting ... collected 14 items / 13 deselected / 1 selected

tests/test_portfolio_analytics_api.py::test_max_position_weight_evaluates_individual_positions_not_asset_classes FAILED [100%]

================================== FAILURES ===================================
__ test_max_position_weight_evaluates_individual_positions_not_asset_classes __
    ...
>       assert trigger["status"] == "NOT_TRIGGERED"
E       AssertionError: assert 'TRIGGERED' == 'NOT_TRIGGERED'
E         - NOT_TRIGGERED
E         + TRIGGERED
================= 1 failed, 13 deselected, 1 warning in 0.86s =================
```

---

## GREEN Execution Record

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_portfolio_analytics_api.py -v
```

Output:
```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.4.2, pluggy-1.7.0 -- E:\Yottaflex\portfolio-rebalancing-system\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: E:\Yottaflex\portfolio-rebalancing-system
configfile: pytest.ini
plugins: anyio-4.16.0
collecting ... collected 15 items

tests/test_portfolio_analytics_api.py::test_get_portfolio_valuation_success PASSED [  6%]
tests/test_portfolio_analytics_api.py::test_get_portfolio_valuation_optional_as_of_date PASSED [ 13%]
tests/test_portfolio_analytics_api.py::test_get_portfolio_drift_success PASSED [ 20%]
tests/test_portfolio_analytics_api.py::test_unknown_portfolio_returns_404 PASSED [ 26%]
tests/test_portfolio_analytics_api.py::test_missing_market_price_returns_client_error PASSED [ 33%]
tests/test_portfolio_analytics_api.py::test_invalid_date_format_returns_422 PASSED [ 40%]
tests/test_portfolio_analytics_api.py::test_rebalance_trigger_not_configured_when_no_policy_exists PASSED [ 46%]
tests/test_portfolio_analytics_api.py::test_rebalance_trigger_triggered_when_configured_constraint_breached PASSED [ 53%]
tests/test_portfolio_analytics_api.py::test_rebalance_trigger_not_triggered_when_within_configured_constraint PASSED [ 60%]
tests/test_portfolio_analytics_api.py::test_rebalance_trigger_inactive_or_expired_constraint_ignored PASSED [ 66%]
tests/test_portfolio_analytics_api.py::test_rebalance_trigger_min_weight_breach PASSED [ 73%]
tests/test_portfolio_analytics_api.py::test_empty_portfolio_valuation_via_api PASSED [ 80%]
tests/test_portfolio_analytics_api.py::test_unexpected_error_returns_500_without_leak PASSED [ 86%]
tests/test_portfolio_analytics_api.py::test_max_position_weight_evaluates_individual_positions_not_asset_classes PASSED [ 93%]
tests/test_portfolio_analytics_api.py::test_max_position_weight_breach_identifies_specific_breaching_positions PASSED [100%]

======================= 15 passed, 2 warnings in 1.04s ========================
```

---

## Full Test Suite Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Output:
```
.................................................................................................... [ 35%]
.................................................................................................... [ 71%]
..............................................................................                       [100%]
278 passed, 2 warnings in 4.91s
```

