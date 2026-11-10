# Prompt P1-10 — Implement MarketPrice Using TDD

**AI Tool:** Antigravity  
**Phase:** 1 — Database Foundation  
**Task:** Implement MarketPrice entity using TDD

## Prompt

Implement the MarketPrice entity in the existing portfolio-rebalancing-system project.

Existing models: InvestorProfile, Portfolio, Instrument, Holding.
Existing test suite: 57 passing tests.

## Required schema

- id: BIGINT identity primary key
- instrument_id: String(20), required FK to instrument.instrument_id
- price: Numeric/Decimal, required and strictly positive
- price_date: Date, required
- source: required String

A unique constraint must prevent duplicate prices for the same instrument and price date.

## TDD execution

1. Create `tests/test_market_price.py` first.
2. Test inheritance, table name, primary key, foreign key, column types, positive price CHECK constraint, unique `(instrument_id, price_date)`, metadata registration, SQLite insertion/retrieval, invalid foreign key and duplicate price rejection.
3. Run the new tests first and verify RED.
4. Implement `app/models/market_price.py` using SQLAlchemy 2.x typed mappings.
5. Export MarketPrice from `app/models/__init__.py`.
6. Run the full pytest suite and verify GREEN.

## Restrictions

- Do not modify existing entity schemas.
- Do not implement TargetAllocation or other entities.
- Do not create migrations.
- Do not add dependencies.
- Use Decimal and SQLite foreign-key enforcement.
- Do not weaken existing tests.
- Keep the implementation minimal.

## Actual Results

### RED Phase
- Executed: `pytest tests/test_market_price.py -v`
- Result: 11 failed out of 11 tests with `ImportError: cannot import name 'MarketPrice' from 'app.models'`.
- All 57 pre-existing tests continued to pass.

### GREEN Phase
- Created `app/models/market_price.py` with `MarketPrice` entity using SQLAlchemy 2.x `Mapped`, `mapped_column`, `BigInteger` identity primary key (with `Integer` variant for SQLite autoincrement), `Numeric(18, 4)` price, `CheckConstraint('price > 0')`, and `UniqueConstraint('instrument_id', 'price_date')`.
- Exported `MarketPrice` in `app/models/__init__.py`.
- Executed: `pytest -v`
- Result: 68 passed, 0 failed across all 7 test suites.

