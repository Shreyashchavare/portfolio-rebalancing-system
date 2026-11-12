# Phase 2 — Synthetic Data Foundation and Generators

## Objective
Build a deterministic synthetic dataset that exercises the portfolio-rebalancing workflow with valid relationships, reproducible identifiers and documented validation rules.

## Consolidated scope
- Define a data dictionary for all domain entities: field types, required/optional status, allowed values, units, uniqueness and validation rules.
- Provide deterministic ID utilities and shared validation helpers.
- Generate master/reference records before dependent records.
- Implement generators for investor profiles, portfolios, instruments, market prices, target allocations, holdings, fee schedules, constraints, proposals and trades.
- Generate bridge records for constraint/instrument associations.
- Derive valuations, weights, drift, trades and other dependent values from source records rather than assigning unrelated random outcomes.

## Generation rules
- Use fixed seed `20261022`.
- Use the same generator logic for starter and full-scale configurations.
- Generate a valid baseline first; inject labelled anomalies only after the baseline is valid.
- Preserve referential integrity and valid parent IDs.
- Keep ground-truth labels separate from operational input features.
- Use documented synthetic data unless lawful external-data provenance is recorded.

## Baseline and full-scale targets in the source brief
- Starter dataset: 10 portfolios, 20 instruments, 600 market prices, 40 target allocations.
- Full dataset: 1,000 portfolios, 5,000 instruments/holdings, 250 trading days of prices, plus proposals, trades, constraints and fee schedules.

## Deliverables
Generator modules, schema/data dictionary, deterministic IDs, validation utilities, dataset configuration, CSV/JSON/SQL exports, README instructions, manifest and validation summary.
