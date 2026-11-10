# Prompt P2-02 — Master and Reference Data Generators (TDD)

**AI Tool:** Antigravity  
**Phase:** 2 — Synthetic Data Foundation  
**Task:** Batch 2.2 — Master and Reference Data Generators

## Prompt

# Phase 2 — Batch 2.2: Master and Reference Data Generators (TDD)

Project: portfolio-rebalancing-system

Existing baseline:
- 10 core SQLAlchemy entities.
- Deterministic ID utilities and reusable schema validators.
- 154 existing tests passing.
- Python 3.12, SQLAlchemy 2.x, Pandas, NumPy, pytest.

## Objective

Implement deterministic synthetic generators for investor profiles, portfolios, instruments, historical market prices, and target allocations.

All generators must produce valid baseline records with consistent IDs and foreign keys.

## 1. Generator architecture

Create the following modules:

- `synthetic_data/generators/investor_generator.py`
- `synthetic_data/generators/portfolio_generator.py`
- `synthetic_data/generators/instrument_generator.py`
- `synthetic_data/generators/market_price_generator.py`
- `synthetic_data/generators/target_allocation_generator.py`

Create shared configuration only if needed:
- `synthetic_data/config.py`

Use pure or isolated generator functions with explicit inputs. Avoid global mutable state.

Each generator should accept:
- A seed or deterministic random generator.
- Required parent records or IDs.
- A configurable record count where applicable.

Use `numpy.random.default_rng(seed)` or another deterministic local RNG. Do not use global random state.

## 2. InvestorProfile generator

Generate:
- Deterministic `INV-000001` IDs.
- Names from synthetic, non-identifying name components.
- Risk categories: LOW, MODERATE, HIGH.
- Valid required fields and timestamps.

Allow configurable investor count.

## 3. Portfolio generator

Generate:
- Deterministic portfolio IDs using the existing ID utility.
- Valid investor foreign keys.
- Portfolio names.
- Base currencies.
- ACTIVE/INACTIVE status.
- Valid creation timestamps.

Support configurable portfolios per investor.

## 4. Instrument generator

Generate:
- Deterministic `INS-000001` IDs.
- Unique symbols.
- Instrument names.
- Asset classes.
- Positive Decimal lot sizes.
- Active/inactive flags.

Include a representative range of asset classes such as EQUITY, DEBT, ETF, GOLD, and CASH.

Do not generate real financial instrument recommendations or claim that synthetic prices are market prices.

## 5. MarketPrice generator

Generate:
- Positive Decimal prices.
- Valid instrument foreign keys.
- Trading dates over a configurable number of trading days.
- A required source label such as SYNTHETIC.
- Unique `(instrument_id, price_date)` records.

Use deterministic price paths with controlled variation. Avoid negative or zero prices.

Support configurable trading-day count. The full-scale configuration must support 250 trading days.

Do not generate missing-price anomalies in this batch.

## 6. TargetAllocation generator

Generate:
- Valid portfolio foreign keys.
- Asset-class target weights using Decimal.
- Effective dates.
- Valid allocation weights between 0 and 100 inclusive.

For each generated portfolio, baseline target allocations must sum to exactly 100.0000%.

Use a deterministic allocation strategy based on investor risk category. Document the allocation assumptions; do not present them as financial advice.

Ensure each generated allocation has valid effective dates and no duplicate `(portfolio_id, asset_class, effective_from)` keys.

## 7. Shared requirements

- Use existing ID utilities.
- Reuse schema validators where appropriate.
- Return records in a consistent structure suitable for CSV/JSON export in Batch 2.3.
- Keep financial values as Decimal until serialization.
- Ensure all generated foreign keys refer to existing parent records.
- Support a small starter dataset and the eventual full dataset using the same functions.
- Fixed seed default: `20261022`.
- Do not connect to PostgreSQL or write to the database in this batch.
- Do not introduce anomaly injection yet.

## 8. TDD execution

Create tests first:

- `tests/test_investor_generator.py`
- `tests/test_portfolio_generator.py`
- `tests/test_instrument_generator.py`
- `tests/test_market_price_generator.py`
- `tests/test_target_allocation_generator.py`

Test:
- Expected record counts.
- Exact ID conventions.
- Deterministic output for the same seed.
- Different output for different seeds where random attributes are involved.
- Valid enum values.
- Unique IDs and symbols.
- Foreign-key integrity.
- Decimal precision and positive values.
- Market-price date coverage and uniqueness.
- Target allocations sum to exactly 100.0000% per portfolio.
- Empty and small dataset handling.
- Existing validators accept generated baseline records.

Run all new tests first and verify RED. Implement generators, run focused tests, then the full test suite.

## 9. Restrictions

- Do not modify SQLAlchemy model schemas.
- Do not implement holdings, fees, constraints, trades, proposals, anomaly injection, or export yet.
- Do not add dependencies unless necessary.
- Do not use Python float for financial values.
- Do not hardcode dataset outputs.
- Keep the code modular and minimal.

## 10. Prompt record

Save this exact prompt as:

`prompts/phase-2/02-master-reference-generators.md`

Append concise RED/GREEN execution results and document deterministic generation assumptions.

## 11. Final report

Report:
- Changed files.
- Generator functions and input/output structures.
- Seed and determinism behavior.
- Record counts in tests.
- Target allocation reconciliation.
- RED/GREEN results.
- Full test count and warnings.
- Git status.

Stop after Batch 2.2.

---

## Actual Results

### RED Phase
- Created test suites covering all 5 generators (27 total tests):
  - `tests/test_investor_generator.py` (6 tests)
  - `tests/test_portfolio_generator.py` (5 tests)
  - `tests/test_instrument_generator.py` (6 tests)
  - `tests/test_market_price_generator.py` (5 tests)
  - `tests/test_target_allocation_generator.py` (5 tests)
- Executed: `pytest tests/test_*_generator.py -v`
- Result: **27 failed** out of 27 tests due to missing generator modules (`ModuleNotFoundError: No module named 'synthetic_data.generators.investor_generator'`).
- Pre-existing suite check: All 154 pre-existing tests passed (`pytest -k "not test_investor_generator and not test_portfolio_generator and not test_instrument_generator and not test_market_price_generator and not test_target_allocation_generator" -v`).

### GREEN Phase
- Implemented pure, isolated generators using `numpy.random.default_rng(seed)` with default seed `20261022`:
  - `synthetic_data/generators/investor_generator.py`: `generate_investors(count, seed, base_created_at)`
  - `synthetic_data/generators/portfolio_generator.py`: `generate_portfolios(investors, portfolios_per_investor, seed, base_currency, base_created_at)`
  - `synthetic_data/generators/instrument_generator.py`: `generate_instruments(count, seed)`
  - `synthetic_data/generators/market_price_generator.py`: `generate_market_prices(instruments, trading_days, start_date, seed, source)`
  - `synthetic_data/generators/target_allocation_generator.py`: `generate_target_allocations(portfolios, investors, effective_from, effective_to, seed)`
- Exported all generator functions in `synthetic_data/generators/__init__.py`.
- Executed focused tests: `pytest tests/test_*_generator.py -v` $\rightarrow$ **27 passed**, 0 failed.
- Executed full test suite: `pytest -v` $\rightarrow$ **181 passed**, 0 failed, 1 Starlette deprecation warning across 19 test files.

### Deterministic Generation Assumptions
1. **Local RNG & Seed Isolation**: Each generator accepts an optional `seed: int = 20261022` or `np.random.Generator`. Functions construct local instances using `np.random.default_rng(seed)` to guarantee reproducible outputs without polluting Python or NumPy global random states.
2. **Names & Identifiers**: Names are synthesized by combining non-identifying token pools (e.g., `["Alpha", "Apex", "Beacon", ...]` and `["Capital", "Ventures", "Holdings", ...]`). IDs strictly use zero-padded formats via `synthetic_data.id_generator`.
3. **Asset Class Coverage**: Instruments span 5 distinct asset classes: `EQUITY`, `DEBT`, `ETF`, `GOLD`, `CASH`. Lot sizes are Decimal integers or fractions strictly greater than zero (e.g., equity lot size 1, debt 10, cash 1).
4. **Market Price Geometric Random Walk**:
   - Initial base prices vary deterministically per asset class (Equities ~100-3000, Debt ~1000, Gold ~6000, Cash = 1.0000).
   - Daily returns are bounded using normal random variables calibrated per asset volatility (`max(0.01, price * (1 + return))`).
   - Trading days advance strictly on weekdays (skipping Saturday and Sunday) up to 250 trading days.
   - Prices are formatted as `Decimal(f"{price:.4f}")` and guaranteed strictly positive.
5. **Target Allocation Strategy & 100.0000% Reconciliation**:
   - Mapped deterministically by investor risk category:
     - `LOW`: EQUITY (20.0000%), DEBT (50.0000%), GOLD (10.0000%), CASH (20.0000%) = 100.0000%
     - `MODERATE`: EQUITY (50.0000%), DEBT (30.0000%), ETF (10.0000%), CASH (10.0000%) = 100.0000%
     - `HIGH`: EQUITY (70.0000%), DEBT (10.0000%), ETF (15.0000%), CASH (5.0000%) = 100.0000%
   - Fallback/uniform splits assign the exact remainder to the final asset class, guaranteeing `sum(target_weight) == Decimal("100.0000")` with zero rounding error.

