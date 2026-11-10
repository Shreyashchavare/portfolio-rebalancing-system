# Phase 1.2 — TDD: SQLAlchemy Base and InvestorProfile Tests

We are continuing the portfolio-rebalancing-system project.

## Objective
Establish the SQLAlchemy declarative base and implement the first database entity: `InvestorProfile`.

## Step 1 — Tests only

Create `tests/test_investor_profile.py`.

Write tests covering:

1. `Base` exists and is a SQLAlchemy `DeclarativeBase`.
2. `InvestorProfile` inherits from `Base`.
3. Table name is `investor_profile`.
4. `investor_id` is the primary key and uses the agreed string identifier.
5. Required fields and their SQLAlchemy column types.
6. `risk_category` accepts only `LOW`, `MODERATE`, and `HIGH` at the application/database constraint level.
7. `created_at` has a timestamp default.
8. The model can be registered in SQLAlchemy metadata.
9. A valid InvestorProfile can be inserted and retrieved using an explicitly supplied SQLite in-memory test engine.

Use the agreed schema:

- `investor_id`: VARCHAR(20), primary key
- `name`: required string
- `risk_category`: LOW / MODERATE / HIGH
- `created_at`: timestamp with a default

Do not add extra business fields.

## Constraints

- Do not implement the model yet.
- Do not modify existing database configuration/session code.
- Do not create other entities.
- Do not add migrations yet.
- Do not weaken existing tests.
- Use SQLite explicitly for isolated database tests.
- Keep tests independent and deterministic.

## Step 2 — Verify RED

Run:

`pytest -v`

Expected: the new InvestorProfile tests fail because the model and Base have not yet been implemented. Existing 13 tests must continue passing.

Report:
1. New test file created.
2. Test cases added.
3. Exact failure summary.
4. Existing test results.

Stop after the RED phase. Do not implement the model until reviewed.