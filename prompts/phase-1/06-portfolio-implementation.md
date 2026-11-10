# Phase 1.3 — GREEN: Implement Portfolio Entity

The RED phase is complete:
- 11 Portfolio tests fail because the model is missing.
- 22 existing tests pass.

Implement only the Portfolio model.

## Files

Create:
- `app/models/portfolio.py`

Modify:
- `app/models/__init__.py`

## Schema

- `portfolio_id`: String(40), primary key
- `investor_id`: String(20), required foreign key to `investor_profile.investor_id`
- `portfolio_name`: required String
- `base_currency`: required String
- `status`: ACTIVE or INACTIVE, with a database CHECK constraint
- `created_at`: timezone-aware timestamp with UTC Python default

## Relationships

Implement:
- `Portfolio.investor`
- `InvestorProfile.portfolios`

Use SQLAlchemy `relationship()` and `back_populates`.

Modify `investor_profile.py` only to add the inverse relationship. Do not change its existing columns or constraints.

## Constraints

- Follow the existing SQLAlchemy 2.x typed mapping style.
- Reuse the existing Base.
- Export Portfolio from `app.models`.
- Do not implement any other entity.
- Do not change database configuration/session management.
- Do not modify or weaken tests.
- Do not create Alembic migrations.
- Keep the implementation minimal.

## Verification

Run:

`pytest -v`

Expected: all 33 tests pass.

Report changed files, implementation decisions, and test results. Stop after implementation.