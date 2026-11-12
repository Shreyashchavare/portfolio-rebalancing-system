# Phase 4 — Simulation, Constraint Gatekeeper, Persistence and API

## Post-trade simulation
- Simulate proposed trades against an isolated in-memory copy of holdings.
- Apply only executable trades.
- Adjust cash for sell proceeds, sell fees, buy notional and buy fees.
- Recalculate post-trade values, asset-class weights and drift.
- Preserve Decimal precision, lot-size rules and residual drift.
- Keep simulated cash nonnegative.
- Never mutate actual holdings during proposal generation.
- Reconcile post-trade portfolio value with pre-trade value less executable fees.

## Constraint gatekeeper
Evaluate active constraints effective on the as-of date and resolve scope correctly. The source requirements cover:
`EXCLUDED_INSTRUMENT`, `MAX_POSITION_WEIGHT`, `MIN_POSITION_WEIGHT`, `MIN_TRADE_VALUE`, `MAX_TRADE_VALUE`, `MIN_TRADE_QUANTITY`, `MAX_TRADE_QUANTITY` and `LIQUIDITY_LIMIT`.

- Evaluate position limits against individual instrument positions.
- Evaluate trade limits against each proposed trade.
- Evaluate liquidity against post-trade cash percentage.
- Hard violations block affected trades and prevent approval.
- Soft violations remain visible as warnings.
- A blocked sell must not finance buys.

## Persistence and API
Persist a proposal and its trades in one transaction; roll back on failure and avoid partial records. Clean proposals enter `PENDING_REVIEW` with `review_decision=PENDING`. Hard violations reject the proposal and block affected trades. Unknown price freshness must require human review.

Endpoint:
`POST /api/v1/portfolios/{portfolio_id}/rebalance/proposals`

Return proposal, trades, simulation, findings and review status. Do not execute trades or automatically approve proposals.
