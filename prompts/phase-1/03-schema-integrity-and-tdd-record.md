# Phase 1 — Schema Integrity and TDD Record

## Shared implementation conventions
- Python 3.12, SQLAlchemy 2.x typed mappings (`Mapped`, `mapped_column`) and a shared declarative base.
- PostgreSQL is the intended relational database; SQLite in-memory is used for isolated tests.
- Add database-level CHECK, UNIQUE and FOREIGN KEY constraints where appropriate.
- Use explicit relationships and `back_populates` where they represent real domain relationships.
- Avoid adding fields, entities, migrations or dependencies outside the current batch.

## Core relationship map
- InvestorProfile 1 → many Portfolios.
- Portfolio 1 → many Holdings, TargetAllocations and RebalanceProposals.
- Instrument 1 → many Holdings, MarketPrices and Trades.
- Constraint many ↔ many Instrument through ConstraintInstrument.
- RebalanceProposal 1 → many Trades.
- FeeSchedule 1 → many Trades; a Trade may have no fee schedule so the missing-fee exception can be handled explicitly.

## ID conventions recorded in the project brief
- Investor: `INV-000001`
- Portfolio: `PORT-<investor-id>-01`
- Instrument: `INS-000001`
- Holding: `HOLD-<portfolio-id>-<instrument-id>`
- Rebalance proposal: `RB-2026-000001`

IDs should be stable and treated as identifiers, not regenerated during updates.

## TDD acceptance pattern
1. Inspect existing code and tests.
2. Add tests before implementation.
3. Confirm the expected RED result.
4. Implement the smallest scoped change.
5. Confirm focused tests and the full suite pass.
6. Record changed files, decisions, exact test results and warnings.

## Limitations of this condensed record
This file consolidates the repeated per-entity test prompts. It intentionally omits repeated terminal transcripts and historical intermediate test counts; consult the original archive if exact per-commit output is required.
