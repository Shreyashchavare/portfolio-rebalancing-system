# Prompt P3-04 — Portfolio Analytics API and Rebalance Trigger Evaluation

**AI Tool:** Antigravity  
**Phase:** 3 — Core Portfolio Analytics  
**Task:** Batch 3.2 — Portfolio Analytics API and Rebalance Trigger Evaluation

## Prompt

# Phase 3.2 — Portfolio Analytics API and Rebalance Trigger Evaluation

Repository: `E:\Yottaflex\portfolio-rebalancing-system`

## Objective

Expose the completed portfolio analytics service through FastAPI and add a deterministic rebalance-trigger evaluation using only existing, explicitly configured project policies.

## Step 1 — Inspect Before Editing

Inspect:
- `app/main.py`
- `app/api/`
- `app/database/`
- `app/services/portfolio_analytics_service.py`
- `app/schemas/portfolio_analytics.py`
- Existing models and constraints relevant to rebalance thresholds.
- Existing API and database dependency patterns.
- Existing API and integration tests.

Identify the established router registration, session dependency, response schema, and error-handling conventions.

Do not introduce a parallel pattern if an existing one can be reused.

## Step 2 — Write Tests First (RED)

Add tests for:

1. `GET /api/v1/portfolios/{portfolio_id}/valuation`
   - Returns the portfolio valuation and position details.
   - Accepts an optional `as_of_date` query parameter.
   - Defaults to current date if omitted.

2. `GET /api/v1/portfolios/{portfolio_id}/drift`
   - Returns the target asset-class comparisons, drift metrics, and deterministic rebalance-trigger status.
   - Accepts an optional `as_of_date` query parameter.
   - Defaults to current date if omitted.

3. Error handling:
   - Unknown portfolio -> HTTP 404
   - Missing market price -> client-facing error (HTTP 422 with MissingPriceError detail)
   - Invalid date format -> HTTP 422 (FastAPI standard)
   - Internal or unexpected errors -> HTTP 500 without leaking stack traces or database errors.

4. Deterministic rebalance-trigger evaluation:
   - Query existing applicable `Constraint` records (`scope_type == 'PORTFOLIO'`, `scope_reference_id == portfolio_id`, `is_active == True`, `effective_from <= as_of_date <= effective_to`).
   - If no threshold policy exists, return an explicit `NOT_CONFIGURED` / `UNKNOWN` status (`rebalance_required = None`).
   - Do NOT invent default thresholds or trading calendars; do not infer decisions from unknown stale prices; do not use LLMs.

Run tests and demonstrate RED.

## Step 3 — Minimal Implementation (GREEN)

1. Add `RebalanceTriggerEvaluation` schema and include in `PortfolioDriftResult`.
2. Add deterministic rebalance-trigger evaluation against active `Constraint` records in `PortfolioAnalyticsService`.
3. Create `app/api/v1/analytics.py` implementing `/valuation` and `/drift` endpoints with `get_db` dependency injection.
4. Register router in `app/main.py`.
5. Run tests and demonstrate GREEN.
6. Run the complete test suite.
7. Save prompt and execution record to `prompts/phase-3/04-portfolio-analytics-api.md`.

---

## RED Execution Record

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
collecting ... collected 9 items

tests/test_portfolio_analytics_api.py::test_get_portfolio_valuation_success FAILED [ 11%]
tests/test_portfolio_analytics_api.py::test_get_portfolio_valuation_optional_as_of_date FAILED [ 22%]
tests/test_portfolio_analytics_api.py::test_get_portfolio_drift_success FAILED [ 33%]
tests/test_portfolio_analytics_api.py::test_unknown_portfolio_returns_404 FAILED [ 44%]
tests/test_portfolio_analytics_api.py::test_missing_market_price_returns_client_error FAILED [ 55%]
tests/test_portfolio_analytics_api.py::test_invalid_date_format_returns_422 FAILED [ 66%]
tests/test_portfolio_analytics_api.py::test_rebalance_trigger_not_configured_when_no_policy_exists FAILED [ 77%]
tests/test_portfolio_analytics_api.py::test_rebalance_trigger_triggered_when_configured_constraint_breached FAILED [ 88%]
tests/test_portfolio_analytics_api.py::test_rebalance_trigger_not_triggered_when_within_configured_constraint FAILED [100%]

================================== FAILURES ===================================
FAILED tests/test_portfolio_analytics_api.py::test_get_portfolio_valuation_success - assert 404 == 200
FAILED tests/test_portfolio_analytics_api.py::test_get_portfolio_valuation_optional_as_of_date - assert 404 == 200
FAILED tests/test_portfolio_analytics_api.py::test_get_portfolio_drift_success - assert 404 == 200
FAILED tests/test_portfolio_analytics_api.py::test_unknown_portfolio_returns_404 - AssertionError: assert 'Portfolio not found' in 'Not Found'
FAILED tests/test_portfolio_analytics_api.py::test_missing_market_price_returns_client_error - assert 404 == 422
FAILED tests/test_portfolio_analytics_api.py::test_invalid_date_format_returns_422 - assert 404 == 422
FAILED tests/test_portfolio_analytics_api.py::test_rebalance_trigger_not_configured_when_no_policy_exists - assert 404 == 200
FAILED tests/test_portfolio_analytics_api.py::test_rebalance_trigger_triggered_when_configured_constraint_breached - assert 404 == 200
FAILED tests/test_portfolio_analytics_api.py::test_rebalance_trigger_not_triggered_when_within_configured_constraint - assert 404 == 200
======================== 9 failed, 1 warning in 0.99s =========================
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
collecting ... collected 13 items

tests/test_portfolio_analytics_api.py::test_get_portfolio_valuation_success PASSED [  7%]
tests/test_portfolio_analytics_api.py::test_get_portfolio_valuation_optional_as_of_date PASSED [ 15%]
tests/test_portfolio_analytics_api.py::test_get_portfolio_drift_success PASSED [ 23%]
tests/test_portfolio_analytics_api.py::test_unknown_portfolio_returns_404 PASSED [ 30%]
tests/test_portfolio_analytics_api.py::test_missing_market_price_returns_client_error PASSED [ 38%]
tests/test_portfolio_analytics_api.py::test_invalid_date_format_returns_422 PASSED [ 46%]
tests/test_portfolio_analytics_api.py::test_rebalance_trigger_not_configured_when_no_policy_exists PASSED [ 53%]
tests/test_portfolio_analytics_api.py::test_rebalance_trigger_triggered_when_configured_constraint_breached PASSED [ 61%]
tests/test_portfolio_analytics_api.py::test_rebalance_trigger_not_triggered_when_within_configured_constraint PASSED [ 69%]
tests/test_portfolio_analytics_api.py::test_rebalance_trigger_inactive_or_expired_constraint_ignored PASSED [ 76%]
tests/test_portfolio_analytics_api.py::test_rebalance_trigger_min_weight_breach PASSED [ 84%]
tests/test_portfolio_analytics_api.py::test_empty_portfolio_valuation_via_api PASSED [ 92%]
tests/test_portfolio_analytics_api.py::test_unexpected_error_returns_500_without_leak PASSED [100%]

======================= 13 passed, 2 warnings in 1.08s ========================
```

---

## Full Test Suite Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Output:
```
.................................................................................................... [ 36%]
.................................................................................................... [ 72%]
............................................................................                         [100%]
276 passed, 2 warnings in 5.88s
```

