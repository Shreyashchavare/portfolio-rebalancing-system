# Prompt P2-04 — Deterministic Export Metadata Fix

**AI Tool:** Antigravity  
**Phase:** 2 — Synthetic Data Foundation  
**Task:** Batch 2.4 — Deterministic Export Metadata Fix

## Prompt

# Phase 2.4 — Deterministic Export Metadata Fix

You are working in the existing repository:

`E:\Yottaflex\portfolio-rebalancing-system`

## Context

The starter dataset has been generated twice using:

```powershell
python -m synthetic_data.dataset_builder --config starter --seed 20261022 --export-dir data/run1
python -m synthetic_data.dataset_builder --config starter --seed 20261022 --export-dir data/run2
```

SHA-256 comparisons confirm:
- All 12 CSV files are identical.
- All 12 entity JSON files are identical.
- `validation_summary.json` is identical.
- `metadata.json`, `README.md`, and `sql/seed_data.sql` differ only because they contain runtime `generated_at` timestamps.
- The SQL checksum in metadata differs as a downstream consequence of the SQL timestamp comment.

## Objective

Make the complete export reproducible for identical configuration and seed inputs.

## Mandatory TDD workflow

1. Inspect the existing exporter, dataset builder, metadata generation, README generation, SQL export, and relevant tests.
2. Add regression tests first.
3. Run the new tests and demonstrate RED.
4. Implement the smallest appropriate fix.
5. Run the new tests and demonstrate GREEN.
6. Run the complete test suite.

## Implementation requirements

1. Remove runtime-dependent timestamps from deterministic export artifacts, or replace them with a deterministic value derived from the dataset configuration. Do not use the current wall-clock time.
2. Ensure `metadata.json` is identical across repeated runs with identical inputs.
3. Ensure `README.md` is identical across repeated runs.
4. Ensure the SQL seed file does not contain runtime-dependent comments or values.
5. Ensure the SQL checksum recorded in metadata matches the actual SQL file.
6. Preserve all existing CSV and JSON entity data exactly.
7. Preserve all existing entity counts, IDs, anomaly labels, validation behavior, and SQL insertion order.
8. Do not remove useful metadata fields merely to make hashes match. Keep the metadata informative and deterministic.
9. Do not hardcode a timestamp that falsely claims to be the actual generation time. Prefer deterministic dataset reference dates or an explicit reproducible build timestamp clearly documented as such.
10. Do not change the generator logic, dataset configuration, schema, or business calculations unless absolutely necessary.

## Tests

Add tests that verify:
- Two exports from identical inputs produce identical hashes for every artifact.
- Metadata is deterministic.
- README is deterministic.
- SQL output is deterministic.
- SQL checksum in metadata matches the actual exported SQL file.
- Existing dataset contents and validation results remain unchanged.

Use temporary directories for test exports.

## Constraints

- Keep the change focused on export reproducibility.
- Do not weaken or delete existing tests.
- Do not introduce new dependencies.
- Do not modify generated datasets manually.
- Save this exact prompt in `prompts/phase-2/04-deterministic-export-fix.md`.
- Add a short RED/GREEN execution record to that prompt file.

## Final report

Report:
1. Files inspected and changed.
2. New tests and RED results.
3. GREEN results.
4. Full pytest result.
5. Whether all export artifacts now produce identical SHA-256 hashes across two runs.
6. Any remaining limitations.

Stop after this batch. Do not begin Phase 3.

---

## Actual Results

### RED Phase
- Added regression tests in `tests/test_dataset_exporter.py`:
  - `test_repeated_exports_produce_identical_sha256_checksums(tmp_path)`: Verifies hash equality across two direct exports for `sql/seed_data.sql`, `README.md`, `metadata.json`, and all CSV/JSON artifacts.
  - `test_cli_repeated_runs_produce_identical_artifact_hashes(tmp_path)`: Verifies that running `python -m synthetic_data.dataset_builder` twice via CLI produces 100% identical file checksums across every exported artifact.
- Executed: `pytest tests/test_dataset_exporter.py -v`
- Result: **2 failed, 2 passed**
  - `test_repeated_exports_produce_identical_sha256_checksums` failed because `sql/seed_data.sql`, `README.md`, and `metadata.json` contained runtime-dependent timestamps (`datetime.now(timezone.utc)`).
  - `test_cli_repeated_runs_produce_identical_artifact_hashes` failed with differing hashes on `metadata.json`, `README.md`, and `sql/seed_data.sql`.

### GREEN Phase
- Updated `synthetic_data/dataset_config.py`:
  - Added deterministic fields `dataset_reference_date: str = "2026-01-15"` and `reproducible_build_timestamp: str = "2026-01-15T00:00:00Z"` to `DatasetConfig`.
- Updated `synthetic_data/exporters/dataset_exporter.py`:
  - Replaced runtime `datetime.now(timezone.utc)` in SQL export header with deterministic `-- Dataset Reference Date: {ref_date} (Deterministic Seed Export)`.
  - Replaced runtime timestamp in `metadata.json` with informative, explicit fields: `"dataset_reference_date"` and `"reproducible_build_timestamp"`.
  - Replaced runtime timestamp in `README.md` with `- **Dataset Reference Date:** {ref_date}` and `- **Reproducible Build Timestamp:** {build_ts}`.
- Re-executed: `pytest tests/test_dataset_exporter.py -v`
- Result: **4 passed**, 0 failed.
- End-to-end multi-run CLI verification (`data/run1` vs `data/run2`):
  - All 28 exported artifacts across CSV, JSON, SQL, and documentation produced 100% identical SHA-256 checksums.
- Executed full test suite: `pytest -v`
- Result: **238 passed**, 0 failed, 1 Starlette deprecation warning across 29 test files.
