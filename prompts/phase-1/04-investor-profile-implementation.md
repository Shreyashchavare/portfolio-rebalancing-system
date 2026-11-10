# Phase 1.2 — GREEN: Implement Base and InvestorProfile

The RED phase is complete. Nine tests in `tests/test_investor_profile.py` fail because the model and declarative Base are not implemented. Thirteen existing tests pass.

Implement only the functionality required to make these tests pass.

## Required files

1. `app/models/base.py`
2. `app/models/investor_profile.py`
3. `app/models/__init__.py`

## Requirements

### Base
- Use SQLAlchemy 2.x `DeclarativeBase`.
- Define one shared declarative Base.
- Ensure model metadata is registered correctly.

### InvestorProfile

Implement the agreed schema:

| Column | Definition |
|---|---|
| investor_id | String(20), primary key |
| name | Required string |
| risk_category | Required, restricted to LOW, MODERATE, HIGH |
| created_at | Timestamp with appropriate default |

Requirements:
- Use SQLAlchemy 2.x typed mappings (`Mapped`, `mapped_column`) where appropriate.
- Add a database-level CHECK constraint for `risk_category`.
- Use a UTC-aware timestamp default.
- Do not add unrelated fields or relationships.
- Export `Base` and `InvestorProfile` from `app.models`.

## Constraints
- Do not modify database configuration or session management.
- Do not modify or weaken existing tests.
- Do not implement other entities.
- Do not create Alembic migrations yet.
- Do not add dependencies.
- Keep the implementation minimal.

## Verification

Run:

`pytest -v`

Expected:
- All 9 InvestorProfile tests pass.
- All 13 existing tests continue passing.
- Total: 22 passing tests.

Report changed files, implementation decisions, test results, and any warnings. Stop after this task.