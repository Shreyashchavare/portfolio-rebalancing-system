# Phase 1 — Database Foundation: Financial and Rebalancing Models

## Objective
Complete the domain schema required for policy-constrained recommendations and proposal persistence.

## Consolidated entities
- **TargetAllocation:** portfolio, asset class, target percentage and effective date range. Enforce 0–100 percentage bounds, valid dates and uniqueness by portfolio/asset class/effective start.
- **FeeSchedule:** asset class, BUY/SELL side, notional tier, basis-point rate, fixed/minimum/optional maximum fee, currency and effective dates. Multiple rows represent fee tiers.
- **Constraint:** supported constraint type, scope (`PORTFOLIO`, `ASSET_CLASS`, `INSTRUMENT`), scope reference, severity (`HARD`, `SOFT`), optional Decimal threshold, effective dates and active state.
- **ConstraintInstrument:** many-to-many bridge between constraints and instruments, with a composite primary key.
- **RebalanceProposal:** proposal lifecycle status, separate review decision, pre/post-trade values, timestamps and review reason.
- **Trade:** proposal/instrument/optional fee-schedule references, BUY/SELL side, positive quantity/price/notional, nonnegative fee, status and timestamp.

## Important schema decisions
- Use Decimal/Numeric columns for money, rates, weights and quantities.
- A `Constraint.scope_reference_id` is polymorphic; do not create a misleading single FK. Validate it according to `scope_type`.
- A nullable `Trade.fee_schedule_id` permits missing-fee cases to be represented and explicitly blocked.
- Keep proposal lifecycle status separate from the human review decision.
- Do not cascade-delete financial history.
- Keep historical state-transition events for the later workflow/audit phase rather than inventing unrelated tables here.

## Verification approach
Test required/nullable fields, enum/check constraints, foreign keys, uniqueness, relationships, effective dates, Decimal behavior and SQLite CRUD. Run the full test suite after each entity batch.

## Scope boundary
This phase establishes persistence models only. Financial calculations, APIs, migrations and UI belong to later phases.
