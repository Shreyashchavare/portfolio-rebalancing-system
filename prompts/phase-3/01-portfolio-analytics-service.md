# Phase 3 — Portfolio Analytics Service

## Objective
Implement deterministic portfolio valuation, allocation analysis and target-drift calculations using persisted holdings, prices and effective target allocations.

## Core capabilities
- Value a portfolio as of a requested date.
- Value individual positions using the latest eligible market price on or before the requested date.
- Report missing prices explicitly.
- Calculate position and asset-class market values and weights.
- Retrieve target allocations effective on the requested date.
- Calculate actual-versus-target drift and identify overweight/underweight classes.
- Preserve rounding consistency and report residuals.
- Classify stale-price status and expose price age; unknown freshness must not be treated as fresh.

## Financial correctness
Use Decimal arithmetic for prices, quantities, values, percentages and drift. Do not invent missing prices, stale-price thresholds, trading calendars or default target allocations. A missing or unknown input must be surfaced as a diagnostic or error.

## Runtime target validation
Target allocations must be validated at the service boundary:
- Total target weight must equal 100%.
- Weights cannot be negative or exceed the allowed range.
- Duplicate asset-class targets must be rejected.
- Effective-date validity must be enforced.

The source archive's later correction added shared runtime validation and applied it to drift and proposal-generation paths.

## API scope
Expose:
- `GET /api/v1/portfolios/{portfolio_id}/valuation`
- `GET /api/v1/portfolios/{portfolio_id}/drift`

Support optional `as_of_date`; use the documented default when omitted. Return structured response schemas and safe errors: unknown portfolio (404), invalid/missing required data (422), and unexpected server errors (500 without internal details).
