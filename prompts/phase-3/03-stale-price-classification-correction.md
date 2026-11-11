# Prompt P3-03 — Correct Stale-Price Classification

**AI Tool:** Antigravity  
**Phase:** 3 — Core Portfolio Analytics  
**Task:** Batch 3.1 Verification — Correct Stale-Price Classification

## Prompt

# Phase 3.1 Verification — Correct Stale-Price Classification

Repository: `E:\Yottaflex\portfolio-rebalancing-system`

## Problem

The current analytics service marks every price with `price_date < as_of_date` as stale.

This incorrectly treats any historical price as stale, including a valid previous trading-day price when the as-of date is a weekend or market holiday.

The audit confirmed that no explicit stale-price threshold or trading-calendar policy exists in the project.

## Requirements

1. Inspect `app/services/portfolio_analytics_service.py`, `app/schemas/portfolio_analytics.py`, and `tests/test_portfolio_analytics_service.py`.
2. Write regression tests first.
3. Demonstrate RED.
4. Correct stale-price classification:
   - Always calculate and expose `price_age_days`.
   - If `price_date == as_of_date`, classify the price as not stale.
   - If `price_date < as_of_date` and no staleness policy is configured, classify staleness as unknown (`None`).
   - Do not invent a threshold or trading calendar.
   - Preserve useful price-age diagnostics.
   - Preserve `MissingPriceError` for missing prices.
5. Update the Pydantic schema to support an unknown stale status (`bool | None`) if required.
6. Run targeted tests and demonstrate GREEN.
7. Run the complete suite using `python -m pytest -q` with the project's active Python environment.
8. Save this prompt and concise RED/GREEN execution record in `prompts/phase-3/03-stale-price-classification-correction.md`.

## Constraints

- No database model or migration changes.
- No new dependencies.
- No unrelated refactoring.
- Do not modify synthetic datasets.
- Do not commit or push.

## Deliverables

Report changed files, RED/GREEN results, full-suite result, and final stale-price classification behavior.

---

## Actual Results

### RED Phase
- Updated `test_stale_price_diagnosed_correctly` in `tests/test_portfolio_analytics_service.py` to assert that when `price_date < as_of_date` and no policy is configured, `pos.is_stale is None` (unknown status).
- Added `test_current_price_classified_as_not_stale` asserting `pos.is_stale is False` and `pos.diagnostic is None` when `price_date == as_of_date`.
- Executed:
  ```powershell
  pytest tests/test_portfolio_analytics_service.py -k "test_stale_price or test_current_price" -v
  ```
- Result: **1 failed, 1 passed, 12 deselected**
  - Failure: `assert True is None` on `test_stale_price_diagnosed_correctly` (current code was returning `True`).

### Implementation
1. `app/schemas/portfolio_analytics.py`:
   - Updated `PositionValuation.is_stale` type to `Optional[bool] = None`.
2. `app/services/portfolio_analytics_service.py`:
   - Refactored price staleness evaluation:
     - `price_age_days = (as_of_date - latest_price_rec.price_date).days`
     - If `price_age_days == 0`: `is_stale = False`, `diagnostic = None`.
     - If `price_age_days > 0`: `is_stale = None` (unknown, since no calendar/threshold policy exists), preserving descriptive diagnostic `f"Price as of {latest_price_rec.price_date} is {price_age_days} day(s) old relative to as-of date {as_of_date}"`.
     - Preserved `MissingPriceError` when no price exists on or before `as_of_date`.

### GREEN Phase
- Executed targeted tests:
  ```powershell
  pytest tests/test_portfolio_analytics_service.py -v
  ```
- Result: **14 passed in 0.56s** (100% passing).

### Full Suite Verification
- Executed active virtual environment suite:
  ```powershell
  .\.venv\Scripts\python.exe -m pytest -q
  ```
- Result: **263 passed, 1 warning in 4.42s** (0 regressions across entire test suite).

