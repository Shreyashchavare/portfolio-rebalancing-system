# Prompt P2-07 — Fix PostgreSQL Reserved-Identifier Quoting in SQL Exporter

**AI Tool:** Antigravity  
**Phase:** 2 — Synthetic Data Foundation  
**Task:** Batch 2.4 — Fix PostgreSQL Reserved-Identifier Quoting in SQL Exporter

## Prompt

# Fix PostgreSQL reserved-identifier quoting in SQL exporter

Repository: `E:\Yottaflex\portfolio-rebalancing-system`

## Confirmed issue

The full SQL export contains:

```sql
INSERT INTO constraint (constraint_id, constraint_name, ...)
```

PostgreSQL rejects this because `constraint` is a reserved keyword.

The SQLAlchemy model table is correctly named `constraint`. PostgreSQL created it successfully through `Base.metadata.create_all()` because SQLAlchemy handles identifier quoting automatically.

The dedicated PostgreSQL verification database is already running:
- Container: `yottaflex-verification-postgres`
- Database: `yottaflex_verification`
- Port: `55432`
- All 11 tables successfully created.

The existing full dataset is already generated:
- 1,270,546 total records
- SQL export: `data/full/sql/seed_data.sql`
- SQL file size: approximately 172.5 MB
- Existing CSV and JSON checksums verified successfully.

## Objective

Fix PostgreSQL identifier quoting in the SQL exporter and repair the existing SQL export without rebuilding the full synthetic dataset.

## Requirements

### 1. Tests first

Inspect `synthetic_data/exporters/dataset_exporter.py` and `tests/test_dataset_exporter.py`.

Add regression tests proving:

- The generated INSERT for the `constraint` table uses a quoted identifier: `INSERT INTO "constraint"`.
- Ordinary table inserts remain valid PostgreSQL.
- Column identifiers are safely quoted if the exporter adopts quoting for all identifiers.
- SQL export remains deterministic.
- Existing export and checksum tests continue passing.

Run targeted tests first and demonstrate RED.

### 2. Production fix

Update the SQL exporter to generate PostgreSQL-safe identifiers.

Prefer a safe identifier-quoting implementation rather than a special-case string replacement for `constraint`.

Requirements:
- Quote table identifiers correctly.
- Quote column identifiers correctly if using a general quoting strategy.
- Escape embedded double quotes in identifiers.
- Preserve all values, column order, SQL literal formatting, and insertion order.
- Do not change model table names or schema definitions.
- Keep SQL output deterministic.

### 3. Repair the existing full SQL export

Do NOT rebuild the 1.27-million-row dataset.

After tests pass:
- Update only the SQL export artifact at `data/full/sql/seed_data.sql` so its table and column identifiers follow the corrected exporter convention.
- Preserve every INSERT row, value, and insertion order.
- Do not modify any CSV or entity JSON file.
- Recalculate the SHA-256 checksum for `sql/seed_data.sql` in `data/full/metadata.json`.
- Verify all other existing metadata checksums still match their files.

Use a streaming or line-by-line transformation if appropriate; do not load the entire SQL file into memory unnecessarily.

### 4. TDD and verification

1. Add tests.
2. Run targeted tests and show RED.
3. Implement the exporter correction.
4. Run targeted tests and show GREEN.
5. Run the full test suite.
6. Verify the repaired SQL contains no unquoted `INSERT INTO constraint` statements.
7. Verify all 2,008 constraint INSERT statements are preserved.
8. Verify SQL checksum matches metadata.
9. Verify all non-SQL entity checksums remain unchanged.
10. Save this prompt and a concise RED/GREEN record in `prompts/phase-2/07-postgresql-sql-identifier-quoting.md`.

### Constraints

- Do not start, stop, delete, or recreate any Docker containers.
- Do not import the SQL file yet.
- Do not modify database models or table names.
- Do not regenerate the full dataset.
- Do not commit or push.
- Preserve all existing data and deterministic behavior.

## Deliverables

Report:
- Files changed.
- Tests added.
- RED and GREEN results.
- Full-suite result.
- Number of constraint INSERT statements preserved.
- Checksum verification.
- Confirmation that CSV and JSON data were not modified.

---

## Actual Results

### RED Phase
- Added regression tests in `tests/test_dataset_exporter.py`:
  - `test_quote_identifier_helper`: Verifies safe ANSI/PostgreSQL identifier quoting and double-quote escaping.
  - `test_sql_export_quotes_table_and_column_identifiers`: Verifies that `INSERT INTO "constraint" (...)` is quoted, ordinary tables (`"portfolio"`, `"investor_profile"`) are quoted, columns are quoted, and no unquoted table names exist in INSERT statements.
- Executed: `pytest tests/test_dataset_exporter.py -v`
- Result: **2 failed, 5 passed**
  - `test_quote_identifier_helper` failed: `assert 'constraint' == '"constraint"'`
  - `test_sql_export_quotes_table_and_column_identifiers` failed: `assert 'INSERT INTO "constraint" (' in sql_content`

### Implementation
1. `synthetic_data/exporters/dataset_exporter.py`:
   - Added `_quote_identifier(name: str) -> str` to safely quote table and column identifiers with double quotes, escaping embedded quotes (`name.replace('"', '""')`).
   - Updated `export_dataset` to wrap all table names (`_quote_identifier(tbl)`) and column names (`[_quote_identifier(col) for col in cols]`) in generated INSERT statements.
2. `data/full/sql/seed_data.sql`:
   - Executed a streaming, line-by-line transform on the 1.27M-row file in 4.02 seconds without regenerating the dataset.
   - Replaced all unquoted table and column identifiers with PostgreSQL-safe quoted identifiers.
   - Preserved all 1,270,541 INSERT records, value strings, and insertion orders.
3. `data/full/metadata.json`:
   - Recalculated SHA-256 checksum for `sql/seed_data.sql`: `5cfb07269bb601185b032767d907c94ce22b6c854e7961563c52d3a7c94080ba`.
   - Verified 100% of non-SQL file checksums match on disk.

### GREEN Phase
- Executed: `pytest tests/test_dataset_exporter.py -v`
- Result: **7 passed in 2.02s**

### Full Suite Verification
- Executed: `pytest -v`
- Result: **248 passed, 1 warning in 3.75s** (100% passing across entire test suite).

### SQL Verification Results
- Unquoted `constraint` statements: 0
- Quoted `"constraint"` statements: 2,008
- Total INSERT statements: 1,270,541
- All non-SQL entity checksums match metadata on disk.

