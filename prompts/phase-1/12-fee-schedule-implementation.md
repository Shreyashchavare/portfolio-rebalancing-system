# Prompt P1-12 — Implement FeeSchedule Using TDD

**AI Tool:** Antigravity  
**Phase:** 1 — Database Foundation  
**Task:** Implement FeeSchedule entity using TDD

## Prompt

# Phase 1.8 — Implement FeeSchedule Using TDD

Existing models: InvestorProfile, Portfolio, Instrument, Holding, MarketPrice, TargetAllocation.
Existing test suite: 80 passing tests.

## Purpose

Represent fee schedules with multiple tiers to support deterministic trade-fee calculations in the rebalancing system.

The challenge requires fee tiers and fee calculations but does not prescribe exact database columns or a fee formula. Use the following minimal schema assumptions and document them.

## Required schema

Implement `FeeSchedule` with:

- `fee_schedule_id`: String(20), primary key.
- `asset_class`: String(50), required.
- `trade_side`: String(4), required; allowed values BUY and SELL.
- `min_trade_value`: Numeric(18, 4), required; minimum trade notional for this tier, inclusive.
- `max_trade_value`: Numeric(18, 4), nullable; maximum trade notional for this tier, inclusive. NULL means no upper limit.
- `fee_rate_bps`: Numeric(10, 4), required; fee rate in basis points.
- `fixed_fee`: Numeric(18, 4), required; fixed fee in the schedule currency.
- `minimum_fee`: Numeric(18, 4), required.
- `maximum_fee`: Numeric(18, 4), nullable.
- `currency`: String(3), required.
- `effective_from`: Date, required.
- `effective_to`: Date, nullable.
- `is_active`: Boolean, required, default true.

## Database constraints

1. Trade value range must be valid: `min_trade_value >= 0` and `max_trade_value IS NULL OR max_trade_value >= min_trade_value`.
2. Fee rate, fixed fee, and minimum fee must be nonnegative.
3. Maximum fee must be NULL or greater than or equal to minimum fee.
4. Effective date range must be valid: `effective_to IS NULL OR effective_to >= effective_from`.
5. Trade side must be BUY or SELL.
6. Use a suitable uniqueness constraint to prevent duplicate tiers for the same asset class, trade side, minimum trade value, and effective start date.

## TDD execution

1. Create `tests/test_fee_schedule.py` first.
2. Cover model inheritance, table name, primary key, required fields, column types, Decimal handling, all CHECK constraints, allowed trade sides, effective dates, uniqueness, metadata registration, and SQLite insertion/retrieval.
3. Run new tests first and verify RED.
4. Implement `app/models/fee_schedule.py` using SQLAlchemy 2.x typed mappings.
5. Export `FeeSchedule` from `app/models/__init__.py`.
6. Run the complete test suite and verify GREEN.

## Restrictions

- Do not modify existing entity schemas.
- Do not implement Trade, Constraint, or RebalanceProposal yet.
- Do not create a separate fee-tier entity.
- Do not implement fee calculation services yet.
- Do not add dependencies or migrations.
- Use Decimal, never float for financial fields.
- Keep implementation minimal and consistent with existing models.
- Document the schema assumptions in the prompt record.

## Prompt record

Save this exact prompt in:
`prompts/phase-1/12-fee-schedule-implementation.md`

Append a brief RED/GREEN execution record.

## Final report

Report changed files, schema decisions, RED result, GREEN result, total test count, warnings, and Git status.

Stop after completing FeeSchedule.

---

## Schema Assumptions & Decisions

1. **Tier Representation within Single Entity**: Rather than introducing a normalized parent-child fee structure (`FeeSchedule` -> `FeeTier`), fee tiers are modeled directly on `FeeSchedule` rows keyed by `(asset_class, trade_side, min_trade_value, effective_from)`. This fulfills the requirement without unnecessary relational complexity.
2. **Open-Ended Tiers**: An unbounded tier (no cap on notional value) is modeled with `max_trade_value = NULL`.
3. **Fee Components**: Supports both proportional bps fees (`fee_rate_bps`) and flat ticket charges (`fixed_fee`), bounded by `minimum_fee` and optional `maximum_fee` caps.
4. **Trade Side Validation**: Enforced at the database CHECK constraint level (`trade_side IN ('BUY', 'SELL')`) and represented as a typed Python `TradeSide(str, Enum)`.
5. **Precision & Scale**: All monetary amounts use `Numeric(18, 4)` and rates use `Numeric(10, 4)` with Python `Decimal` to ensure exact non-floating arithmetic.

---

## Actual Results

### RED Phase
- Executed: `pytest tests/test_fee_schedule.py -v`
- Result: 13 failed out of 13 tests with `ModuleNotFoundError: No module named 'app.models.fee_schedule'` and `ImportError: cannot import name 'FeeSchedule' from 'app.models'`.
- All 80 pre-existing tests continued to pass (`pytest -k "not test_fee_schedule" -v`).

### GREEN Phase
- Created `app/models/fee_schedule.py` with `FeeSchedule` entity and `TradeSide` enum using SQLAlchemy 2.x typed mappings (`Mapped`, `mapped_column`).
- Enforced all 5 CHECK constraints and the composite unique constraint `(asset_class, trade_side, min_trade_value, effective_from)`.
- Exported `FeeSchedule` and `TradeSide` in `app/models/__init__.py`.
- Executed: `pytest -v`
- Result: 93 passed, 0 failed across all 9 test suites (80 existing + 13 new).

