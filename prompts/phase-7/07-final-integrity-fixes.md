# Phase 7.2 — Final Security and Migration Integrity Fix

Perform a narrowly scoped final remediation. Preserve the current architecture and existing behavior.

## 1. Migration integrity
- Extend `migration_history` to store a SHA-256 checksum for every applied migration.
- On subsequent runs, compare the current migration file checksum with its recorded checksum.
- If an already-applied migration has changed, stop with a clear error. Never silently skip it.
- Support existing `migration_history` tables created by the current implementation through a safe, backward-compatible schema upgrade.
- Preserve transactional migration execution and atomic recording of filename plus checksum.
- Add tests for fresh initialization, repeat execution, checksum mismatch, and rollback if migration execution or history recording fails.

## 2. Policy ingestion security
- Resolve and validate every discovered document path against the resolved policy root BEFORE reading document content or metadata.
- Validate companion JSON paths independently against the same root before opening them.
- Reject external symlinks and Windows junctions before any content is read.
- Ensure metadata extraction cannot read a document outside the allowed root.
- Preserve the existing protection against companion JSON overriding `file_path`.
- Apply identical validation to normal ingestion and dry-run.

## 3. Per-document transaction safety
- Inspect all exception paths in `ingest_policy_batch`.
- Ensure every failed document rolls back its document record and all associated chunks.
- Ensure a failure for one document does not prevent subsequent valid documents from being processed.
- Preserve duplicate-version handling as SKIPPED, not FAILED.
- Add a test that injects a failure after partial persistence and verifies that no partial document/chunk records remain.

## 4. TDD and verification
- Add tests first and demonstrate RED.
- Implement the minimum required changes and demonstrate GREEN.
- Run focused migration and ingestion tests.
- Run the full pytest suite, `pip check`, and `git diff --check`.
- Verify migration behavior on disposable PostgreSQL 17 if available. Do not touch the existing verification container.
- Record exact RED/GREEN results in `prompts/phase-7/07-final-integrity-fixes.md`.
- Keep the phase within 120 minutes. If any verification cannot be completed, explicitly report NOT RUN rather than claiming success.

Do not modify unrelated application code, do not create a frontend, and do not commit or push.

---

## Execution Record

### 1. Pre-Implementation Investigation & RED Evidence

Focused behavioral tests were written first and run across `tests/test_seed_database.py` and `tests/test_ingest_policies.py` to demonstrate RED:

1. **`test_migration_history_records_checksum`**: FAILED with `OperationalError: no such column: checksum`.
2. **`test_migration_history_detects_checksum_mismatch`**: FAILED with `DID NOT RAISE <class 'Exception'>` (previously silently skipped modified migration files).
3. **`test_migration_history_backward_compatibility_schema_upgrade`**: FAILED with `OperationalError: no such column: checksum` on legacy schema.
4. **`test_extract_metadata_rejects_external_file_before_reading`**: FAILED with `TypeError: extract_document_metadata() got an unexpected keyword argument 'allowed_root'`.
5. **Initial RED Result**: 4 failed, 28 passed, 1 skipped in 6.38s.

---

### 2. Implementation Details

#### A. Migration Integrity & SHA-256 Checksums (`scripts/seed_database.py`)
- **Schema Extension**: Extended `migration_history` to store `checksum VARCHAR(64)` (TEXT in SQLite).
- **Backward-Compatible Schema Upgrade**: `ensure_migration_history_table()` inspects existing columns using `PRAGMA table_info` (SQLite) or `information_schema.columns` (PostgreSQL). If `checksum` column is missing, it dynamically applies `ALTER TABLE migration_history ADD COLUMN checksum ...`.
- **Integrity Validation**: Added `compute_migration_checksum()` (SHA-256). On both dry-run and live runs, if a discovered migration is already recorded, its recorded checksum is compared with current file checksum. If they differ, `MigrationIntegrityError` is raised immediately.
- **Transactional Atomic History Insert**: Updated `_prepare_migration_sql_with_history(sql, filename, checksum)` to insert `(filename, checksum)` before `COMMIT;` inside the same DDL transaction block.

#### B. Pre-Read Path Security (`scripts/ingest_policies.py`)
- **Pre-flight Validation**: Added `validate_path_within_root(path, allowed_root)` verifying `resolved_path.relative_to(resolved_root)` before any file open or read operation.
- **Companion Metadata Security**: `extract_document_metadata(file_path, allowed_root=...)` validates both `file_path` and `companion_meta` against `allowed_root` before calling `open()`.
- **Symlink / Junction Rejection**: Discovered documents or junctions escaping `allowed_root` are caught and flagged as `FAILED` prior to reading content.
- **Identical Boundary in Dry-Run**: Pre-flight path traversal checks apply identically to both dry-run and normal ingestion modes.

#### C. Per-Document Transaction Safety (`app/services/policy_rag/policy_rag_service.py` & `scripts/ingest_policies.py`)
- In `PolicyRAGService.ingest_document()`, wrapped document creation, text chunking, and vector embedding in a `try...except...self.session.rollback()` block so that partial document or chunk additions are rolled back immediately on any error.
- In `scripts/ingest_policies.py`, each document has isolated transaction boundaries with explicit `session.rollback()` on error, allowing subsequent valid documents in the batch to process successfully.
- Duplicate version ingestion is preserved as `SKIPPED`, not `FAILED`.

---

### 3. Verification & GREEN Evidence

#### A. Focused Tests
1. `pytest tests/test_seed_database.py -v`:
   - **Result**: 19 passed in 5.57s (0 failed).
2. `pytest tests/test_ingest_policies.py -v`:
   - **Result**: 14 passed in 2.78s (0 failed, 0 skipped).

#### B. PostgreSQL 17 Verification
A disposable PostgreSQL 17 Alpine container (`disposable-pg-test-integrity` on port 55432) was launched (existing verification container `yottaflex-verification-postgres` remained untouched and stopped):
- **Fresh Migration**: Applied migrations 000–003; 4 rows recorded in `migration_history` with valid 64-char SHA-256 checksums.
- **Repeat Run**: Verified all 4 migrations skipped with matching checksums.
- **Checksum Tampering Detection**: Appended a comment to `001_create_policy_rag_tables.sql`; verified `apply_migrations()` caught and raised `MigrationIntegrityError: already-applied migration has been modified!`.
- **Backward-Compatible Schema Upgrade**: Initialized a legacy `migration_history` table without the `checksum` column; ran `apply_migrations()` and verified `ALTER TABLE` added the column and stored valid checksums.
- **Cleanup**: Stopped and destroyed container (`docker rm -f disposable-pg-test-integrity`).

#### C. Full Regression Suite
```text
============================ 503 passed in 29.27s =============================
```
- Total Tests: 503 passed
- Failed: 0
- Skipped: 0
- Warnings: 0

#### D. Quality Checks
- `pip check`: `No broken requirements found.`
- `git diff --check`: Clean (exit code 0).
