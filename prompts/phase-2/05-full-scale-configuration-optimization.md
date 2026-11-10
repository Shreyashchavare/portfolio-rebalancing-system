# Prompt P2-05 — Full-Scale Configuration and Memory Optimization

**AI Tool:** Antigravity  
**Phase:** 2 — Synthetic Data Foundation  
**Task:** Batch 2.4 — Full-Scale Configuration and Memory Optimization

## Prompt

# Phase 2.4 — Full-Scale Configuration and Memory Optimization

Repository:
`E:\Yottaflex\portfolio-rebalancing-system`

## Objective

Implement the minimal changes identified in the Full-Scale Configuration and Capacity Audit.

Target:
- 500 investors
- 1,000 portfolios
- 5,000 instruments
- Exactly 5,000 holdings
- 250 trading days
- Seed: 20261022

## Important

This is an audit-first task. Do not start full-scale generation, modify PostgreSQL, or change production code before reporting findings.

## Mandatory TDD workflow

1. Inspect the existing implementation and tests.
2. Write regression tests first.
3. Run tests and demonstrate RED.
4. Implement the minimal changes.
5. Run focused tests and demonstrate GREEN.
6. Run the complete test suite.

## Task 1 — Correct FULL_CONFIG

Update only FULL_CONFIG in `synthetic_data/dataset_config.py`:

- investor_count = 500
- portfolios_per_investor = 2
- instrument_count = 5000
- trading_days = 250
- min_holdings = 4
- max_holdings = 4
- proposals_per_portfolio = 1
- trades_per_proposal = 2
- seed = 20261022

Keep STARTER_CONFIG unchanged.

The holding generator currently adds one cash holding plus the configured number of non-cash holdings per portfolio. Setting min_holdings = max_holdings = 4 ensures:
- 1 cash holding per portfolio
- 4 non-cash holdings per portfolio
- 5 holdings per portfolio
- Exactly 5,000 holdings across 1,000 portfolios

Verify this logic by test before and after editing.

## Task 2 — Holding generator verification

Verify that `synthetic_data/generators/holding_generator.py`:
- Generates valid holdings.
- Preserves unique holding IDs: `HOLD-<portfolio-id>-<instrument-id>`.
- Does not sample non-cash instruments with replacement for the same portfolio.
- Generates positive quantities matching instrument lot size.
- Produces exactly 5,000 holdings for 1,000 portfolios when configured with min_holdings = 4 and max_holdings = 4.

Add or update unit tests to prove this.

## Task 3 — Selective copy in anomaly injector

Refactor `synthetic_data/anomaly_injector.py`:
- Do not perform deep copies of the entire dataset.
- Large tables like `market_price` (1,250,000 records at full scale) are never modified by anomalies.
- Deep copy only the tables that anomalies modify:
  - `target_allocation` (Allocation Sum Mismatch)
  - `trade` (Excess Sell Quantity, Missing Fee, Excluded Instrument, Stale Price Usage)
- Pass all other tables through by reference or shallow copy.

Verify this behavior by test:
- Ensure the original dataset is not modified by anomaly injection.
- Ensure `market_price` is not deep copied.
- Ensure all 5 anomaly types are correctly injected.
- Ensure ground-truth labels are correctly generated.

## Task 4 — Tests

Write tests verifying:
- FULL_CONFIG parameter values match challenge requirements.
- FULL_CONFIG produces exactly 5,000 holdings across 1,000 portfolios.
- STARTER_CONFIG remains unchanged.
- Anomaly injector mutates only target_allocation and trade, leaving other tables isolated and unmodified.
- Baseline dataset is preserved when anomalies are injected.

## Task 5 — Prompt record

Save this exact prompt in:
`prompts/phase-2/05-full-scale-configuration-optimization.md`

Add a short RED/GREEN execution record to that file.

## Final report

Report:
1. Files inspected and modified.
2. RED test results.
3. GREEN test results.
4. Full pytest result.
5. Confirmation of exact holding counts (5,000 across 1,000 portfolios).
6. Confirmation that STARTER_CONFIG remains unchanged.
7. Confirmation of anomaly copy isolation (market_price not copied, trade and target_allocation isolated).
8. Any remaining limitations or operational notes.

Stop after this batch. Do not run the full dataset build, do not modify PostgreSQL, and do not begin Phase 3.

---

## Actual Results

### RED Phase
- Added regression tests in `tests/test_dataset_config.py`:
  - `test_starter_config_parameters_unchanged`: Validates STARTER_CONFIG immutability.
  - `test_full_config_parameters_match_challenge_requirements`: Validates challenge parameters (500 investors, 2 portfolios/investor, 5,000 instruments, 250 trading days, min_holdings=4, max_holdings=4, proposals_per_portfolio=1, trades_per_proposal=2, seed=20261022).
  - `test_full_config_exact_holdings_math`: Validates exact mathematical calculation for 5,000 holdings.
- Added tests in `tests/test_holding_generator.py`:
  - `test_generate_holdings_exact_five_per_portfolio`: Verifies sampling without replacement and exactly 5 holdings (1 cash + 4 non-cash) per portfolio.
- Added and updated tests in `tests/test_anomaly_injector.py`:
  - `test_selective_copying_and_memory_isolation`: Asserts that `market_price`, `portfolio`, `investor_profile`, etc., are passed by reference (`is` identity check), while `target_allocation` and `trade` are isolated deep copies.
- Executed: `pytest tests/test_dataset_config.py tests/test_holding_generator.py tests/test_anomaly_injector.py -v`
- Result: **8 failed, 13 passed**
  - `test_full_config_parameters_match_challenge_requirements` failed: `assert 100 == 5000` (FULL_CONFIG instrument count).
  - `test_full_config_exact_holdings_math` failed: `assert 3 == 4` (FULL_CONFIG min_holdings).
  - `test_selective_copying_and_memory_isolation` and individual anomaly tests failed: `market_price` was deep-copied, failing object reference identity check (`assert anomalous_data['market_price'] is baseline['market_price']`).

### Implementation
1. `synthetic_data/dataset_config.py`:
   - Updated `FULL_CONFIG`: `instrument_count = 5000`, `min_holdings = 4`, `max_holdings = 4`.
   - Maintained `STARTER_CONFIG` unchanged (`min_holdings = 3`, `max_holdings = 8`).
2. `synthetic_data/anomaly_injector.py`:
   - Introduced `_copy_dataset_selectively(dataset, mutate_tables)` to perform top-level dict shallow copy and deep copy only tables targeted for mutation (`target_allocation`, `trade`).
   - Refactored `inject_all_anomalies` to copy mutable tables exactly once.
   - Replaced full list comprehension in `inject_stale_price_usage` with generator expression `next(...)` to eliminate memory and traversal overhead on 1.25M price records.

### GREEN Phase
- Executed: `pytest tests/test_dataset_config.py tests/test_holding_generator.py tests/test_anomaly_injector.py -v`
- Result: **21 passed in 0.20s** (100% focused tests passing).

### Full Suite Verification
- Executed: `pytest -v`
- Result: **243 passed, 1 warning in 3.50s** (0 regressions across entire test suite).

