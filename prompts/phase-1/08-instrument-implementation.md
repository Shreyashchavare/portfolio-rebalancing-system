# Prompt P1-08 — Implement Instrument Entity (TDD)

**AI Tool:** Antigravity  
**Phase:** 1 — Database Foundation  
**Task:** Implement the Instrument entity using TDD

## Prompt

Implement the Instrument entity in my existing portfolio-rebalancing-system project using TDD.

Existing state:
- SQLAlchemy 2.x shared Base.
- InvestorProfile and Portfolio models implemented.
- 33 existing tests passing.
- Python 3.12, SQLAlchemy 2.x, SQLite for isolated tests.

## Required schema

- instrument_id: String(20), primary key
- symbol: required, unique String
- instrument_name: required String
- asset_class: required String
- lot_size: required Numeric/Decimal, strictly greater than zero
- is_active: required Boolean, default True

## Execution

1. First create `tests/test_instrument.py`.
2. Cover model inheritance, table name, columns/types, primary key, unique symbol, positive lot size, database CHECK constraint, Boolean default, metadata registration, SQLite insert/retrieve and duplicate-symbol rejection.
3. Run only the new tests and verify they fail because the model is missing (RED).
4. Implement `app/models/instrument.py` using the existing Base and SQLAlchemy 2.x typed mappings.
5. Add a database CHECK constraint for `lot_size > 0`, unique symbol constraint and appropriate defaults.
6. Export Instrument from `app/models/__init__.py`.
7. Run the complete pytest suite and verify all tests pass (GREEN).

## Restrictions

- Do not modify InvestorProfile, Portfolio, database configuration or session management.
- Do not implement other entities.
- Do not create migrations.
- Do not add dependencies.
- Do not weaken existing tests.
- Follow existing project conventions and keep code minimal.

## Actual Results

### RED Phase
- Executed: `pytest tests/test_instrument.py -v`
- Result: 11 failed, 0 passed. All 11 tests failed with `ImportError: cannot import name 'Instrument' from 'app.models'`.
- All 33 existing tests continued passing.

### GREEN Phase
- Created `app/models/instrument.py` with `Instrument` model, `CheckConstraint('lot_size > 0')`, unique `symbol`, `Numeric(18, 4)` lot size, and boolean `is_active` default.
- Exported `Instrument` in `app/models/__init__.py`.
- Executed: `pytest -v`
- Result: 44 passed, 0 failed.
