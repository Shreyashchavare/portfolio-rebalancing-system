# Phase 3.0 — Portfolio Analytics Audit (READ ONLY)

Repository: `E:\Yottaflex\portfolio-rebalancing-system`

## Objective
Audit the existing portfolio analytics implementation and identify the minimum work required to complete Phase 3.

## Inspect these files
- `synthetic_data/calculations.py`
- `tests/test_calculations.py`
- Relevant models:
  - Holding
  - Instrument
  - MarketPrice
  - Portfolio
  - TargetAllocation
- Any existing analytics-related services or schemas.

## Audit the following capabilities

1. Position market value calculation.
2. Total portfolio valuation.
3. Asset-class allocation weights.
4. Target allocation comparison.
5. Allocation drift calculation.
6. Trade notional and fee calculations (identify existing functionality; do not duplicate).
7. Decimal precision and rounding.
8. Missing and stale market-price handling.
9. Zero-quantity and empty-portfolio handling.
10. Reconciliation of portfolio weights to 100%.

## Requirements

- Read existing code and tests before making recommendations.
- Identify implemented, partially implemented and missing capabilities.
- Identify correctness issues and uncovered edge cases.
- Check whether financial calculations consistently use Decimal.
- Identify existing functions that later phases can reuse.
- Map each gap to the smallest necessary code/test change.
- Recommend no more than 2–3 implementation batches.

## Strict constraints

- READ ONLY. Do not edit or create files.
- Do not refactor existing code.
- Do not add dependencies.
- Do not change database models.
- Do not regenerate synthetic data.
- Do not commit or push.

## Deliverables

Provide:
1. Files inspected.
2. Existing functions and their responsibilities.
3. Implemented / partial / missing capability table.
4. Critical correctness issues.
5. Missing test coverage.
6. Minimum implementation plan with time estimates.
7. Explicit confirmation that no files were modified.