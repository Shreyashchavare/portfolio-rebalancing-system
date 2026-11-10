# Prompt P1-09 — Implement Holding Entity (TDD)

**AI Tool:** Antigravity  
**Phase:** 1 — Database Foundation  
**Task:** Implement the Holding entity using TDD

## Prompt

Implement the Holding entity in my existing `portfolio-rebalancing-system` project using Test-Driven Development.

## Existing project state
- Python 3.12
- SQLAlchemy 2.x
- Shared declarative `Base`
- Implemented models: InvestorProfile, Portfolio, Instrument
- Existing test suite: 44 tests passing
- SQLite in-memory for isolated tests

## 1. Required schema

| Column | Definition |
|---|---|
| holding_id | String(100), primary key |
| portfolio_id | String(40), required FK to portfolio.portfolio_id |
| instrument_id | String(20), required FK to instrument.instrument_id |
| quantity | Numeric/Decimal, required and non-negative |
| as_of_date | Date, required |

ID convention:

`HOLD-<portfolio-id>-<instrument-id>`

A portfolio/instrument/date combination must be unique. The same portfolio and instrument must be allowed to have multiple historical snapshots on different dates.

## 2. TDD execution

First create `tests/test_holding.py`.

Cover:
1. Inheritance from shared Base.
2. Table name.
3. Primary key and column types.
4. Portfolio foreign key.
5. Instrument foreign key.
6. Required fields.
7. Non-negative quantity using a database CHECK constraint.
8. Unique constraint on `(portfolio_id, instrument_id, as_of_date)`.
9. Metadata registration.
10. Valid insert and retrieval using SQLite.
11. Invalid foreign-key references are rejected.
12. Historical snapshots on different dates are allowed.
13. Duplicate snapshots for the same portfolio, instrument and date are rejected.

Run the new tests first and verify RED because Holding is not implemented.

Then implement:
- `app/models/holding.py`
- Update `app/models/__init__.py`

Use SQLAlchemy 2.x typed mappings (`Mapped`, `mapped_column`), `Decimal`, and appropriate database constraints.

Enable SQLite foreign-key enforcement in tests using `PRAGMA foreign_keys=ON`.

## 3. Restrictions

- Do not modify existing entity schemas.
- Do not implement MarketPrice or other entities.
- Do not create Alembic migrations.
- Do not add dependencies.
- Do not weaken existing tests.
- Do not modify database configuration/session management.
- Keep implementation minimal and consistent with existing models.

## 4. Verification

Run:

`pytest -v`

Expected:
- All 44 existing tests pass.
- All new Holding tests pass.
- Report exact total test count and RED/GREEN results.

## Actual Results

### RED Phase
- Executed: `pytest tests/test_holding.py -v`
- Result: 13 failed out of 13 tests with `ImportError: cannot import name 'Holding' from 'app.models'`.
- All 44 pre-existing tests continued to pass.

### GREEN Phase
- Created `app/models/holding.py` with `Holding` entity using SQLAlchemy 2.x `Mapped`, `mapped_column`, `Numeric(18, 4)` for `quantity`, `CheckConstraint('quantity >= 0')`, and `UniqueConstraint('portfolio_id', 'instrument_id', 'as_of_date')`.
- Exported `Holding` in `app/models/__init__.py`.
- Executed: `pytest -v`
- Result: 57 passed, 0 failed across all 6 test suites.

