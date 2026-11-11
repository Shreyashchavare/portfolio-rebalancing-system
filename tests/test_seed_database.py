"""Tests for database initialization, migration, and starter dataset seeding automation."""

from pathlib import Path
import subprocess
import sys
import pytest
from sqlalchemy import create_engine, inspect

from scripts.seed_database import (
    apply_migrations,
    get_migration_files,
    inspect_database_state,
    main,
    seed_dataset,
    validate_connectivity,
)


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Return path to a fresh SQLite database file for isolated testing."""
    return tmp_path / "test_seed.db"


@pytest.fixture
def temp_db_url(temp_db_path: Path) -> str:
    """Return SQLite connection URL for isolated testing."""
    return f"sqlite:///{temp_db_path.as_posix()}"


def test_cli_help():
    """Verify scripts/seed_database.py exposes standard CLI help flag."""
    cmd = [sys.executable, "scripts/seed_database.py", "--help"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Database initialization and seeding" in result.stdout
    assert "--dry-run" in result.stdout
    assert "--skip-migrations" in result.stdout
    assert "--skip-seed" in result.stdout
    assert "--force" in result.stdout
    assert "Bypass populated-database safeguard only" in result.stdout


def test_validate_connectivity_success(temp_db_url: str):
    """Verify connectivity check succeeds on a valid database."""
    engine = create_engine(temp_db_url)
    assert validate_connectivity(engine) is True
    engine.dispose()


def test_validate_connectivity_failure():
    """Verify connectivity check returns False on an invalid/unreachable database."""
    engine = create_engine("postgresql+psycopg2://invalid_user:invalid_pass@127.0.0.1:59999/nonexistent_db")
    assert validate_connectivity(engine) is False
    engine.dispose()


def test_get_migration_files_order():
    """Verify migration files are discovered in strict alphabetical sequence 000-003."""
    migrations_dir = Path("docs/migrations")
    files = get_migration_files(migrations_dir)
    assert len(files) == 4
    filenames = [f.name for f in files]
    assert filenames[0].startswith("000_")
    assert filenames[1].startswith("001_")
    assert filenames[2].startswith("002_")
    assert filenames[3].startswith("003_")


def test_apply_migrations_creates_all_tables(temp_db_url: str):
    """Verify apply_migrations creates all 15 tables in sequence."""
    engine = create_engine(temp_db_url)
    migrations_dir = Path("docs/migrations")

    applied = apply_migrations(engine, migrations_dir)
    assert len(applied) == 4

    insp = inspect(engine)
    table_names = insp.get_table_names()
    assert "investor_profile" in table_names
    assert "portfolio" in table_names
    assert "instrument" in table_names
    assert "holding" in table_names
    assert "market_price" in table_names
    assert "target_allocation" in table_names
    assert "fee_schedule" in table_names
    assert "constraint" in table_names
    assert "constraint_instrument" in table_names
    assert "rebalance_proposal" in table_names
    assert "trade" in table_names
    assert "policy_documents" in table_names
    assert "policy_chunks" in table_names
    assert "workflow_runs" in table_names
    assert "audit_events" in table_names
    engine.dispose()


def test_dry_run_mode_does_not_modify_database(temp_db_url: str, temp_db_path: Path):
    """Verify dry-run mode validates without creating tables or inserting data."""
    exit_code = main([
        "--database-url", temp_db_url,
        "--dry-run",
    ])
    assert exit_code == 0

    engine = create_engine(temp_db_url)
    insp = inspect(engine)
    assert len(insp.get_table_names()) == 0
    engine.dispose()


def test_seed_starter_dataset_populates_core_tables(temp_db_url: str):
    """Verify seeding starter dataset populates the 11 core tables matching metadata."""
    engine = create_engine(temp_db_url)
    migrations_dir = Path("docs/migrations")
    dataset_dir = Path("data/starter")

    apply_migrations(engine, migrations_dir)
    inserted_counts = seed_dataset(engine, dataset_dir)

    assert inserted_counts["investor_profile"] == 5
    assert inserted_counts["portfolio"] == 10
    assert inserted_counts["instrument"] == 20
    assert inserted_counts["market_price"] == 600
    assert inserted_counts["target_allocation"] == 40
    assert inserted_counts["holding"] == 53
    assert inserted_counts["fee_schedule"] == 30
    assert inserted_counts["constraint"] == 28
    assert inserted_counts["constraint_instrument"] == 3
    assert inserted_counts["rebalance_proposal"] == 10
    assert inserted_counts["trade"] == 20

    # Verify counts directly via SQL
    state = inspect_database_state(engine)
    assert state["investor_profile"] == 5
    assert state["portfolio"] == 10
    assert state["instrument"] == 20
    engine.dispose()


def test_prevent_duplicate_seeding_on_populated_database(temp_db_url: str):
    """Verify seeding halts safely without --force if database already contains records."""
    engine = create_engine(temp_db_url)
    migrations_dir = Path("docs/migrations")
    dataset_dir = Path("data/starter")

    apply_migrations(engine, migrations_dir)
    seed_dataset(engine, dataset_dir)

    # Attempt second seed run without --force; must raise ValueError and not duplicate records
    with pytest.raises(ValueError, match="already contains data"):
        seed_dataset(engine, dataset_dir, force=False)

    # Counts must remain unchanged
    state = inspect_database_state(engine)
    assert state["investor_profile"] == 5
    engine.dispose()


def test_repeated_migrations_are_idempotent(temp_db_url: str):
    """Verify applying migrations repeatedly skips already-applied migrations."""
    engine = create_engine(temp_db_url)
    migrations_dir = Path("docs/migrations")

    applied1 = apply_migrations(engine, migrations_dir)
    assert len(applied1) == 4

    # Repeated execution must discover that all 4 are recorded and apply 0
    applied2 = apply_migrations(engine, migrations_dir)
    assert len(applied2) == 0
    engine.dispose()


def test_migration_history_table_created_and_recorded(temp_db_url: str):
    """Verify migration_history table records filenames and timestamps after execution."""
    from sqlalchemy import text
    engine = create_engine(temp_db_url)
    migrations_dir = Path("docs/migrations")

    applied = apply_migrations(engine, migrations_dir)
    assert len(applied) == 4

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT filename, applied_at FROM migration_history ORDER BY filename")).fetchall()
        assert len(rows) == 4
        recorded_filenames = [r[0] for r in rows]
        assert recorded_filenames == [
            "000_create_core_tables.sql",
            "001_create_policy_rag_tables.sql",
            "002_add_policy_family_id.sql",
            "003_add_orchestration_and_audit_tables.sql",
        ]
        # Timestamps must not be None
        for r in rows:
            assert r[1] is not None
    engine.dispose()


def test_migration_history_applies_newly_added_migration(temp_db_url: str, tmp_path: Path):
    """Verify only newly added migrations are executed when earlier migrations are already recorded."""
    import shutil
    from sqlalchemy import inspect
    # Copy existing migrations to a temp directory
    temp_migrations_dir = tmp_path / "migrations"
    temp_migrations_dir.mkdir()
    for f in Path("docs/migrations").glob("*.sql"):
        shutil.copy(f, temp_migrations_dir / f.name)

    engine = create_engine(temp_db_url)
    applied_first = apply_migrations(engine, temp_migrations_dir)
    assert len(applied_first) == 4

    # Add a 5th migration
    new_mig = temp_migrations_dir / "004_test_extra_table.sql"
    new_mig.write_text(
        "CREATE TABLE IF NOT EXISTS test_extra_table (\n"
        "    id INTEGER PRIMARY KEY,\n"
        "    note TEXT\n"
        ");\n",
        encoding="utf-8",
    )

    # Re-apply migrations; only the newly added migration must be applied
    applied_second = apply_migrations(engine, temp_migrations_dir)
    assert applied_second == ["004_test_extra_table.sql"]

    # Table must now exist
    insp = inspect(engine)
    assert "test_extra_table" in insp.get_table_names()
    engine.dispose()


def test_migration_history_does_not_record_failed_migration(temp_db_url: str, tmp_path: Path):
    """Verify that a failed migration rolls back and is NOT marked as applied in migration_history."""
    from sqlalchemy import text
    import shutil
    temp_migrations_dir = tmp_path / "broken_migrations"
    temp_migrations_dir.mkdir()
    for f in Path("docs/migrations").glob("*.sql"):
        shutil.copy(f, temp_migrations_dir / f.name)

    engine = create_engine(temp_db_url)
    apply_migrations(engine, temp_migrations_dir)

    # Add a failing migration with invalid SQL
    bad_mig = temp_migrations_dir / "004_syntax_error.sql"
    bad_mig.write_text("THIS IS INVALID SQL DDL SYNTAX;\n", encoding="utf-8")

    with pytest.raises(Exception):
        apply_migrations(engine, temp_migrations_dir)

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT filename FROM migration_history WHERE filename = '004_syntax_error.sql'")).fetchall()
        assert len(rows) == 0, "Failed migration must NOT be recorded in migration_history!"
    engine.dispose()


def test_migration_history_records_checksum(temp_db_url: str):
    """Verify migration_history stores SHA-256 checksum for every applied migration."""
    from sqlalchemy import text
    engine = create_engine(temp_db_url)
    migrations_dir = Path("docs/migrations")

    applied = apply_migrations(engine, migrations_dir)
    assert len(applied) == 4

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT filename, checksum FROM migration_history ORDER BY filename")).fetchall()
        assert len(rows) == 4
        for filename, checksum in rows:
            assert checksum is not None, f"Checksum missing for {filename}"
            assert len(checksum) == 64, f"Invalid SHA-256 length for {filename}: {checksum}"
            # Checksum must be valid hexadecimal
            int(checksum, 16)
    engine.dispose()


def test_migration_history_detects_checksum_mismatch(temp_db_url: str, tmp_path: Path):
    """Verify modifying an already-applied migration raises a checksum mismatch error and does not silently skip."""
    import shutil
    temp_migrations_dir = tmp_path / "mod_migrations"
    temp_migrations_dir.mkdir()
    for f in Path("docs/migrations").glob("*.sql"):
        shutil.copy(f, temp_migrations_dir / f.name)

    engine = create_engine(temp_db_url)
    apply_migrations(engine, temp_migrations_dir)

    # Tamper with an already-applied migration file
    target_mig = temp_migrations_dir / "001_create_policy_rag_tables.sql"
    with open(target_mig, "a", encoding="utf-8") as f:
        f.write("\n-- Tampered comment modifying file content\n")

    # Repeat run MUST fail with integrity error or checksum mismatch
    with pytest.raises(Exception) as exc_info:
        apply_migrations(engine, temp_migrations_dir)

    err_msg = str(exc_info.value).lower()
    assert any(term in err_msg for term in ("checksum mismatch", "integrity", "tampered", "modified"))
    engine.dispose()


def test_migration_history_backward_compatibility_schema_upgrade(temp_db_url: str):
    """Verify legacy migration_history tables without checksum column are upgraded safely and backfilled."""
    from sqlalchemy import text
    from scripts.seed_database import compute_migration_checksum
    engine = create_engine(temp_db_url)

    # Simulate legacy migration_history table created before checksum support
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE migration_history ("
            "    filename TEXT PRIMARY KEY,"
            "    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
            ");"
        ))
        # Simulate an existing applied record without checksum
        conn.execute(text("INSERT INTO migration_history (filename) VALUES ('000_create_core_tables.sql');"))

    migrations_dir = Path("docs/migrations")
    # Must upgrade schema cleanly, backfill legacy checksum, and apply remaining migrations (001, 002, 003)
    applied = apply_migrations(engine, migrations_dir)
    assert "001_create_policy_rag_tables.sql" in applied
    assert "000_create_core_tables.sql" not in applied

    # Verify checksum column was added and new migration has checksum
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT filename, checksum FROM migration_history WHERE filename = '001_create_policy_rag_tables.sql'")).fetchall()
        assert len(rows) == 1
        assert rows[0][1] is not None
        assert len(rows[0][1]) == 64

        # Verify legacy row (000) was safely backfilled with its actual SHA-256 checksum
        row0 = conn.execute(text("SELECT filename, checksum FROM migration_history WHERE filename = '000_create_core_tables.sql'")).fetchone()
        assert row0 is not None
        assert row0[1] is not None
        assert len(row0[1]) == 64
        expected_000_checksum = compute_migration_checksum(migrations_dir / "000_create_core_tables.sql")
        assert row0[1] == expected_000_checksum
    engine.dispose()


def test_legacy_migration_modification_rejected_after_backfill(temp_db_url: str, tmp_path: Path):
    """Verify modifying a legacy migration after backfill is detected and rejected on subsequent runs."""
    import shutil
    from sqlalchemy import text
    from scripts.seed_database import MigrationIntegrityError

    temp_migrations_dir = tmp_path / "legacy_mod_migrations"
    temp_migrations_dir.mkdir()
    for f in Path("docs/migrations").glob("*.sql"):
        shutil.copy(f, temp_migrations_dir / f.name)

    engine = create_engine(temp_db_url)
    # Initialize legacy table with NULL checksum for 000
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE migration_history ("
            "    filename TEXT PRIMARY KEY,"
            "    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
            ");"
        ))
        conn.execute(text("INSERT INTO migration_history (filename) VALUES ('000_create_core_tables.sql');"))

    # Initial run upgrades and backfills 000
    apply_migrations(engine, temp_migrations_dir)

    # Now tamper with 000_create_core_tables.sql
    target_mig = temp_migrations_dir / "000_create_core_tables.sql"
    with open(target_mig, "a", encoding="utf-8") as f:
        f.write("\n-- Tampered legacy content\n")

    # Subsequent run MUST detect checksum mismatch on the backfilled legacy migration
    with pytest.raises(MigrationIntegrityError) as exc_info:
        apply_migrations(engine, temp_migrations_dir)

    assert "already-applied migration '000_create_core_tables.sql' has been modified" in str(exc_info.value)
    engine.dispose()


def test_legacy_migration_missing_file_fails_clearly(temp_db_url: str):
    """Verify a legacy applied migration whose file is missing raises a clear integrity error during backfill."""
    from sqlalchemy import text
    from scripts.seed_database import MigrationIntegrityError

    engine = create_engine(temp_db_url)
    # Initialize legacy table with a nonexistent migration file
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE migration_history ("
            "    filename TEXT PRIMARY KEY,"
            "    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
            ");"
        ))
        conn.execute(text("INSERT INTO migration_history (filename) VALUES ('nonexistent_legacy_999.sql');"))

    migrations_dir = Path("docs/migrations")
    with pytest.raises(MigrationIntegrityError) as exc_info:
        apply_migrations(engine, migrations_dir)

    err_msg = str(exc_info.value).lower()
    assert "missing" in err_msg or "not found" in err_msg
    engine.dispose()


def test_force_flag_bypasses_guard_and_rejects_duplicates(temp_db_url: str):
    """Verify --force bypasses the populated-database guard, but constraints reject duplicate rows safely."""
    engine = create_engine(temp_db_url)
    migrations_dir = Path("docs/migrations")
    dataset_dir = Path("data/starter")

    apply_migrations(engine, migrations_dir)
    seed_dataset(engine, dataset_dir)

    # Initial count verified
    state_before = inspect_database_state(engine)
    assert state_before["investor_profile"] == 5

    # Re-running with force=True bypasses the pre-check, but attempts duplicate insert
    # Database primary key / unique constraint MUST reject duplicate inserts safely
    with pytest.raises(Exception) as exc_info:
        seed_dataset(engine, dataset_dir, force=True)

    # Verify error is constraint-related (e.g. IntegrityError / UNIQUE constraint failed)
    err_msg = str(exc_info.value).lower()
    assert any(term in err_msg for term in ("unique constraint", "integrityerror", "duplicate key", "primary key"))

    # Critical Safety Assertion: Existing data was NOT corrupted or duplicated
    state_after = inspect_database_state(engine)
    assert state_after["investor_profile"] == 5
    assert state_after["portfolio"] == 10
    engine.dispose()


def test_seed_rollback_on_simulated_failure(temp_db_url: str, tmp_path: Path):
    """Verify a failure during seeding triggers an atomic rollback leaving zero partial records."""
    engine = create_engine(temp_db_url)
    migrations_dir = Path("docs/migrations")
    apply_migrations(engine, migrations_dir)

    # Construct a synthetic seed dataset where a syntax or constraint failure occurs on statement 3
    bad_dataset_dir = tmp_path / "broken_starter"
    bad_dataset_dir.mkdir()
    bad_sql_file = bad_dataset_dir / "seed_data.sql"
    bad_sql_file.write_text(
        "INSERT INTO investor_profile (investor_id, name, risk_category, created_at) "
        "VALUES ('INV-TEST-01', 'Test Name', 'MODERATE', '2026-01-01T00:00:00+00:00');\n"
        "INSERT INTO investor_profile (investor_id, name, risk_category, created_at) "
        "VALUES ('INV-TEST-02', 'Test Name 2', 'LOW', '2026-01-01T00:00:00+00:00');\n"
        "-- Intentional failure statement: invalid table and syntax error\n"
        "INSERT INTO nonexistent_table_triggering_rollback (id) VALUES (1);\n",
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        seed_dataset(engine, bad_dataset_dir)

    # Critical Atomicity Assertion: Because statement 3 failed, statement 1 & 2 MUST be rolled back!
    state = inspect_database_state(engine)
    assert state["investor_profile"] == 0
    engine.dispose()


def test_prevent_loading_full_dataset_by_default(temp_db_url: str):
    """Verify attempting to load data/full without --force is rejected by safety guard."""
    engine = create_engine(temp_db_url)
    migrations_dir = Path("docs/migrations")
    full_dataset_dir = Path("data/full")

    apply_migrations(engine, migrations_dir)
    with pytest.raises(ValueError, match="Refusing to load full dataset by default"):
        seed_dataset(engine, full_dataset_dir, force=False)
    engine.dispose()


def test_main_cli_end_to_end(temp_db_url: str):
    """Verify main() CLI execution initializes schema and seeds starter dataset."""
    exit_code = main([
        "--database-url", temp_db_url,
        "--dataset-dir", "data/starter",
        "--migrations-dir", "docs/migrations",
    ])
    assert exit_code == 0

    engine = create_engine(temp_db_url)
    state = inspect_database_state(engine)
    assert state["investor_profile"] == 5
    assert state["portfolio"] == 10
    engine.dispose()
