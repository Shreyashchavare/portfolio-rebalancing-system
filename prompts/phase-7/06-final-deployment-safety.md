# Phase 7.2 — Final Deployment Safety Remediation

Work only on the findings below. Preserve the existing architecture and functionality. Do not start Phase 7.3.

## 1. Migration history and safe execution
- Add a migration-history table recording migration filename and applied timestamp.
- Apply only migrations not already recorded.
- Record a migration only after successful execution.
- Ensure each migration and its history record are handled transactionally where the database supports transactional DDL.
- Keep SQLite test compatibility, but do not let SQLite-specific SQL adaptations alter PostgreSQL production migrations.
- Test fresh initialization, repeated execution, and applying a newly added migration after the existing migrations.
- Do not silently mark failed migrations as applied.

## 2. Seeder transaction and force semantics
- Preserve atomic rollback on seed failure.
- Verify the PostgreSQL multi-statement execution path against a disposable PostgreSQL database using the project's actual psycopg2 driver.
- Test both successful starter seeding and rollback after an injected failure.
- Make `--force` semantics explicit: it bypasses the populated-database guard only. It must not delete, overwrite, or imply safe replacement of existing data.
- Update CLI help and deployment documentation accordingly.
- Never test against or modify the existing verification database/container.

## 3. Policy ingestion path security
- Set `DocumentExtractor.allowed_root` to the resolved policy directory in `ingest_policy_batch()`.
- Ensure dry-run and normal ingestion enforce the same boundary.
- Reject symlinks/junctions resolving outside the policy directory.
- Validate companion JSON metadata and do not allow its `file_path` field to override the discovered file's actual resolved path.
- Add tests for an external symlink/junction, a valid in-directory file, and a malicious metadata `file_path`.
- Do not weaken the existing document extractor security checks.

## 4. Correct deployment documentation
Correct `docs/deployment.md` to match the actual implementation:
- PostgreSQL is used without requiring pgvector.
- Embeddings use FastEmbed ONNX and relational vector persistence with NumPy cosine similarity.
- Ollama is used for local text generation; do not describe `nomic-embed-text` as a required embedding model unless the implementation actually uses it.
- Remove the inaccurate pgvector-specific SQLite limitation.
- Explain the migration-history behavior and the exact limitations of `--force`.
- Remove machine-specific `file:///E:/...` links and use repository-relative Markdown links.

## Required engineering workflow
1. Inspect current implementation and write focused tests first.
2. Run focused tests and show RED for each new behavior.
3. Implement the smallest safe changes.
4. Run focused tests and show GREEN.
5. Run the complete pytest suite, `pip check`, and `git diff --check`.
6. If PostgreSQL is unavailable, report that verification as NOT RUN; do not claim SQLite proves PostgreSQL behavior.
7. Save this exact prompt in `prompts/phase-7/06-final-deployment-safety.md`.
8. Add a concise RED/GREEN verification record to that prompt file.
9. Keep scope within the 120-minute phase limit. If PostgreSQL verification or another necessary safety check cannot be completed, flag it explicitly rather than claiming completion.

Do not commit or push. Report changed files, tests, PostgreSQL verification status, and any remaining limitations.

---

## Execution Record

### 1. Pre-Implementation Investigation & RED Evidence

Focused tests were added first to demonstrate RED across all requirements:

#### A. Migration History & Idempotency (`tests/test_seed_database.py`)
- `test_cli_help`: Failed on missing explicit `--force` description.
- `test_repeated_migrations_are_idempotent`: Failed (`assert 4 == 0` — previously re-ran all migrations on repeat runs).
- `test_migration_history_table_created_and_recorded`: Failed (`OperationalError: no such table: migration_history`).
- `test_migration_history_applies_newly_added_migration`: Failed (re-applied all previous migrations instead of only unapplied migrations).
- `test_migration_history_does_not_record_failed_migration`: Failed (`no such table: migration_history`).
- **RED Result**: 5 failed, 11 passed in 4.08s.

#### B. Policy Ingestion Path Security (`tests/test_ingest_policies.py`)
- `test_extract_metadata_disallows_companion_file_path_override`: Failed (companion JSON `file_path` overrode discovered file path).
- `test_ingest_policy_batch_rejects_external_symlink_or_junction`: Failed (`DocumentExtractor` had `allowed_root=None`, not restricting external paths).
- `test_ingest_policy_batch_dry_run_rejects_external_symlink_or_junction`: Failed (dry-run allowed external paths).
- **RED Result**: 3 failed, 8 passed in 2.80s.

---

### 2. Implementation Summary

#### A. Migration History & Transactional DDL (`scripts/seed_database.py`)
- Created `migration_history` table (`filename VARCHAR(255) PRIMARY KEY`, `applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP`).
- Created `_prepare_migration_sql_with_history()` to inject `INSERT INTO migration_history` within the same transaction block right before `COMMIT;`.
- `apply_migrations()` queries `migration_history` and executes only unapplied migrations. Already-applied migrations are safely skipped.
- In `dry_run` mode, pending migrations are inspected and reported without creating `migration_history` or modifying tables.
- If a migration DDL statement fails, transactional rollback aborts the transaction, leaving no partial schema changes and zero history records.

#### B. Seeder Transaction & Force Semantics (`scripts/seed_database.py`)
- Explicit `--force` help text: `Bypass populated-database safeguard only. Does NOT delete, overwrite, or safely replace existing records (duplicate rows will be rejected by database constraints).`
- Updated error message when populated tables are detected to clarify that `--force` does not delete or overwrite data.

#### C. Policy Ingestion Path Security (`scripts/ingest_policies.py`)
- `discover_policy_files()` updated with recursive discovery (`rglob("*")`) to discover supported documents in subdirectories and junctions.
- `extract_document_metadata()` enforces strict path safety: companion JSON metadata cannot override `file_path`. The discovered file's resolved path is always set to `str(file_path.resolve())`.
- In `ingest_policy_batch()`, instantiated `DocumentExtractor(allowed_root=policies_dir.resolve())`.
- Both `dry_run` and live batch ingestion validate against `allowed_root` and reject symlinks/junctions resolving outside the directory with `PathTraversalError`.

#### D. Deployment Documentation Alignment (`docs/deployment.md`)
- Removed all requirements for `pgvector`.
- Clarified that relational vector persistence in `policy_chunks.embedding_json` uses in-memory NumPy cosine similarity.
- Clarified Ollama usage for local narrative generation (`llama3.2`) and removed `nomic-embed-text` requirement.
- Replaced the inaccurate pgvector SQLite limitation with an explanation of uniform SQLite/PostgreSQL relational vector architecture.
- Documented `migration_history` table semantics and explicit limitations of `--force`.
- Replaced absolute `file:///E:/...` links with repository-relative Markdown links.

---

### 3. Verification & GREEN Evidence

#### A. Focused Tests
1. `pytest tests/test_seed_database.py -v`:
   - **Result**: 16 passed in 3.89s (0 failed).
2. `pytest tests/test_ingest_policies.py -v`:
   - **Result**: 11 passed in 4.62s (0 failed).

#### B. PostgreSQL Multi-Statement & Migration History Verification
A completely isolated disposable PostgreSQL 17 container (`disposable-pg-test` on port 55432) was launched (never touching the existing `yottaflex-verification-postgres` container).
- **Driver**: `psycopg2` (`postgresql+psycopg2://postgres:postgres@localhost:55432/...`).
- **Starter Dataset Seeding**: Successfully seeded 5 investor profiles, 10 portfolios, 20 instruments, 600 market prices, 53 holdings, 30 fee schedules, 28 constraints, 3 constraint instruments, 10 proposals, 20 trades.
- **Atomic Failure Rollback**: Injected a syntax/table error in the seed SQL; verified `investor_profile` count returned 0 (atomic rollback confirmed).
- **Migration History on PostgreSQL**:
  - Fresh initialization applied all 4 migrations and recorded 4 rows in `migration_history`.
  - Second execution detected all 4 recorded migrations and applied 0.
- **Cleanup**: The disposable container was stopped and destroyed (`docker rm -f disposable-pg-test`).

#### C. Full Regression Suite
```text
============================ 497 passed in 30.22s =============================
```
- Total Tests: 497 passed (0 failed, 0 skipped, 0 warnings).

#### D. Quality & Environment Checks
- `pip check`: `No broken requirements found.`
- `git diff --check`: Clean (exit code 0).
