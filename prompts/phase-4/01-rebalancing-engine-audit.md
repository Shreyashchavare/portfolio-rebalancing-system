# Prompt P4-01 — Rebalancing Engine Read-Only Audit

**AI Tool:** Antigravity  
**Phase:** 4 — Rebalancing Engine  
**Task:** Phase 4.0 — Rebalancing Engine Read-Only Audit

## Prompt

# Phase 4.0 — Rebalancing Engine Read-Only Audit

Repository: `E:\Yottaflex\portfolio-rebalancing-system`

## Objective

Audit the existing project to determine exactly what is required to implement a deterministic, constraint-aware portfolio rebalancing engine.

This is an inspection-only task. Do not modify production code, tests, models, migrations, dependencies, datasets, or Git history.

## 1. Inspect Existing Implementation

Inspect these areas:

### Database models
- `app/models/holding.py`
- `app/models/instrument.py`
- `app/models/market_price.py`
- `app/models/portfolio.py`
- `app/models/target_allocation.py`
- `app/models/trade.py`
- `app/models/rebalance_proposal.py`
- `app/models/fee_schedule.py`
- `app/models/constraint.py`

### Existing calculations and services
- `synthetic_data/calculations.py`
- `app/services/portfolio_analytics_service.py`
- `app/schemas/portfolio_analytics.py`
- Existing service and schema package exports.

### Existing tests and data
- `tests/test_calculations.py`
- `tests/test_portfolio_analytics_service.py`
- `tests/test_portfolio_analytics_api.py`
- Relevant model tests.
- Synthetic generators for holdings, constraints, fees, proposals and trades.
- Data dictionary and Phase 2 documentation.

## 2. Determine Existing Contracts

Document:

1. How current holdings and market values are calculated.
2. How target allocations and drift are represented.
3. How trade quantities, notionals and fees are calculated.
4. How fee schedules are matched to trades.
5. How minimum trade sizes are represented, if supported.
6. How excluded instruments are represented.
7. How available cash is represented and calculated.
8. How buy and sell trades are represented in the Trade model.
9. How RebalanceProposal relates to trades and portfolio state.
10. Which constraints can be enforced using the existing schema.
11. Whether proposal lifecycle/status fields already exist.
12. Whether existing logic supports post-trade portfolio simulation.

Do not assume a feature exists merely because it appears in the original project requirements. Verify the actual implementation.

## 3. Identify Financial and Engineering Gaps

Evaluate these required scenarios:

- Portfolio allocation differs from target allocation.
- Sell quantities never exceed existing holdings.
- Excluded instruments are never recommended.
- Buy trades never exceed available cash.
- Fees are calculated and included.
- Minimum trade sizes are respected.
- Position and portfolio constraints are enforced.
- Post-trade holdings and asset-class allocations are recalculated.
- Financial calculations use Decimal, not float.
- Rebalancing produces deterministic results for identical inputs.
- Missing or unknown market-price freshness is not silently treated as safe.

Identify any ambiguous business rules that cannot be safely inferred from existing models.

## 4. Recommend Implementation Batches

Recommend the smallest practical implementation plan:

- Batch 4.1: deterministic trade generation.
- Batch 4.2: constraint validation and post-trade simulation.

For each batch specify:
- Exact files likely to change.
- Existing functions and models to reuse.
- Missing functionality.
- Required regression tests.
- Any schema/model changes that may be unavoidable.

Keep the existing architecture. Avoid unnecessary abstractions and dependencies.

## 5. Required Deliverable

Create:
`prompts/phase-4/01-rebalancing-engine-audit.md`

---

## Audit Findings Summary

### 1. Existing Contracts & Capabilities
1. **Holdings & Valuation**: Handled by `PortfolioAnalyticsService.get_portfolio_valuation(portfolio_id, as_of_date)` using latest prices on or before `as_of_date` via `calculate_position_market_value` (Decimal arithmetic, 4 decimal places).
2. **Target Allocation & Drift**: Handled by `PortfolioAnalyticsService.get_portfolio_drift(portfolio_id, as_of_date)` using `TargetAllocation` records with active date filtering (`effective_from <= as_of_date <= effective_to`). Drift exposes monetary drift, percentage drift, and directional action signal (`BUY`/`SELL`/`HOLD`).
3. **Trade Math & Fees**: Handled by `synthetic_data/calculations.py`: `calculate_trade_notional` and `calculate_trade_fee` with bps, fixed fees, and min/max clamps. Tier selection is provided by `match_fee_tier`.
4. **Constraints Schema**: `app/models/constraint.py` provides 8 types: `MAX_POSITION_WEIGHT`, `MIN_POSITION_WEIGHT`, `MIN_TRADE_VALUE`, `MAX_TRADE_VALUE`, `MIN_TRADE_QUANTITY`, `MAX_TRADE_QUANTITY`, `EXCLUDED_INSTRUMENT`, and `LIQUIDITY_LIMIT`, with `HARD` and `SOFT` severities.
5. **Cash Architecture**: No separate cash column exists; cash is modeled as a `Holding` referencing an instrument with `asset_class == 'CASH'` (e.g. `CSH-USD-MM`, price $1.0000).
6. **Proposal & Trade Lifecycle**: `RebalanceProposal` and `Trade` models already contain all required lifecycle fields (`DRAFT`, `PENDING_REVIEW`, `APPROVED`, `REJECTED`, and trade status `PROPOSED`, `BLOCKED`, `APPROVED`, `REJECTED`).
7. **Post-Trade Simulation**: **Non-existent**. No existing production function or service calculates post-trade holding states or validates post-trade allocation.

### 2. Confirmed Gaps
- **Rebalancing Engine Service**: No service currently exists to convert allocation drift into concrete, lot-sized `Trade` recommendations.
- **Cash Outlay & Proceeds Tracking**: No mechanism enforces that buy trades (including transaction fees) do not exceed available cash + net sell proceeds.
- **Lot Sizing & Residual Allocation**: No production logic rounds trade quantities to instrument `lot_size` while preventing overshoots.
- **Post-Trade Portfolio Simulator**: No component recalculates post-trade holdings, post-trade portfolio valuation (`pre_val - total_fees`), and post-trade drift.
- **Constraint Gatekeeper**: No service evaluates proposed trades against `EXCLUDED_INSTRUMENT`, `MIN_TRADE_VALUE`, or post-trade `MAX_POSITION_WEIGHT` to block trades or reject proposals.

### 3. Ambiguities & Edge Cases
- **Instrument Selection for Underweight Classes**: When an asset class is underweight and multiple instruments exist (or none are currently held), an explicit deterministic selection rule is needed (e.g. primary active instrument ordered by `instrument_id`).
- **Sell Allocation across Holdings**: When an asset class is overweight and holds multiple instruments, sell order needs a deterministic rule (e.g. proportional or largest position first to simultaneously reduce concentration).
- **Cash Reserve Target vs. Liquidity Limit**: Portfolios may have both a `TargetAllocation` for `CASH` and a `LIQUIDITY_LIMIT` constraint.

### 4. Implementation Plan
- **Batch 4.1: Deterministic Trade Generation** (Est. 45 min)
  - Files: `app/schemas/rebalancing.py`, `app/services/rebalancing_service.py`, `tests/test_rebalancing_service.py`
  - Scope: Convert drift to lot-sized sell/buy trades, calculate fees, enforce cash solvency, deterministic instrument selection.
- **Batch 4.2: Constraint Validation, Post-Trade Simulation & API** (Est. 45 min)
  - Files: `app/services/rebalancing_service.py`, `app/api/v1/rebalancing.py`, `app/main.py`, `tests/test_rebalancing_simulation_api.py`
  - Scope: Post-trade simulation, constraint gatekeeper (`HARD` $\rightarrow$ `BLOCKED`/`REJECTED`), proposal creation endpoint.

