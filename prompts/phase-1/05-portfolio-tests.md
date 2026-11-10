# Phase 1.3 — TDD: Portfolio Entity Tests (RED)

We are continuing the portfolio-rebalancing-system project.

The following are already implemented:
- SQLAlchemy 2.x declarative Base.
- InvestorProfile model.
- Database configuration and session management.
- Existing test suite: 22 tests passing.

## Objective

Create tests for the `Portfolio` entity only. Do not implement the model yet.

## Step 1 — Create tests/test_portfolio.py

Use the agreed schema:

| Column | Definition |
|---|---|
| portfolio_id | VARCHAR(40), primary key |
| investor_id | VARCHAR(20), foreign key to investor_profile.investor_id |
| portfolio_name | Required string |
| base_currency | Required string |
| status | ACTIVE / INACTIVE |
| created_at | Timestamp with default |

## Required tests

1. Portfolio model inherits from the shared `Base`.
2. Table name is `portfolio`.
3. `portfolio_id` is a VARCHAR(40) primary key.
4. `investor_id` is a required VARCHAR(20) foreign key referencing `investor_profile.investor_id`.
5. `portfolio_name` and `base_currency` are required fields.
6. `status` accepts only ACTIVE and INACTIVE, with a database-level CHECK constraint.
7. `created_at` has an appropriate timestamp default.
8. Model is registered in shared metadata.
9. A valid portfolio can be inserted and retrieved using SQLite in-memory.
10. A portfolio cannot reference a nonexistent investor.
11. Relationship to InvestorProfile works correctly.

## Testing requirements

- Use SQLite explicitly.
- Enable SQLite foreign-key enforcement using a connection event (`PRAGMA foreign_keys=ON`).
- Create tables using `Base.metadata.create_all()`.
- Insert the parent InvestorProfile before inserting Portfolio.
- Test invalid foreign-key references.
- Do not weaken existing tests.
- Keep tests independent and deterministic.

## Constraints

- Do not implement Portfolio yet.
- Do not modify existing models or database configuration.
- Do not implement Instrument, Holding, or any other entity.
- Do not create Alembic migrations yet.
- Do not add dependencies.

## Step 2 — Verify RED

Run:

`pytest -v`

Expected:
- New Portfolio tests fail because the Portfolio model does not exist.
- All 22 existing tests remain passing.

Report the test count and exact failure summary. Stop after RED.