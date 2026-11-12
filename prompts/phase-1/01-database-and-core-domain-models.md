# Phase 1 — Database Foundation: Configuration and Core Models

## Objective
Create the relational foundation using FastAPI, SQLAlchemy 2.x and PostgreSQL, with SQLite in-memory databases for isolated model tests.

## Consolidated scope
1. Database configuration and session lifecycle:
   - Read `DATABASE_URL` from environment settings.
   - Create SQLAlchemy engines and session factories explicitly.
   - Provide a FastAPI `get_db` dependency that always closes sessions.
   - Avoid connecting to PostgreSQL merely by importing the application.
2. Shared ORM foundation:
   - One SQLAlchemy 2.x declarative `Base`.
   - Consistent typed mappings and model exports.
3. Core entities:
   - `InvestorProfile`: investor identity, name, risk category (`LOW`, `MODERATE`, `HIGH`) and creation timestamp.
   - `Portfolio`: investor FK, name, base currency, `ACTIVE`/`INACTIVE` status and creation timestamp.
   - `Instrument`: symbol, name, asset class, positive Decimal lot size and active flag.
   - `Holding`: portfolio/instrument FKs, nonnegative Decimal quantity and dated snapshots.
   - `MarketPrice`: instrument FK, positive Decimal price, date and source.

## Data integrity
- Add primary keys, foreign keys, uniqueness and CHECK constraints.
- Enable SQLite foreign-key enforcement in tests.
- Permit historical holding snapshots on different dates; prevent duplicate portfolio/instrument/date snapshots.
- Prevent duplicate instrument prices for the same instrument/date.
- Use `Decimal` for financial and quantity values; do not use binary floating point.

## TDD workflow
For each entity, write focused tests first, verify the missing implementation fails (RED), implement only that entity, then run focused and full suites (GREEN). Preserve existing tests and avoid unrelated migrations, services or APIs in this phase.

## Source-history note
The source archive records progressive model implementation and test growth. One source file (`07-instrument-tests.md`) is empty; no additional requirement is inferred from it.
