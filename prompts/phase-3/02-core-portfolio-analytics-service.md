# Prompt P3-02 — Core Portfolio Analytics Service and Schemas

**AI Tool:** Antigravity  
**Phase:** 3 — Core Portfolio Analytics  
**Task:** Batch 3.1 — Core Portfolio Analytics Service and Schemas

## Prompt

# Phase 3.1 — Core Portfolio Analytics Service and Schemas

Repository: `E:\Yottaflex\portfolio-rebalancing-system`

## Objective

Implement the minimum production-ready portfolio analytics service by reusing existing calculation functions and database models.

## Existing implementation

Reuse these functions from `synthetic_data/calculations.py` wherever appropriate:

- `calculate_position_market_value`
- `calculate_portfolio_market_value`
- `calculate_asset_class_weights`
- `calculate_allocation_drift`

Existing models:

- Portfolio
- Holding
- Instrument
- MarketPrice
- TargetAllocation

Existing calculations use Decimal and four-decimal-place quantization.

Read the actual implementations before making changes. Do not duplicate existing functionality.

## 1. Pydantic schemas

Create `app/schemas/portfolio_analytics.py`.

Implement only the schemas needed for:

- Position valuation
- Asset-class allocation
- Allocation drift
- Portfolio valuation result

Include relevant identifiers, quantities, prices, market values, asset classes, current weights, target weights, percentage drift, and monetary drift.

Use Decimal for financial fields and appropriate Pydantic validation.

Avoid unnecessary schema complexity.

## 2. Portfolio analytics service

Create `app/services/portfolio_analytics_service.py`.

Implement a service that accepts the existing SQLAlchemy database session.

Required capabilities:

### A. Portfolio valuation

Implement `get_portfolio_valuation(portfolio_id, as_of_date)`.

- Retrieve the portfolio and its holdings.
- Resolve instrument details.
- Resolve the latest available market price on or before `as_of_date`.
- Calculate position market values.
- Calculate total portfolio value.
- Return the typed valuation schema.
- Handle unknown portfolio IDs explicitly.

### B. Missing and stale prices

- Never silently substitute zero for a missing market price.
- Define an explicit `MissingPriceError`.
- Detect stale prices using an existing documented threshold or policy if one exists.
- If no threshold is defined, expose price age and a stale-price diagnostic without inventing an arbitrary policy.
- Never silently treat an unpriced holding as a zero-value position.

### C. Asset-class allocation

- Calculate actual allocation percentages.
- Include asset classes with target allocations even if no holdings currently exist in those classes.
- Reuse existing calculation logic.
- Reconcile rounding residual against the largest allocation weight rather than arbitrarily selecting the first dictionary entry.

### D. Target allocation and drift

Implement `get_portfolio_drift(portfolio_id, as_of_date)`.

Select effective target allocations using:

`effective_from <= as_of_date`

and:

`effective_to IS NULL OR effective_to >= as_of_date`

Include both actual and target asset classes.

Calculate:

`percentage_drift = current_weight - target_weight`

`monetary_drift = percentage_drift / 100 * portfolio_market_value`

Interpretation:

- Positive drift: overweight, potential SELL.
- Negative drift: underweight, potential BUY.

Use Decimal throughout.

## 3. Tests — TDD mandatory

Create `tests/test_portfolio_analytics_service.py`.

Write tests before implementation and demonstrate RED.

Required coverage:

1. Correct position market value.
2. Correct total portfolio valuation.
3. Latest market price on or before as-of date.
4. Missing market price raises an explicit error.
5. Stale price is diagnosed correctly.
6. Effective target allocation date filtering.
7. Target asset class without holdings has negative drift.
8. Positive and negative monetary drift calculations.
9. Monetary drift reconciliation across asset classes.
10. Largest-weight rounding residual assignment.
11. Empty portfolio behavior.
12. Unknown portfolio handling.
13. Decimal precision preservation.

Use existing test fixtures and conventions where possible. Avoid duplicating large fixtures.

## Constraints

- Do not modify database models or migrations.
- Do not add dependencies.
- Do not implement API endpoints in this batch.
- Do not implement trade generation or rebalance execution.
- Do not introduce an arbitrary stale-price threshold.
- Do not weaken existing calculations or tests.
- Do not regenerate synthetic datasets.
- Do not commit or push.

## TDD execution

1. Inspect existing code and test conventions.
2. Write regression tests.
3. Run targeted tests and demonstrate RED.
4. Implement schemas and service.
5. Run targeted tests and demonstrate GREEN.
6. Run the complete test suite.
7. Inspect the final diff.

## Prompt history

Save this exact prompt and a concise RED/GREEN execution record in:

`prompts/phase-3/02-core-portfolio-analytics-service.md`

Create the directory if necessary.

## Deliverables

Report:

- Files created and modified.
- Functions implemented.
- Tests added.
- RED and GREEN results.
- Full-suite result.
- Missing/stale price behavior.
- Decimal and reconciliation verification.
- Elapsed time and remaining Phase 3 budget.
- Confirmation that no commit or push occurred.

---

## Actual Results

### RED Phase
- Created test suite `tests/test_portfolio_analytics_service.py` with 13 comprehensive test functions covering all required capabilities.
- Executed: `pytest tests/test_portfolio_analytics_service.py -v`
- Result: **13 failed in 0.56s** (All tests failed with `ModuleNotFoundError: No module named 'app.services.portfolio_analytics_service'`, proving clean RED state).

### Implementation
1. `app/schemas/portfolio_analytics.py`:
   - Defined `PositionValuation`, `AssetClassAllocation`, `AssetClassDrift`, `PortfolioValuationResult`, and `PortfolioDriftResult`.
   - Strictly typed all financial values as `Decimal`.
2. `app/services/portfolio_analytics_service.py`:
   - Implemented `PortfolioNotFoundError` and `MissingPriceError`.
   - Implemented `PortfolioAnalyticsService`:
     - `get_portfolio_valuation(portfolio_id, as_of_date)`: Resolves holdings as-of date, fetches latest market price on or before as-of date (raising `MissingPriceError` if missing), computes position valuations, diagnoses stale prices with price age, and reconciles rounding residual to the largest allocation weight.
     - `get_portfolio_drift(portfolio_id, as_of_date)`: Queries active target allocations (`effective_from <= as_of_date <= effective_to`), unions actual and target asset classes, computes percentage and monetary drift ($W_{\text{curr}} - W_{\text{tgt}}$ and $\Delta_{\$} = \text{Drift} \times V_{\text{portfolio}}$), and reconciles cross-asset-class monetary drift.
3. `app/schemas/__init__.py` & `app/services/__init__.py`:
   - Exported public models and service interfaces.

### GREEN Phase
- Executed: `pytest tests/test_portfolio_analytics_service.py -v`
- Result: **13 passed in 0.54s** (100% passing).

### Full Suite Verification
- Executed: `pytest -v`
- Result: **262 passed, 1 warning in 4.81s** (0 regressions across all 262 repository tests).

