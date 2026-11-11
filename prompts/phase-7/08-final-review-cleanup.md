# Phase 7.2 — Final Test Quality Cleanup

## Original Prompt

Make only these two targeted improvements. Do not refactor unrelated code.

1. Fix the vacuous chunk rollback assertion in `tests/test_ingest_policies.py`.
   - Replace the `"DOC2"` substring check with assertions using actual `PolicyDocument.id` and `PolicyChunk.document_id` relationships.
   - Prove that the failed document and all its chunks were rolled back.
   - Prove that successful earlier and later documents remain persisted.

2. Handle legacy NULL migration checksums in `scripts/seed_database.py`.
   - During the backward-compatible migration-history upgrade, safely backfill checksums for previously applied migration files using their current SHA-256 values.
   - Do not overwrite any existing non-NULL checksum.
   - If an applied migration file is missing, fail clearly rather than silently accepting it.
   - Add tests proving legacy backfill works and subsequent migration-file modification is rejected.
   - Preserve transactional migration execution.

Timebox: 120 minutes.

Strict TDD:
- Demonstrate RED first.
- Implement the smallest safe fixes.
- Demonstrate GREEN on focused tests.
- Run the full pytest test suite (0 failures, 0 skips, 0 warnings).
- Run `pip check` and `git diff --check`.
- Save this exact prompt and concise RED/GREEN execution results in `prompts/phase-7/` using the next sequential filename.
- Do not commit or push.

---

## Execution Record

### 1. Root Cause Analysis

1. **Vacuous Chunk Rollback Assertion**:
   - `PolicyChunk.id` is generated as `CHK-<doc_id_hex>-<index>` using random UUID prefixes (e.g. `DOC-A1B2C3D4`), not literal `"DOC2"`.
   - The test was previously checking `session.query(PolicyChunk).filter(PolicyChunk.id.like("%DOC2%")).all() == []`, which vacuously evaluated to `True` regardless of rollback because `"DOC2"` never appeared in UUID-based identifiers.
   - *Fix*: Captured the actual `captured_failed_doc_id` inside the monkeypatched error hook and asserted against `PolicyChunk.document_id == captured_failed_doc_id`, as well as asserting that all persisted chunks belong strictly to `doc1` and `doc3`.

2. **Legacy NULL Migration Checksums**:
   - Backward-compatible schema upgrades added the `checksum` column to legacy `migration_history` tables but left existing rows with `checksum = NULL`.
   - Previously, `apply_migrations` checked `if recorded_checksum is not None and recorded_checksum != current_checksum:`, which skipped validation if `recorded_checksum` was `None`, allowing post-migration modifications or missing files to go undetected.
   - *Fix*: Added `backfill_legacy_checksums()` to verify the presence of every recorded migration file, compute its current SHA-256 checksum, and update the legacy record transactionally. In dry-run mode, verified all recorded migrations against disk.

---

### 2. RED Phase

#### Legacy Migration Integrity Tests
Added tests to `tests/test_seed_database.py`:
- `test_migration_history_backward_compatibility_schema_upgrade`: Asserted legacy row `000` has its checksum backfilled to match disk.
- `test_legacy_migration_modification_rejected_after_backfill`: Verifies tampering with legacy migration file after backfill raises `MigrationIntegrityError`.
- `test_legacy_migration_missing_file_fails_clearly`: Verifies missing legacy migration file raises `MigrationIntegrityError`.

Execution:
```text
pytest tests/test_seed_database.py -k "legacy" -v

FAILED tests/test_seed_database.py::test_legacy_migration_modification_rejected_after_backfill - Failed: DID NOT RAISE <class 'scripts.seed_database.MigrationIntegrityError'>
FAILED tests/test_seed_database.py::test_legacy_migration_missing_file_fails_clearly - Failed: DID NOT RAISE <class 'scripts.seed_database.MigrationIntegrityError'>
2 failed, 19 deselected in 0.40s
```

---

### 3. Implementation (Smallest Safe Changes)

1. **`tests/test_ingest_policies.py`**:
   - Captured `captured_failed_doc_id = document.id` in `faulty_store`.
   - Proved `Policy One` and `Policy Three` were committed with their actual IDs.
   - Proved `Policy Two` (`captured_failed_doc_id`) is not in `PolicyDocument`.
   - Proved `PolicyChunk` contains zero chunks referencing `captured_failed_doc_id` and all existing chunks belong to `doc1` or `doc3`.

2. **`scripts/seed_database.py`**:
   - Implemented `backfill_legacy_checksums(raw_conn, dialect_name: str, migrations_dir: Path) -> None`:
     - Queries `SELECT filename FROM migration_history WHERE checksum IS NULL`.
     - Validates `file_path.is_file()`; raises `MigrationIntegrityError` if missing.
     - Computes SHA-256 checksum and executes parameterized `UPDATE migration_history SET checksum = ? WHERE filename = ? AND checksum IS NULL`.
     - Commits transaction via `raw_conn.commit()`.
   - Updated `ensure_migration_history_table()` to accept `migrations_dir: Optional[Path] = None` and invoke `backfill_legacy_checksums` when provided.
   - Updated `apply_migrations()`:
     - In dry-run mode, safely checks table schema and validates existence and checksum of all recorded migrations.
     - In execution mode, calls `ensure_migration_history_table(..., migrations_dir=migrations_dir)` and validates all recorded migrations before applying pending ones.

---

### 4. GREEN Phase

#### Focused Legacy Tests
```text
pytest tests/test_seed_database.py -k "legacy" -v
2 passed, 19 deselected in 0.42s
```

#### Focused Upgrade Tests
```text
pytest tests/test_seed_database.py -k "upgrade" -v
1 passed, 20 deselected in 0.32s
```

#### Focused Seed and Ingestion Test Suites (35 tests)
```text
pytest tests/test_seed_database.py tests/test_ingest_policies.py -v
============================= 35 passed in 5.87s ==============================
```

#### Full Test Suite (505 tests)
```text
pytest -v
============================ 505 passed in 27.32s =============================
```
- **0 failed**
- **0 skipped**
- **0 warnings**

---

### 5. Final Quality Verifications

1. **Package Requirements Integrity**:
   ```powershell
   .\.venv\Scripts\python.exe -m pip check
   No broken requirements found.
   ```

2. **Git Diff & Whitespace Integrity**:
   ```powershell
   git diff --check
   (clean, exit code 0)
   ```

3. **Git Worktree Status**:
   - Changes preserved uncommitted in working directory.
   - Baseline commit: `f322e8c`.
   - No commits or pushes made.

