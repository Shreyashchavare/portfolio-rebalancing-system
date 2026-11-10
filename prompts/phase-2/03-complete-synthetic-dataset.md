# Prompt P2-03 — Complete Synthetic Dataset, Anomalies and Export (TDD)

**AI Tool:** Antigravity  
**Phase:** 2 — Synthetic Data Foundation  
**Task:** Batch 2.3 — Complete Synthetic Dataset, Anomalies and Export

## Prompt

# Phase 2 — Batch 2.3: Complete Synthetic Dataset, Anomalies and Export (TDD)

Project: portfolio-rebalancing-system

Existing baseline:
- 10 core SQLAlchemy entities.
- Data dictionary, deterministic ID utilities and schema validators.
- Five master/reference generators implemented.
- 181 existing tests passing.
- Fixed seed: 20261022.

## Objective

Complete the synthetic dataset by generating holdings, fee schedules, constraints, proposals and trades; calculate derived portfolio metrics; inject labelled anomalies; validate the complete dataset; and export reproducible CSV/JSON/SQL seed data.

## 1. Remaining generators

Create:

- `synthetic_data/generators/holding_generator.py`
- `synthetic_data/generators/fee_schedule_generator.py`
- `synthetic_data/generators/constraint_generator.py`
- `synthetic_data/generators/rebalance_proposal_generator.py`
- `synthetic_data/generators/trade_generator.py`

Requirements:

### Holding
- Generate consistent `HOLD-<portfolio-id>-<instrument-id>` IDs.
- Valid portfolio and instrument references.
- Positive Decimal quantities.
- Valid as_of_date snapshots.
- Use generated instrument lot sizes where relevant.
- Avoid duplicate `(portfolio_id, instrument_id, as_of_date)` records.

### FeeSchedule
- Generate multiple fee tiers for asset classes and BUY/SELL sides.
- Valid trade-value ranges, rates, fixed fees, minimum/maximum fees and effective dates.
- Use Decimal throughout.
- Ensure no overlapping tiers for the same asset class, trade side and effective period.
- Include open-ended upper tiers where appropriate.

### Constraint and ConstraintInstrument
- Generate portfolio-, asset-class- and instrument-scoped constraints.
- Generate HARD and SOFT severities.
- Generate supported constraint types.
- Generate valid effective dates and nonnegative thresholds.
- Generate valid bridge-table associations for instrument-specific constraints.
- Keep polymorphic scope references consistent with their scope type.

### RebalanceProposal
- Generate deterministic proposal IDs using the existing ID utility.
- Reference valid portfolios.
- Generate valid proposal status and review decision combinations.
- Calculate proposal values from generated portfolio/holding data where applicable.
- Keep timestamps and lifecycle values coherent.

### Trade
- Generate valid BUY/SELL trades linked to proposals and instruments.
- Use positive Decimal quantity, price and trade value.
- Compute fee amounts deterministically from applicable fee tiers.
- Reference applicable FeeSchedule rows.
- Keep trade statuses consistent with proposal state.
- Do not generate real trade executions.

## 2. Derived calculations

Create:

`synthetic_data/calculations.py`

Implement deterministic calculations for:
- Position market value = quantity × applicable market price.
- Portfolio market value = sum of position values plus cash, if represented.
- Current asset-class weights.
- Allocation drift = current weight − target weight.
- Trade notional.
- Fee calculation using matching fee tiers.

Use Decimal arithmetic and explicit rounding rules.

Do not independently generate derived values that can be calculated from source records.

Document how cash is represented. Do not silently invent a CashBalance entity.

## 3. Valid baseline first

Generate valid baseline records before introducing anomalies.

The baseline must satisfy:
- Referential integrity.
- Target allocations sum to exactly 100%.
- Positive prices and quantities.
- Fee tier validity and fee consistency.
- Valid constraint associations.
- Coherent proposal and trade statuses.
- Reconciled portfolio values and weights.

## 4. Anomaly injection

Create:

`synthetic_data/anomaly_injector.py`

Inject only the five required challenge anomalies:

1. Portfolio allocation weights do not sum to 100%.
2. Trade quantity exceeds available holding.
3. Excluded instrument is recommended.
4. Required fee is omitted.
5. Stale market price is used without a stale-price flag.

Requirements:
- Inject anomalies only after valid baseline generation.
- Keep each anomaly identifiable through `issue_type` and a separate ground-truth record.
- Do not corrupt unrelated rows.
- Do not silently alter source records.
- Preserve original baseline data or provide an explicit copy/variant.
- Keep ground-truth labels completely separate from model input features.

Ground truth should include at least:
- Record identifier.
- Issue type.
- Expected decision or label.
- Relevant explanation.

## 5. Dataset validation

Create:

`synthetic_data/validators/dataset_validator.py`

Validate:
- Primary-key uniqueness.
- All foreign-key relationships.
- Allowed enum values.
- Effective-date ordering.
- Arithmetic reconciliation.
- Portfolio allocation totals.
- Fee calculations.
- Trade quantity versus holdings.
- Constraint and bridge-table consistency.
- Lifecycle status consistency.
- Duplicate snapshots.
- Anomaly labels and ground-truth correspondence.

Return structured validation results.

Baseline validation must fail if invalid baseline records exist. Anomaly validation must distinguish expected labelled anomalies from accidental corruption.

## 6. Dataset configuration and orchestration

Create:

- `synthetic_data/dataset_config.py`
- `synthetic_data/dataset_builder.py`

Support two configurations using the same generator pipeline:

Starter:
- Small configurable counts for rapid local development.

Full:
- 1,000 portfolios.
- 5,000 instruments/holdings.
- 250 trading days.

Use seed `20261022` by default.

Generation order:
1. Investors.
2. Portfolios.
3. Instruments.
4. Market prices.
5. Target allocations.
6. Holdings.
7. Fee schedules.
8. Constraints and bridge associations.
9. Derived calculations.
10. Rebalance proposals.
11. Trades.
12. Validate baseline.
13. Inject labelled anomalies.
14. Validate final dataset and ground truth.

Avoid unnecessary database connections.

## 7. Export

Create:

`synthetic_data/exporters/dataset_exporter.py`

Export:
- CSV files for each entity/table.
- JSON dataset or JSON files per entity.
- SQL seed data suitable for the implemented schema.
- Separate `ground_truth.csv` and/or `ground_truth.json`.
- Dataset README and generation metadata.
- Validation summary.
- Source manifest.

Ensure Decimal and date serialization is explicit and lossless enough for the defined precision.

Do not include ground-truth labels in ordinary entity exports.

## 8. Reproducibility

Create tests proving:
- Same seed and configuration produce identical logical records.
- Same seed produces identical row counts and checksums.
- Different seeds change randomized attributes.
- Exported files have stable ordering.
- Ground truth remains separate from input data.
- Starter and full configurations use the same generation pipeline.

Provide a CLI command such as:

`python -m synthetic_data.dataset_builder --config starter --seed 20261022`

and:

`python -m synthetic_data.dataset_builder --config full --seed 20261022`

Do not require PostgreSQL just to generate or validate files.

## 9. TDD execution

Create tests first for:
- Each remaining generator.
- Derived calculations.
- Anomaly injection.
- Dataset validation.
- Dataset builder.
- Export and reproducibility.

Run new tests first and verify RED.

Implement in logical order, run focused tests, then full suite.

Run a small starter dataset end-to-end. Do not run the full 1,000-portfolio generation until the starter dataset passes all validation.

## 10. Restrictions

- Do not modify SQLAlchemy entity schemas.
- Do not add unrelated entities.
- Do not use floats for financial arithmetic.
- Do not leak ground truth into features.
- Do not connect to real trading or market systems.
- Do not add dependencies unless absolutely necessary.
- Keep generation deterministic and modular.
- Do not weaken existing tests.

## 11. Prompt record

Save this exact prompt as:

`prompts/phase-2/03-complete-synthetic-dataset.md`

Append RED/GREEN results, schema assumptions, generation commands, and starter dataset validation results.

## 12. Final report

Report:
- Changed files.
- Generator coverage.
- Calculation rules.
- Anomaly counts by issue type.
- Ground-truth separation.
- Starter dataset row counts.
- Validation results.
- Reproducibility/checksum results.
- RED/GREEN test results.
- Full test count and warnings.
- Git status.

Stop after Batch 2.3.

---

## Actual Results

### RED Phase
- Created 10 new test suites covering the remaining generators, calculations, anomalies, validation, pipeline orchestration, and export:
  - `tests/test_holding_generator.py` (8 tests)
  - `tests/test_fee_schedule_generator.py` (6 tests)
  - `tests/test_constraint_generator.py` (7 tests)
  - `tests/test_calculations.py` (7 tests)
  - `tests/test_rebalance_proposal_generator.py` (5 tests)
  - `tests/test_trade_generator.py` (5 tests)
  - `tests/test_anomaly_injector.py` (8 tests)
  - `tests/test_dataset_validator.py` (4 tests)
  - `tests/test_dataset_builder.py` (3 tests)
  - `tests/test_dataset_exporter.py` (2 tests)
- Executed: `pytest tests/test_holding_generator.py ... -v`
- Result: **10 test files failed collection** due to missing modules (`ModuleNotFoundError: No module named 'synthetic_data.generators.holding_generator'`, etc.).
- Pre-existing suite check: All 181 pre-existing tests passed (`pytest tests/test_*_generator.py -v`).

### GREEN Phase
- Implemented all modules:
  - `synthetic_data/id_generator.py`: Added `generate_trade_id`, `generate_constraint_id`, and `generate_fee_schedule_id`.
  - `synthetic_data/generators/holding_generator.py`: Generates `HOLD-<portfolio_id>-<instrument_id>` positions, enforces lot size multiples, and provides mandatory CASH positions.
  - `synthetic_data/generators/fee_schedule_generator.py`: Generates non-overlapping multi-tier fee structures for BUY/SELL across all asset classes with open-ended upper tiers.
  - `synthetic_data/generators/constraint_generator.py`: Generates PORTFOLIO-, ASSET_CLASS-, and INSTRUMENT-scoped constraints with HARD/SOFT severities and bridge records in `constraint_instrument`.
  - `synthetic_data/calculations.py`: Pure Decimal functions for position market value, portfolio market value, asset-class weights, allocation drift, trade notional, and tiered fee calculation.
  - `synthetic_data/generators/rebalance_proposal_generator.py`: Generates proposals with coherent `(status, review_decision)` lifecycle states.
  - `synthetic_data/generators/trade_generator.py`: Generates trades with valid holding SELL limits, matching fee schedule tiers, and status coherence.
  - `synthetic_data/generators/__init__.py`: Exported all 10 generator functions.
  - `synthetic_data/anomaly_injector.py`: Injects exactly 5 labelled challenge anomalies into isolated deep-copies while generating structured `GroundTruthRecord` entries.
  - `synthetic_data/validators/dataset_validator.py`: Comprehensive validator covering foreign keys, primary keys, date ordering, arithmetic, allocation totals, trade fees, and anomaly reconciliation.
  - `synthetic_data/dataset_config.py`: Defines `DatasetConfig`, `STARTER_CONFIG`, and `FULL_CONFIG`.
  - `synthetic_data/exporters/dataset_exporter.py`: Lossless export to CSV, JSON, and SQL seed scripts with separate `ground_truth` artifacts, `metadata.json`, and SHA-256 checksums.
  - `synthetic_data/dataset_builder.py`: 14-step orchestration pipeline with CLI entrypoint (`python -m synthetic_data.dataset_builder`).
- Executed new tests: `pytest tests/test_holding_generator.py ... -v` $\rightarrow$ **55 passed**, 0 failed.
- Executed full test suite: `pytest -v` $\rightarrow$ **236 passed**, 0 failed, 1 Starlette deprecation warning across all 29 test files.

### Schema & Generation Assumptions
1. **Cash Representation**: Cash is not a separate entity table. It is represented as a holding in a CASH asset-class instrument (`CSH-USD-MM` or similar) with price `1.0000`, lot size `1.0000`, and quantity representing currency balance. This integrates seamlessly into `Holding`, `MarketPrice`, and `TargetAllocation` without inventing schema tables.
2. **Deterministic Tiered Fees**:
   - Tier 1: [0, 10,000], 15 bps + \$5.00 fixed (min \$10, max \$50).
   - Tier 2: [10,000, 100,000], 10 bps + \$10.00 fixed (min \$20, max \$200).
   - Tier 3: [100,000, None], 5 bps + \$25.00 fixed (min \$50, open-ended).
   - Cash transactions incur 0 bps fee; debt incurs 50% bps rate.
3. **5 Injected Challenge Anomalies**:
   - `ALLOCATION_SUM_MISMATCH`: Target allocations sum to 105.0000% (target_allocation row modified).
   - `EXCESS_SELL_QUANTITY`: SELL trade quantity exceeds available portfolio holding units.
   - `EXCLUDED_INSTRUMENT_RECOMMENDED`: BUY trade recommends purchasing an instrument with an active `EXCLUDED_INSTRUMENT` constraint.
   - `MISSING_FEE`: Mandatory fee is omitted (`fee_amount = 0.0000`, `fee_schedule_id = None`) on a non-zero trade.
   - `STALE_PRICE_USAGE`: Trade uses a historical/stale unit price instead of current market price.
4. **Ground-Truth Separation**: Ground-truth records are stored strictly in `csv/ground_truth.csv` and `json/ground_truth.json`. Model input features, entity CSVs, JSON tables, and `sql/seed_data.sql` contain zero leakage of anomaly labels.

### Generation Commands & Starter Dataset Validation
```bash
# Generate and export starter dataset
python -m synthetic_data.dataset_builder --config starter --seed 20261022 --export-dir data/starter
```

Starter row counts generated and validated:
- `investor_profile`: 5
- `portfolio`: 10
- `instrument`: 20
- `market_price`: 600 (20 instruments × 30 trading days)
- `target_allocation`: 40
- `holding`: 53
- `fee_schedule`: 30
- `constraint`: 28
- `constraint_instrument`: 3
- `rebalance_proposal`: 10
- `trade`: 20
- `ground_truth`: 5 labelled anomalies

Validation & Reconciliation Outcome:
- `is_cleanly_reconciled`: `true`
- `unreconciled_errors`: `[]` (0 unexpected errors)

