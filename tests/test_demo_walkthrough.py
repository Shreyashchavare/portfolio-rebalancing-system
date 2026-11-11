"""Tests for the reviewer demonstration walkthrough script."""

from datetime import date
from pathlib import Path
import pytest
from sqlalchemy import create_engine

from scripts.demo_walkthrough import run_walkthrough
from scripts.seed_database import apply_migrations, seed_dataset


@pytest.fixture
def temp_db_url(tmp_path: Path) -> str:
    """Fixture providing a temporary SQLite database URL."""
    db_file = tmp_path / "test_demo_run.db"
    return f"sqlite:///{db_file}"


def test_demo_walkthrough_end_to_end_success(temp_db_url: str):
    """Verify that run_walkthrough executes all 9 stages and returns 0."""
    exit_code = run_walkthrough(
        database_url=temp_db_url,
        portfolio_id="PORT-INV-000001-02",
        as_of=date(2026, 1, 15),
    )
    assert exit_code == 0


def test_demo_walkthrough_repeat_execution_is_idempotent_and_safe(temp_db_url: str):
    """Verify that running the demo walkthrough multiple times on the same database succeeds safely."""
    # First execution initializes and seeds
    exit_code_1 = run_walkthrough(
        database_url=temp_db_url,
        portfolio_id="PORT-INV-000001-02",
        as_of=date(2026, 1, 15),
    )
    assert exit_code_1 == 0

    # Repeat execution detects existing state and runs cleanly
    exit_code_2 = run_walkthrough(
        database_url=temp_db_url,
        portfolio_id="PORT-INV-000001-02",
        as_of=date(2026, 1, 15),
    )
    assert exit_code_2 == 0

