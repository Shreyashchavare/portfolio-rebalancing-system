# Phase 2 — Anomalies, Export, Scaling and Reproducibility

## Anomaly design
Create valid baseline data before injecting deliberate, labelled edge cases. The source requirements include:
- Portfolio target weights not summing to 100%.
- Trade quantity exceeding the available holding.
- Recommendation involving an excluded instrument.
- Missing applicable fee schedule.
- Stale market price used without an adequate warning.

Each anomaly must have a documented `issue_type` and expected outcome in a separate ground-truth file. Do not leak labels into operational input features or corrupt unrelated rows.

## Export and validation
- Export CSV, JSON and SQL.
- Quote PostgreSQL identifiers safely, including reserved words.
- Handle null and validation errors explicitly; do not silently substitute misleading values.
- Validate PK/FK integrity, enums, date ranges, arithmetic, lifecycle values and duplicate records.
- Reconcile anomaly counts using clearly documented counting semantics.
- Include row counts, checksums, seed and dataset manifest.

## Reproducibility
Generate the same dataset twice using seed `20261022` in separate output directories. Compare row counts and SHA-256 checksums. Identical inputs and seed should produce byte-identical outputs.

## Scaling
Optimize full-scale generation and memory use without changing deterministic semantics. Keep the full dataset separate from the small live-demo dataset when loading the full dataset would make local evaluation unnecessarily heavy.

## Source-recorded evidence
The later audit reported identical outputs across 24 CSV/JSON files plus the SQL seed, and a full dataset containing 1,000 portfolios, 5,000 instruments, 5,000 holdings and 1.25 million market prices. These are historical reported results, not a substitute for rerunning the generator after future changes.
