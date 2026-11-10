# Prompt P2-08 — Complete Null Fallback Correction with Regression Coverage

**AI Tool:** Antigravity  
**Phase:** 2 — Synthetic Data Foundation  
**Task:** Batch 2.4 — Complete Null Fallback Correction with Regression Coverage

## Prompt

# Complete null fallback correction with regression coverage

Repository: `E:\Yottaflex\portfolio-rebalancing-system`

## Context
The exporter currently uses:
`"total_validation_errors": report.total_validation_errors if report else len(ground_truth)`

The fallback is semantically incorrect because ground-truth anomaly count is not validation-error count.

The production change to use `None` has already been made locally.

## Tasks

1. Inspect the current exporter implementation and existing exporter tests.
2. Add a regression test first that calls `export_dataset()` with `report=None`.
3. Verify the exported `validation_summary.json` contains:
   - `"total_validation_errors": null`
   - Existing fallback behavior for other fields remains unchanged.
4. Run the targeted test and demonstrate RED before implementation changes.
5. Make the smallest required production correction:
   `report.total_validation_errors if report else None`
6. Run targeted tests and demonstrate GREEN.
7. Run the complete test suite.
8. Verify deterministic export tests still pass.
9. Save this exact prompt and a concise RED/GREEN execution record in:
   `prompts/phase-2/08-null-validation-error-fallback.md`

## Constraints
- Do not modify unrelated code.
- Do not regenerate the full dataset.
- Do not modify database tables or SQL exports.
- Do not commit or push.
- Do not change existing anomaly reconciliation semantics.

## Deliverables
Report changed files, RED/GREEN results, full-suite result, and final validation-summary fallback behavior.

---

## Actual Results

### RED Phase
- Added regression test `test_export_validation_summary_fallback_when_report_is_none` in `tests/test_dataset_exporter.py`:
  - Executes `export_dataset()` with `report=None`.
  - Verifies `summary["total_validation_errors"] is None` (exported as JSON `null`).
  - Verifies other fallback fields remain unchanged (`is_cleanly_reconciled=True`, `total_anomalies=len(ground_truth)`, `matched_anomalies=len(ground_truth)`, `unreconciled_errors=[]`).
- Executed against previous logic (`report.total_validation_errors if report else len(ground_truth)`):
  ```powershell
  pytest tests/test_dataset_exporter.py -k test_export_validation_summary_fallback_when_report_is_none -v
  ```
- Result: **1 failed, 7 deselected**
  - Failure: `assert 5 is None`

### Implementation
- Updated line 182 in `synthetic_data/exporters/dataset_exporter.py`:
  ```python
  "total_validation_errors": report.total_validation_errors if report else None,
  ```

### GREEN Phase
- Executed:
  ```powershell
  pytest tests/test_dataset_exporter.py -k test_export_validation_summary -v
  ```
- Result: **2 passed, 6 deselected in 0.50s**
- Executed full exporter module:
  ```powershell
  pytest tests/test_dataset_exporter.py -v
  ```
- Result: **8 passed in 2.28s** (including deterministic export & artifact checksum tests).

### Full Suite Verification
- Executed: `pytest -v`
- Result: **249 passed, 1 warning in 4.33s** (0 regressions across entire test suite).

