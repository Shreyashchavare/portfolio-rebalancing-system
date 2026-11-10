# Prompt P1-14 — Trade and RebalanceProposal (TDD)

**AI Tool:** Antigravity  
**Phase:** 1 — Database Foundation  
**Task:** Implement Trade and RebalanceProposal entities using TDD

## Prompt

# Phase 1 — Batch 6: Trade and RebalanceProposal (TDD)

Existing models: InvestorProfile, Portfolio, Instrument, Holding, MarketPrice, TargetAllocation, FeeSchedule, Constraint, ConstraintInstrument.
Existing test suite: 109 passing tests.

## Objective

Implement Trade and RebalanceProposal as the final two core entities in the database foundation.

## 1. RebalanceProposal entity

Create `app/models/rebalance_proposal.py`.

Required fields:

- `proposal_id`: String(30), primary key. Follow RB-2026-000001 naming convention.
- `portfolio_id`: String(40), required FK to `portfolio.portfolio_id`.
- `status`: String(20), required. Allowed: DRAFT, PENDING_REVIEW, APPROVED, REJECTED.
- `review_decision`: String(20), required. Allowed: PENDING, APPROVED, REJECTED.
- `pre_trade_portfolio_value`: Numeric(18, 4), nullable.
- `post_trade_portfolio_value`: Numeric(18, 4), nullable.
- `created_at`: timezone-aware DateTime, required, UTC default.
- `reviewed_at`: timezone-aware DateTime, nullable.
- `review_reason`: Text, nullable.

Add database CHECK constraints for valid status and review_decision values. Add validation to prevent negative portfolio values.

## 2. Trade entity

Create `app/models/trade.py`.

Required fields:

- `trade_id`: String(40), primary key.
- `proposal_id`: String(30), required FK to `rebalance_proposal.proposal_id`.
- `instrument_id`: String(20), required FK to `instrument.instrument_id`.
- `fee_schedule_id`: String(20), nullable FK to `fee_schedule.fee_schedule_id`. Nullable so missing-fee anomaly cases can be represented and flagged.
- `trade_side`: String(4), required. Allowed BUY, SELL.
- `quantity`: Numeric(18, 4), required, strictly positive.
- `unit_price`: Numeric(18, 4), required, strictly positive.
- `trade_value`: Numeric(18, 4), required, strictly positive.
- `fee_amount`: Numeric(18, 4), required, nonnegative.
- `status`: String(20), required. Allowed PROPOSED, BLOCKED, APPROVED, REJECTED.
- `created_at`: timezone-aware DateTime, required, UTC default.

Add database CHECK constraints for allowed enum values and valid numeric ranges.

Use Decimal for all financial and quantity fields.

## 3. Relationships

- Portfolio has a one-to-many relationship with RebalanceProposal.
- RebalanceProposal has a one-to-many relationship with Trade.
- Instrument has a one-to-many relationship with Trade.
- FeeSchedule has a one-to-many relationship with Trade, with nullable fee_schedule_id.
- Avoid cascade deletion of financial history.
- Add reverse relationships only where useful and consistent with existing models.

## 4. Lifecycle and audit history

Do not overwrite or silently discard historical records.

For this batch:
- Preserve created_at and reviewed_at timestamps.
- Keep status and review_decision separately.
- Do not introduce an unrelated event-history table unless required by the existing challenge schema.
- Document that full state-transition history will be handled in the later workflow/audit implementation.

## 5. TDD execution

1. Create `tests/test_rebalance_proposal.py` and `tests/test_trade.py` before implementing either model.
2. Cover model inheritance, table names, primary keys, foreign keys, required/nullable fields, numeric precision, Decimal handling, CHECK constraints, relationships, timestamps, and SQLite CRUD.
3. Test invalid status, invalid review decision, invalid trade side, negative values, zero trade quantity/price/value, and invalid foreign keys.
4. Test that a Trade may have a NULL fee_schedule_id.
5. Run both new test files first and verify RED.
6. Implement both models and export them from `app/models/__init__.py`.
7. Run focused tests and verify GREEN.
8. Run the complete test suite and verify GREEN.

## 6. Restrictions

- Do not modify existing entity columns or constraints.
- Do not implement services, API endpoints, migrations, or UI.
- Do not add dependencies.
- Do not use float for financial values.
- Do not cascade-delete financial records.
- Do not weaken existing tests.
- Keep implementation minimal and aligned with the challenge.

## 7. Prompt record

Save this exact prompt as:
`prompts/phase-1/14-trade-rebalance-proposal-implementation.md`

Append a brief RED/GREEN execution record and document schema assumptions.

## Final report

Report changed files, schema decisions, RED/GREEN results for both entities, total test count, warnings, and Git status.

Stop after this batch.

---

## Schema Assumptions & Decisions

1. **State and Decision Separation**: In `RebalanceProposal`, `status` (`DRAFT`, `PENDING_REVIEW`, `APPROVED`, `REJECTED`) tracks the overall proposal lifecycle, while `review_decision` (`PENDING`, `APPROVED`, `REJECTED`) records the human decision state. Full immutable state-transition logs will be managed in subsequent audit/workflow modules.
2. **Missing-Fee Anomaly Representation**: `fee_schedule_id` on `Trade` is deliberately nullable to allow trades with unmapped fee tiers or anomalies to be represented, persisted, and marked as `BLOCKED`.
3. **Strictly Positive vs Nonnegative Amounts**:
   - `quantity > 0`, `unit_price > 0`, and `trade_value > 0` are enforced at the database level for `Trade`.
   - `fee_amount >= 0` allows fee-free/promotional trading without allowing negative fees.
   - `pre_trade_portfolio_value >= 0` and `post_trade_portfolio_value >= 0` on `RebalanceProposal` reject negative portfolio valuations while remaining nullable prior to valuation calculation.
4. **No Cascading Deletion**: Foreign key references across `Portfolio` -> `RebalanceProposal` -> `Trade`, `Instrument` -> `Trade`, and `FeeSchedule` -> `Trade` omit cascade deletions (`cascade="all, delete-orphan"`), preserving financial records and immutable audit logs.
5. **Exact Numeric Arithmetic**: All prices, values, fees, and quantities utilize SQLAlchemy `Numeric(18, 4)` and Python `Decimal`.

---

## Actual Results

### RED Phase
- Executed: `pytest tests/test_rebalance_proposal.py tests/test_trade.py -v`
- Result: 26 failed out of 26 tests (12 in `test_rebalance_proposal.py`, 14 in `test_trade.py`) due to missing models and exports.
- All 109 pre-existing tests continued to pass.

### GREEN Phase
- Created [`app/models/rebalance_proposal.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/models/rebalance_proposal.py) with `RebalanceProposal`, `ProposalStatus`, and `ReviewDecision`.
- Created [`app/models/trade.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/models/trade.py) with `Trade` and `TradeStatus`.
- Updated navigation relationships on [`app/models/portfolio.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/models/portfolio.py) (`proposals`), [`app/models/instrument.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/models/instrument.py) (`trades`), and [`app/models/fee_schedule.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/models/fee_schedule.py) (`trades`).
- Exported all new entities and enums in [`app/models/__init__.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/models/__init__.py).
- Executed: `pytest -v`
- Result: 135 passed, 0 failed across all 12 test suites (109 existing + 26 new).

