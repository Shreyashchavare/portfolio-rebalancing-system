"""Database initialization, sequential migration runner, and starter dataset seeding automation."""

import argparse
import hashlib
import logging
import os
from pathlib import Path
import re
import sys

# Ensure repository root is in sys.path when script is executed directly
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from typing import Dict, List, Optional, Sequence
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("seed_database")

CORE_TABLES: Sequence[str] = (
    "investor_profile",
    "portfolio",
    "instrument",
    "holding",
    "market_price",
    "target_allocation",
    "fee_schedule",
    "constraint",
    "constraint_instrument",
    "rebalance_proposal",
    "trade",
    "policy_documents",
    "policy_chunks",
    "workflow_runs",
    "audit_events",
)


def normalize_database_url(url: str) -> str:
    """Normalize database URL scheme for SQLAlchemy 2.x and psycopg2 driver."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def validate_connectivity(engine: Engine, timeout_seconds: float = 5.0) -> bool:
    """Validate database reachability before attempting schema modifications.

    Args:
        engine: SQLAlchemy Engine instance.
        timeout_seconds: Maximum seconds to wait for ping response.

    Returns:
        True if connection succeeded and returned 1, False otherwise.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            return row is not None and row[0] == 1
    except Exception as exc:
        logger.error("Database connectivity check failed: %s", exc)
        return False


def get_migration_files(migrations_dir: Path) -> List[Path]:
    """Discover SQL migration files in strict sequential order.

    Args:
        migrations_dir: Path to directory containing migration SQL files.

    Returns:
        Sorted list of migration Path objects.

    Raises:
        FileNotFoundError: If migrations_dir does not exist or has no .sql files.
    """
    if not migrations_dir.is_dir():
        raise FileNotFoundError(f"Migrations directory '{migrations_dir}' does not exist.")

    files = sorted(migrations_dir.glob("*.sql"), key=lambda p: p.name)
    if not files:
        raise FileNotFoundError(f"No .sql migration files found in '{migrations_dir}'.")

    return files


def _adapt_sql_for_dialect(sql: str, dialect_name: str) -> str:
    """Apply dialect-specific syntax transformations for SQLite test environments.

    PostgreSQL runs the production SQL files untouched.
    """
    if dialect_name == "sqlite":
        # 1. Identity column adaptation
        sql = re.sub(
            r"BIGINT\s+GENERATED\s+BY\s+DEFAULT\s+AS\s+IDENTITY\s+PRIMARY\s+KEY",
            "INTEGER PRIMARY KEY AUTOINCREMENT",
            sql,
            flags=re.IGNORECASE,
        )
        # 2. JSONB adaptation
        sql = re.sub(r"\bJSONB\b", "TEXT", sql, flags=re.IGNORECASE)
        # 3. ALTER TABLE ... ADD COLUMN IF NOT EXISTS -> ADD COLUMN
        sql = re.sub(
            r"ADD\s+COLUMN\s+IF\s+NOT\s+EXISTS",
            "ADD COLUMN",
            sql,
            flags=re.IGNORECASE,
        )
        # 4. Quoting for reserved word 'constraint' in table definition
        sql = re.sub(
            r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+constraint\s+\(",
            'CREATE TABLE IF NOT EXISTS "constraint" (',
            sql,
            flags=re.IGNORECASE,
        )
    return sql


class MigrationIntegrityError(Exception):
    """Raised when an already-applied migration file checksum does not match recorded history."""

    pass


MIGRATION_HISTORY_TABLE = "migration_history"


def compute_migration_checksum(file_path: Path) -> str:
    """Compute SHA-256 hex digest for a migration file."""
    content = file_path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def ensure_migration_history_table(raw_conn, dialect_name: str, migrations_dir: Optional[Path] = None) -> None:
    """Ensure the migration_history table exists and has all required columns.

    Supports backward-compatible schema upgrade for existing tables missing the checksum column.
    If migrations_dir is provided, safely backfills checksums for legacy records.
    """
    cursor = raw_conn.cursor()
    if dialect_name == "sqlite":
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS migration_history (
                filename TEXT PRIMARY KEY,
                checksum TEXT,
                applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Backward-compatible upgrade: verify checksum column exists
        cursor.execute("PRAGMA table_info(migration_history)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        if "checksum" not in existing_cols:
            cursor.execute("ALTER TABLE migration_history ADD COLUMN checksum TEXT")
    else:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS migration_history (
                filename VARCHAR(255) PRIMARY KEY,
                checksum VARCHAR(64),
                applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Backward-compatible upgrade for PostgreSQL
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'migration_history' AND column_name = 'checksum'
            """
        )
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE migration_history ADD COLUMN checksum VARCHAR(64)")
    raw_conn.commit()

    if migrations_dir is not None:
        backfill_legacy_checksums(raw_conn, dialect_name, migrations_dir)


def backfill_legacy_checksums(raw_conn, dialect_name: str, migrations_dir: Path) -> None:
    """Backfill SHA-256 checksums for legacy migration_history records where checksum IS NULL.

    Raises:
        MigrationIntegrityError: If an applied migration file cannot be found in migrations_dir.
    """
    cursor = raw_conn.cursor()
    cursor.execute("SELECT filename FROM migration_history WHERE checksum IS NULL")
    null_rows = [row[0] for row in cursor.fetchall()]
    if not null_rows:
        return

    logger.info("Found %d legacy migration_history records without checksum; backfilling...", len(null_rows))
    param_placeholder = "?" if dialect_name == "sqlite" else "%s"
    for filename in null_rows:
        file_path = migrations_dir / filename
        if not file_path.is_file():
            raise MigrationIntegrityError(
                f"Cannot backfill migration history: recorded migration file '{filename}' was not found in '{migrations_dir}'."
            )
        checksum = compute_migration_checksum(file_path)
        cursor.execute(
            f"UPDATE migration_history SET checksum = {param_placeholder} WHERE filename = {param_placeholder} AND checksum IS NULL",
            (checksum, filename),
        )
    raw_conn.commit()


def get_applied_migrations(raw_conn) -> Dict[str, Optional[str]]:
    """Query mapping of applied migration filenames to their recorded SHA-256 checksums."""
    cursor = raw_conn.cursor()
    cursor.execute("SELECT filename, checksum FROM migration_history")
    return {row[0]: row[1] for row in cursor.fetchall()}


def _prepare_migration_sql_with_history(sql: str, filename: str, checksum: str) -> str:
    """Inject migration_history recording with SHA-256 checksum into the transaction before COMMIT."""
    escaped_filename = filename.replace("'", "''")
    escaped_checksum = checksum.replace("'", "''")
    record_stmt = (
        f"\nINSERT INTO migration_history (filename, checksum) "
        f"VALUES ('{escaped_filename}', '{escaped_checksum}');\n"
    )

    # If the SQL script contains an explicit COMMIT;, insert right before it
    commit_matches = list(re.finditer(r"\bCOMMIT\s*;", sql, flags=re.IGNORECASE))
    if commit_matches:
        last_match = commit_matches[-1]
        start = last_match.start()
        return sql[:start] + record_stmt + sql[start:]

    # If it contains BEGIN;, append record statement and COMMIT;
    if re.search(r"\bBEGIN\s*;", sql, flags=re.IGNORECASE):
        return f"{sql}\n{record_stmt}\nCOMMIT;\n"

    # Otherwise wrap in BEGIN ... COMMIT
    return f"BEGIN;\n{sql}\n{record_stmt}\nCOMMIT;\n"


def apply_migrations(
    engine: Engine,
    migrations_dir: Path,
    dry_run: bool = False,
) -> List[str]:
    """Execute SQL migrations sequentially, applying only unrecorded migrations.

    Records applied migrations and SHA-256 checksums in migration_history transactionally where supported.
    Verifies that already-applied migrations have not been altered.

    Args:
        engine: Connected SQLAlchemy Engine.
        migrations_dir: Path to migration files.
        dry_run: If True, validate file availability and integrity without executing DDL.

    Returns:
        List of newly applied migration file names.

    Raises:
        MigrationIntegrityError: If an already-applied migration file checksum does not match history.
    """
    migration_files = get_migration_files(migrations_dir)
    applied_names: List[str] = []
    dialect_name = engine.dialect.name

    logger.info("Discovered %d migration files in '%s'.", len(migration_files), migrations_dir)

    insp = inspect(engine)
    has_history = MIGRATION_HISTORY_TABLE in insp.get_table_names()

    if dry_run:
        if has_history:
            raw_conn = engine.raw_connection()
            try:
                cursor = raw_conn.cursor()
                if dialect_name == "sqlite":
                    cursor.execute("PRAGMA table_info(migration_history)")
                    has_checksum_col = any(row[1] == "checksum" for row in cursor.fetchall())
                else:
                    cursor.execute(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'migration_history' AND column_name = 'checksum'"
                    )
                    has_checksum_col = cursor.fetchone() is not None

                if has_checksum_col:
                    already_applied = get_applied_migrations(raw_conn)
                else:
                    cursor.execute("SELECT filename FROM migration_history")
                    already_applied = {row[0]: None for row in cursor.fetchall()}
            finally:
                raw_conn.close()
        else:
            already_applied = {}

        # Validate integrity of already-applied migrations in dry-run mode
        for filename, recorded_checksum in already_applied.items():
            target_path = migrations_dir / filename
            if not target_path.is_file():
                raise MigrationIntegrityError(
                    f"Cannot verify migration history: recorded migration file '{filename}' was not found in '{migrations_dir}'."
                )
            current_checksum = compute_migration_checksum(target_path)
            if recorded_checksum is not None and recorded_checksum != current_checksum:
                raise MigrationIntegrityError(
                    f"Migration integrity violation: already-applied migration '{filename}' has been modified! "
                    f"Recorded checksum: '{recorded_checksum}', current file checksum: '{current_checksum}'. "
                    "Applied migrations must remain immutable."
                )

        unapplied = [f for f in migration_files if f.name not in already_applied]
        logger.info("[DRY-RUN] Migrations verified successfully; %d pending.", len(unapplied))
        return [f.name for f in unapplied]

    raw_conn = engine.raw_connection()
    try:
        ensure_migration_history_table(raw_conn, dialect_name, migrations_dir=migrations_dir)
        already_applied = get_applied_migrations(raw_conn)
        cursor = raw_conn.cursor()

        # Validate integrity of already-applied migrations
        for applied_file, recorded_checksum in already_applied.items():
            target_path = migrations_dir / applied_file
            if not target_path.is_file():
                raise MigrationIntegrityError(
                    f"Cannot verify migration history: recorded migration file '{applied_file}' was not found in '{migrations_dir}'."
                )
            current_checksum = compute_migration_checksum(target_path)
            if recorded_checksum is not None and recorded_checksum != current_checksum:
                raise MigrationIntegrityError(
                    f"Migration integrity violation: already-applied migration '{applied_file}' has been modified! "
                    f"Recorded checksum: '{recorded_checksum}', current file checksum: '{current_checksum}'. "
                    "Applied migrations must remain immutable."
                )

        for path in migration_files:
            if path.name in already_applied:
                logger.info("Migration '%s' already recorded with valid checksum; skipping.", path.name)
                continue

            current_checksum = compute_migration_checksum(path)
            logger.info("Applying migration: %s (SHA-256: %s...)", path.name, current_checksum[:12])
            with open(path, "r", encoding="utf-8") as f:
                raw_sql = f.read()

            adapted_sql = _adapt_sql_for_dialect(raw_sql, dialect_name)
            if dialect_name == "sqlite":
                # Check for idempotent column addition in SQLite for migration 002
                if "002" in path.name:
                    cursor.execute("PRAGMA table_info(policy_documents)")
                    existing_cols = {row[1] for row in cursor.fetchall()}
                    if "policy_family_id" in existing_cols:
                        adapted_sql = re.sub(
                            r"ALTER\s+TABLE\s+policy_documents\s+ADD\s+COLUMN[^\;]+\;",
                            "-- Column policy_family_id already exists",
                            adapted_sql,
                            flags=re.IGNORECASE,
                        )

            tx_sql = _prepare_migration_sql_with_history(adapted_sql, path.name, current_checksum)

            if dialect_name == "sqlite":
                cursor.executescript(tx_sql)
                raw_conn.commit()
            else:
                cursor.execute(tx_sql)
                raw_conn.commit()

            applied_names.append(path.name)
            logger.info("Successfully applied and recorded migration: %s", path.name)
    except Exception as exc:
        raw_conn.rollback()
        logger.error("Migration execution failed; rolled back: %s", exc)
        raise
    finally:
        raw_conn.close()

    return applied_names


def inspect_database_state(engine: Engine) -> Dict[str, int]:
    """Inspect current row counts for all recognized system tables.

    Args:
        engine: SQLAlchemy Engine.

    Returns:
        Dict mapping table name to existing row count.
    """
    counts: Dict[str, int] = {}
    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())

    with engine.connect() as conn:
        for tbl in CORE_TABLES:
            if tbl in existing_tables:
                quoted = f'"{tbl}"'
                res = conn.execute(text(f"SELECT COUNT(*) FROM {quoted}"))
                counts[tbl] = res.scalar() or 0
            else:
                counts[tbl] = 0
    return counts


def seed_dataset(
    engine: Engine,
    dataset_dir: Path,
    force: bool = False,
    dry_run: bool = False,
) -> Dict[str, int]:
    """Seed the database using starter dataset SQL statements.

    Safety Rules:
    - Never load the 414 MB full dataset unless explicitly forced.
    - Prevent silent overwrites or duplicate primary key conflicts on populated databases.
    - Quoted identifier normalization for ANSI SQL compatibility.

    Args:
        engine: SQLAlchemy Engine.
        dataset_dir: Directory containing seed data (default: data/starter).
        force: If True, bypass pre-population safeguards.
        dry_run: If True, inspect dataset without modifying database.

    Returns:
        Dict mapping table name to newly inserted row count.

    Raises:
        ValueError: If full dataset is targeted without force, or database already contains data.
        FileNotFoundError: If seed SQL script is missing.
    """
    resolved_dir = dataset_dir.resolve()
    dir_str = str(resolved_dir).lower()

    # Safety Guard 1: Never load full dataset (414 MB) by default
    if "full" in dir_str and not force:
        raise ValueError(
            "Refusing to load full dataset by default (414 MB). Starter dataset is 'data/starter'. "
            "Pass --force to override this safety check."
        )

    # Safety Guard 2: Prevent accidental duplicate seeding on already-populated database
    pre_counts = inspect_database_state(engine)
    populated = {tbl: cnt for tbl, cnt in pre_counts.items() if cnt > 0 and tbl in ("investor_profile", "portfolio", "instrument")}
    if populated and not force:
        details = ", ".join(f"{t}: {c}" for t, c in populated.items())
        raise ValueError(
            f"Database already contains data ({details}). Seeding aborted to prevent duplicates or corruption. "
            "Pass --force to bypass this populated-database safeguard only (note: existing records will not be deleted or overwritten, and duplicate keys will be rejected by database constraints)."
        )

    # Locate seed SQL file
    sql_path = dataset_dir / "sql" / "seed_data.sql"
    if not sql_path.is_file():
        sql_path = dataset_dir / "seed_data.sql"
    if not sql_path.is_file():
        raise FileNotFoundError(f"Seed script 'seed_data.sql' not found in '{dataset_dir}'.")

    if dry_run:
        logger.info("[DRY-RUN] Seed script '%s' validated; skipping execution.", sql_path)
        return {tbl: 0 for tbl in CORE_TABLES}

    dialect_name = engine.dialect.name
    with open(sql_path, "r", encoding="utf-8") as f:
        seed_sql = f.read()

    # ANSI normalization: Ensure "constraint" reserved word is safely quoted
    seed_sql = re.sub(
        r"INSERT\s+INTO\s+constraint\s+\(",
        'INSERT INTO "constraint" (',
        seed_sql,
        flags=re.IGNORECASE,
    )

    # Ensure atomic transaction block
    sql_stripped = seed_sql.strip()
    if not sql_stripped.upper().startswith("BEGIN"):
        tx_sql = f"BEGIN TRANSACTION;\n{seed_sql}\nCOMMIT;\n"
    else:
        tx_sql = seed_sql

    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        if dialect_name == "sqlite":
            cursor.executescript(tx_sql)
            raw_conn.commit()
        else:
            cursor.execute(tx_sql)
            raw_conn.commit()
    except Exception as exc:
        raw_conn.rollback()
        logger.error("Seeding transaction failed; all operations rolled back atomically: %s", exc)
        raise
    finally:
        raw_conn.close()

    post_counts = inspect_database_state(engine)
    inserted = {tbl: post_counts[tbl] - pre_counts.get(tbl, 0) for tbl in CORE_TABLES}
    return inserted


def resolve_database_url(explicit_url: Optional[str] = None) -> str:
    """Resolve database URL from CLI flag, environment variable, or app settings."""
    raw_url: Optional[str] = None
    if explicit_url and explicit_url.strip():
        raw_url = explicit_url.strip()
    elif os.environ.get("DATABASE_URL") and os.environ.get("DATABASE_URL").strip():
        raw_url = os.environ.get("DATABASE_URL").strip()
    else:
        try:
            from app.core.config import get_settings

            raw_url = get_settings().DATABASE_URL
        except Exception as exc:
            raise ValueError(
                "DATABASE_URL is not configured. Provide --database-url or set the DATABASE_URL environment variable."
            ) from exc

    return normalize_database_url(raw_url)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entrypoint for database initialization and seeding."""
    parser = argparse.ArgumentParser(
        description="Database initialization and seeding automation for Portfolio Rebalancing System.",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Explicit database connection URI (overrides DATABASE_URL environment variable).",
    )
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=Path("docs/migrations"),
        help="Path to directory containing migration SQL files (default: docs/migrations).",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("data/starter"),
        help="Path to dataset directory containing seed_data.sql (default: data/starter).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate connectivity, migration files, and dataset without executing modifications.",
    )
    parser.add_argument(
        "--skip-migrations",
        action="store_true",
        help="Skip executing database migrations.",
    )
    parser.add_argument(
        "--skip-seed",
        action="store_true",
        help="Skip seeding dataset records.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass populated-database safeguard only. Does NOT delete, overwrite, or safely replace existing records (duplicate rows will be rejected by database constraints).",
    )

    args = parser.parse_args(argv)

    try:
        db_url = resolve_database_url(args.database_url)
    except Exception as err:
        logger.error("Configuration error: %s", err)
        return 1

    logger.info("Initializing engine for database target: %s", re.sub(r"://([^:]+):[^@]+@", r"://\1:***@", db_url))
    engine = create_engine(db_url)

    # 1. Validate connectivity
    if not validate_connectivity(engine):
        logger.error("Database connectivity check failed. Verify database is running and credentials are valid.")
        engine.dispose()
        return 1

    logger.info("Database connectivity verified successfully.")

    try:
        # 2. Apply migrations in order: 000, 001, 002, 003
        if not args.skip_migrations:
            applied = apply_migrations(engine, args.migrations_dir, dry_run=args.dry_run)
            logger.info("Migrations completed (%d applied).", len(applied))
        else:
            logger.info("Skipping migrations as requested via --skip-migrations.")

        # 3. Seed dataset
        if not args.skip_seed:
            inserted = seed_dataset(engine, args.dataset_dir, force=args.force, dry_run=args.dry_run)
            logger.info("Seeding completed successfully.")
            for tbl, cnt in inserted.items():
                if cnt > 0:
                    logger.info("  %s: +%d rows", tbl, cnt)
        else:
            logger.info("Skipping seeding as requested via --skip-seed.")

        logger.info("Database automation finished successfully.")
        return 0
    except Exception as exc:
        logger.error("Database automation failed: %s", exc)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
