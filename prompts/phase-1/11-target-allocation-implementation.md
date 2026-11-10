# Prompt P1-11 — Implement TargetAllocation Using TDD

**AI Tool:** Antigravity  
**Phase:** 1 — Database Foundation  
**Task:** Implement TargetAllocation entity using TDD

## Prompt

# Phase 1.7 — Implement TargetAllocation Using TDD

Existing models: InvestorProfile, Portfolio, Instrument, Holding, MarketPrice.
Existing test suite: 68 passing tests.

## Required schema

Implement `TargetAllocation` with:

- `id`: BIGINT identity primary key; use a SQLite-compatible Integer variant for autoincrement tests, consistent with MarketPrice.
- `portfolio_id`: String(40), required FK to `portfolio.portfolio_id`.
- `asset_class`: required String(50).
- `target_weight`: Numeric(7, 4), Python Decimal, required; represents a percentage from 0 to 100 inclusive.
- `effective_from`: Date, required.
- `effective_to`: Date, nullable; when supplied, must be greater than or equal to `effective_from`.

## Database constraints

1. CHECK `target_weight >= 0 AND target_weight <= 100`.
2. CHECK `effective_to IS NULL OR effective_to >= effective_from`.
3. UNIQUE `(portfolio_id, asset_class, effective_from)` to prevent duplicate allocation records for the same portfolio, asset class, and effective start date.

## TDD execution

1. Create `tests/test_target_allocation.py` first.
2. Test inheritance, table name, primary key, foreign key, column types, weight range CHECK constraint, effective date CHECK constraint, composite uniqueness, metadata registration, SQLite insertion/retrieval, invalid foreign key, and duplicate allocation rejection.
3. Run new tests first and verify RED.
4. Implement `app/models/target_allocation.py` using SQLAlchemy 2.x typed mappings.
5. Export `TargetAllocation` from `app/models/__init__.py`.
6. Run the full pytest suite and verify GREEN.

## Restrictions

- Do not modify existing entity schemas.
- Do not implement any other entity (CashBalance, RebalancingRun, etc.).
- Do not create migrations.
- Do not add dependencies.
- Use Decimal for weights; do not use float.
- Enforce SQLite foreign keys in SQLite tests.
- Do not weaken existing tests.
- Keep the implementation minimal and consistent with previous models.

Save the exact prompt and brief execution results to `prompts/phase-1/11-target-allocation-implementation.md`.
Report changed files, RED/GREEN outcomes, total test count, warnings, and git status. Stop there; do not implement another entity.

## Actual Results

### RED Phase
- Executed: `pytest tests/test_target_allocation.py -v`
- Result: 12 failed out of 12 tests with `ModuleNotFoundError: No module named 'app.models.target_allocation'` and `ImportError: cannot import name 'TargetAllocation' from 'app.models'`.
- All 68 pre-existing tests continued to pass (`pytest -k "not test_target_allocation" -v`).

### GREEN Phase
- Created `app/models/target_allocation.py` with `TargetAllocation` entity using SQLAlchemy 2.x typed mappings (`Mapped`, `mapped_column`), `BigInteger().with_variant(Integer, "sqlite")`, `Identity()`, `Numeric(7, 4)` target weight, `CheckConstraint("target_weight >= 0 AND target_weight <= 100")`, `CheckConstraint("effective_to IS NULL OR effective_to >= effective_from")`, and `UniqueConstraint("portfolio_id", "asset_class", "effective_from")`.
- Exported `TargetAllocation` in `app/models/__init__.py`.
- Executed: `pytest -v`
- Result: 80 passed, 0 failed across all 8 test suites (68 existing + 12 new).

