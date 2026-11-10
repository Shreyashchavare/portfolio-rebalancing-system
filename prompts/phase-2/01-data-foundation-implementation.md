# Prompt P2-01 — Data Dictionary, Validation Framework and ID Utilities (TDD)

**AI Tool:** Antigravity  
**Phase:** 2 — Synthetic Data Foundation  
**Task:** Batch 2.1 — Data Dictionary, Validation Framework and ID Utilities

## Prompt

# Phase 2 — Batch 2.1: Data Dictionary, Validation Framework and ID Utilities (TDD)

Project: portfolio-rebalancing-system

Existing baseline:
- 10 core database entities implemented.
- 135 existing tests passing.
- Python 3.12, SQLAlchemy 2.x, Pydantic 2.x, pytest.
- Preserve the existing modular-monolith architecture.

## Objective

Build the foundation for deterministic synthetic data generation before implementing individual data generators.

## 1. Data dictionary

Create:

`docs/data-dictionary.md`

Document all 10 core entities:

1. InvestorProfile
2. Portfolio
3. Instrument
4. Holding
5. MarketPrice
6. TargetAllocation
7. Trade
8. FeeSchedule
9. Constraint
10. RebalanceProposal

For every field document:
- Field name
- Data type
- Required/optional
- Allowed values
- Units
- Uniqueness
- Validation rule
- Foreign-key relationship, if applicable

Use the actual SQLAlchemy model definitions as the source of truth. Do not invent columns or silently change existing schemas.

Document the ConstraintInstrument bridge table and its composite primary key separately.

Clearly identify any schema gaps or assumptions instead of silently correcting them.

## 2. Deterministic ID utilities

Create:

`synthetic_data/id_generator.py`

Implement deterministic, zero-padded ID generation for:

- Investor: `INV-000001`
- Portfolio: `PORT-<investor-id>-01`
- Instrument: `INS-000001`
- Holding: `HOLD-<portfolio-id>-<instrument-id>`
- Rebalance proposal: `RB-2026-000001`

Requirements:
- IDs must be deterministic.
- IDs must be immutable after generation.
- Referenced IDs must match exactly.
- Counters must be zero-padded.
- Avoid global mutable counters.
- Support repeatable generation with explicit input/index values.

## 3. Validation framework

Create:

`synthetic_data/validators/schema_validator.py`

Implement reusable validation for:
- Required fields and nullability.
- Primary-key uniqueness.
- Foreign-key integrity.
- Allowed enum values.
- Date ordering.
- Numeric bounds.
- Duplicate records.

The framework should accept generated records in a simple, testable structure such as lists of dictionaries or Pandas DataFrames.

Do not implement dataset-specific anomaly injection yet.

Return structured validation results containing:
- Validation name
- Passed/failed status
- Invalid record count
- Useful error details

Do not silently discard invalid rows.

## 4. Test-first implementation

Create tests first:

- `tests/test_id_generator.py`
- `tests/test_schema_validator.py`

Test:
- Exact ID formats.
- Deterministic output for identical inputs.
- Different IDs for different inputs.
- Portfolio and holding ID composition.
- Primary-key duplicates.
- Missing required values.
- Invalid foreign keys.
- Invalid enums.
- Invalid date ranges.
- Numeric boundary violations.
- Structured validation results.
- Empty datasets.

Run the new tests first and verify RED.

Then implement the modules and run focused tests followed by the entire test suite.

## 5. Restrictions

- Do not implement entity-specific data generators yet.
- Do not modify SQLAlchemy models or database schemas.
- Do not add dependencies unless absolutely necessary.
- Do not use random values in ID generation.
- Do not introduce anomaly injection yet.
- Keep validators reusable and independent of database connections.
- Preserve all existing tests.

## 6. Prompt record

Save this exact prompt as:

`prompts/phase-2/01-data-foundation-implementation.md`

Create `prompts/phase-2/` if it does not exist.

Append a concise RED/GREEN execution record.

## 7. Final report

Report:
- Changed files
- Data dictionary coverage
- ID utility behavior
- Validation rules implemented
- RED/GREEN results
- Full test count
- Warnings
- Git status

Stop after Batch 2.1.

---

## Actual Results

### RED Phase
- Created test suites `tests/test_id_generator.py` (7 tests) and `tests/test_schema_validator.py` (12 tests).
- Executed: `pytest tests/test_id_generator.py tests/test_schema_validator.py -v`
- Result: **19 failed** out of 19 tests due to missing `synthetic_data.id_generator` and `synthetic_data.validators.schema_validator` modules.
- Pre-existing suite check: All 135 pre-existing tests passed (`pytest -k "not test_id_generator and not test_schema_validator" -v`).

### GREEN Phase
- Created `docs/data-dictionary.md` documenting all 10 core entities and `ConstraintInstrument`, field definitions, types, constraints, and documented schema gaps/assumptions.
- Created `synthetic_data/id_generator.py` implementing zero-padded, pure, deterministic ID utilities with parameter validation (`generate_investor_id`, `generate_portfolio_id`, `generate_instrument_id`, `generate_holding_id`, `generate_proposal_id`).
- Created `synthetic_data/validators/schema_validator.py` implementing `SchemaValidator`, `ValidationResult`, and `ValidationErrorDetail` with rules for required fields, PK/composite uniqueness, FK integrity, enum domain validation, date ordering, and numeric boundaries.
- Updated `synthetic_data/validators/__init__.py` to export the validator classes.
- Executed: `pytest -v`
- Result: **154 passed**, 0 failed across all 14 test suites (135 existing + 19 new).

