# Prompt P2-06 — Fix Anomaly-Count Semantics and Verify Synthetic Dataset Reconciliation

**AI Tool:** Antigravity  
**Phase:** 2 — Synthetic Data Foundation  
**Task:** Batch 2.4 — Fix Anomaly-Count Semantics and Reconciliation Report

## Prompt

# Fix anomaly-count semantics and verify synthetic dataset reconciliation

## Context

Repository: `E:\Yottaflex\portfolio-rebalancing-system`

The full synthetic dataset has already been generated using:

```powershell
python -m synthetic_data.dataset_builder --config full --seed 20261022 --export-dir data/full
```

The dataset contains five ground-truth anomaly records:

1. ALLOCATION_SUM_MISMATCH
2. EXCESS_SELL_QUANTITY
3. EXCLUDED_INSTRUMENT_RECOMMENDED
4. MISSING_FEE
5. STALE_PRICE_USAGE

Current `data/full/validation_summary.json`:

```json
{
  "is_cleanly_reconciled": true,
  "total_anomalies": 6,
  "unreconciled_errors": []
}
```

Root cause: `validate_with_ground_truth()` currently sets `total_detected_anomalies=len(report.errors)`. Multiple validation errors can belong to one ground-truth anomaly record.

The five distinct ground-truth records are all matched, but six individual validation errors were detected.

## Objective

Correct the reporting semantics without weakening validation, hiding errors, changing generated records, or modifying the original anomaly injection behavior.

## Requirements

### 1. Reconciliation report

In `synthetic_data/validators/dataset_validator.py`:

- Keep `total_detected_anomalies` as the count of distinct matched anomaly records.
- Add `total_validation_errors` to represent the complete number of validation errors detected by `validate_baseline()`.
- Set:
  - `total_detected_anomalies = len(matched)`
  - `total_validation_errors = len(report.errors)`
- Preserve `matched_anomalies` and `unreconciled_errors`.
- Preserve the existing reconciliation condition: all ground-truth records must be matched and there must be zero unreconciled errors.
- Do not suppress duplicate-field errors or alter validation rules merely to obtain a count of five.

### 2. Exporter

Update `synthetic_data/exporters/dataset_exporter.py` so `validation_summary.json` reports:

```json
{
  "is_cleanly_reconciled": true,
  "total_anomalies": 5,
  "total_validation_errors": 6,
  "matched_anomalies": 5,
  "unreconciled_errors": []
}
```

Use the actual report values rather than hardcoding these expected numbers.

Keep deterministic export behavior. Do not introduce runtime timestamps or nondeterministic metadata.

### 3. Tests — write these first

Add or update tests in the existing validator and exporter test files.

Required regression coverage:

1. Five ground-truth records can match six validation errors.
2. `total_detected_anomalies` reports five.
3. `total_validation_errors` reports six.
4. All five ground-truth records are matched.
5. Unreconciled errors remain empty.
6. An additional validation error with an unknown record ID makes reconciliation fail.
7. Existing baseline validation tests remain unchanged in meaning.
8. Exported validation summary contains the distinct anomaly count and validation error count.
9. Repeated exports remain deterministic.

Use the existing test fixtures and conventions. Avoid duplicating large test fixtures unnecessarily.

## TDD execution sequence

1. Inspect relevant implementation and existing tests.
2. Add regression tests before changing production code.
3. Run targeted tests and show RED results.
4. Implement the smallest compatible correction.
5. Run targeted tests and show GREEN results.
6. Run the complete test suite.
7. Regenerate only the validation/export artifacts needed to update `data/full/validation_summary.json`; do not regenerate or mutate the underlying dataset unless necessary.
8. Verify the updated summary reports five distinct anomalies, six validation errors if that is what the validator detects, five matched anomalies, and zero unreconciled errors.
9. Recheck deterministic export behavior.

## Constraints

- Do not modify the five ground-truth records.
- Do not alter financial calculations, anomaly injection, SQL export, model definitions, or database configuration.
- Do not introduce new dependencies.
- Do not start PostgreSQL or import data in this task.
- Preserve existing public interfaces wherever possible.
- Keep the change focused.

## Deliverables

Report:
- Files changed.
- Tests added/updated.
- RED test results.
- GREEN test results.
- Full-suite result.
- Final validation summary.
- Confirmation that the full dataset's entity files and SQL export were not modified.

Save this exact prompt and a concise RED/GREEN execution record in the tracked `prompts/phase-2/` folder, following the existing naming convention.

Do not commit or push. I will review the changes and handle Git operations.

---

## Actual Results

### RED Phase
- Added regression tests in `tests/test_dataset_validator.py`:
  - `test_reconciliation_anomaly_count_semantics`: Verifies that 5 injected ground-truth anomalies match 6 raw validation errors, with `reconciliation.total_detected_anomalies == 5` and `reconciliation.total_validation_errors == 6`.
  - `test_reconciliation_fails_on_unknown_unreconciled_error`: Verifies that an unexpected error on a non-ground-truth trade causes `is_cleanly_reconciled` to be `False` with populated `unreconciled_errors`.
- Added test in `tests/test_dataset_exporter.py`:
  - `test_export_validation_summary_structure_and_counts`: Verifies that `validation_summary.json` written by `export_dataset` reports `total_anomalies == 5`, `total_validation_errors == 6`, and `matched_anomalies == 5`.
- Executed: `pytest tests/test_dataset_validator.py tests/test_dataset_exporter.py -v`
- Result: **2 failed, 9 passed**
  - `test_reconciliation_anomaly_count_semantics`: `AssertionError: assert 6 == 5` (`total_detected_anomalies` was 6).
  - `test_export_validation_summary_structure_and_counts`: `AssertionError: assert 6 == 5` (`summary["total_anomalies"]` was 6).

### Implementation
1. `synthetic_data/validators/dataset_validator.py`:
   - Updated `ReconciliationReport` dataclass with `total_validation_errors: int = 0`.
   - Updated `validate_with_ground_truth` to set:
     - `total_detected_anomalies = len(matched)` (count of distinct matched ground-truth records, evaluating to 5).
     - `total_validation_errors = len(report.errors)` (complete count of detected validation errors, evaluating to 6).
2. `synthetic_data/exporters/dataset_exporter.py`:
   - Updated `val_summary` dictionary to include:
     - `"total_anomalies": report.total_detected_anomalies if report else len(ground_truth)`
     - `"total_validation_errors": report.total_validation_errors if report else len(ground_truth)`
     - `"matched_anomalies": len(report.matched_anomalies) if report else len(ground_truth)`
     - `"unreconciled_errors": [...]`
3. `data/full/validation_summary.json`:
   - Updated summary artifact to reflect accurate semantics. Verified zero modifications or checksum changes across any underlying entity CSV, JSON, or SQL export files in `data/full/`.

### GREEN Phase
- Executed: `pytest tests/test_dataset_validator.py tests/test_dataset_exporter.py -v`
- Result: **11 passed in 1.76s**

### Full Suite Verification
- Executed: `pytest -v`
- Result: **246 passed, 1 warning in 3.59s** (100% test suite passing).

