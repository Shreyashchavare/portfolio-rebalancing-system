# Phase 3 — Rebalance Trigger Evaluation and Verification

## Trigger semantics
Evaluate rebalance triggers only from explicitly configured, active and effective `Constraint` records scoped to the portfolio. Do not invent a default threshold or infer a trigger from unknown price freshness.

When no applicable threshold policy exists, return an explicit `NOT_CONFIGURED`/`UNKNOWN` result and leave `rebalance_required` unset rather than guessing.

## API and test expectations
- Valuation endpoint returns portfolio value and position details.
- Drift endpoint returns target/actual comparisons, drift metrics and trigger evaluation.
- Accept an optional as-of date.
- Unknown portfolio returns 404.
- Missing market price returns a clear client-facing 422.
- Invalid date returns 422.
- Unexpected errors return a safe 500 response.

## Verification approach
Use service and API tests for:
- Valuation arithmetic and position-level details.
- Price selection and stale/missing-price behavior.
- Effective target selection and drift.
- Trigger configured, breached, not breached and not configured cases.
- Invalid target allocations and error mapping.

## Historical correction note
The source archive includes a stale-price classification correction and a final financial-logic review. The later project audit also reported a regression test for exact price-age date pairs and runtime rejection of invalid allocations. Preserve these behaviors when changing analytics code.
