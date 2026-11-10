"""Tests for SQLAlchemy Portfolio entity.

Following Test-Driven Development (TDD), these tests define the specifications
and contracts for the Portfolio model before implementation.
"""

from datetime import datetime
import pytest
from sqlalchemy import String, create_engine, event, select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.investor_profile import InvestorProfile, RiskCategory


def _import_portfolio():
    """Dynamically import Portfolio model."""
    try:
        from app.models.portfolio import Portfolio
        return Portfolio
    except (ImportError, ModuleNotFoundError):
        from app.models import Portfolio
        return Portfolio


def _create_sqlite_engine():
    """Create an in-memory SQLite engine with foreign key enforcement enabled."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


# ==============================================================================
# Model Definition & Metadata Tests
# ==============================================================================


def test_portfolio_inherits_from_base():
    """Verify Portfolio inherits from the shared declarative Base."""
    Portfolio = _import_portfolio()
    assert issubclass(Portfolio, Base), (
        "Portfolio must inherit from app.models.base.Base"
    )


def test_table_name_is_portfolio():
    """Verify table name is exactly 'portfolio'."""
    Portfolio = _import_portfolio()
    assert Portfolio.__tablename__ == "portfolio"


def test_portfolio_id_is_primary_key_varchar_40():
    """Verify portfolio_id is VARCHAR(40) and the primary key."""
    Portfolio = _import_portfolio()
    col = Portfolio.__table__.c.portfolio_id

    assert col.primary_key is True, "portfolio_id must be the primary key"
    assert isinstance(col.type, String), "portfolio_id must be a String/VARCHAR type"
    assert col.type.length == 40, "portfolio_id must be VARCHAR(40)"
    assert col.nullable is False, "Primary key portfolio_id must not be nullable"


def test_investor_id_is_foreign_key_varchar_20():
    """Verify investor_id is a required VARCHAR(20) referencing investor_profile.investor_id."""
    Portfolio = _import_portfolio()
    col = Portfolio.__table__.c.investor_id

    assert col.nullable is False, "investor_id must not be nullable"
    assert isinstance(col.type, String), "investor_id must be a String/VARCHAR type"
    assert col.type.length == 20, "investor_id must be VARCHAR(20)"

    fk_targets = {fk.target_fullname for fk in col.foreign_keys}
    assert "investor_profile.investor_id" in fk_targets, (
        "investor_id must have a foreign key to investor_profile.investor_id"
    )


def test_required_columns_and_types():
    """Verify portfolio_name and base_currency are required string fields."""
    Portfolio = _import_portfolio()
    table = Portfolio.__table__

    # portfolio_name: required string
    name_col = table.c.portfolio_name
    assert isinstance(name_col.type, String), "portfolio_name must be a String type"
    assert name_col.nullable is False, "portfolio_name is a required field"

    # base_currency: required string
    currency_col = table.c.base_currency
    assert isinstance(currency_col.type, String), "base_currency must be a String type"
    assert currency_col.nullable is False, "base_currency is a required field"


def test_status_constraint():
    """Verify status accepts only 'ACTIVE' and 'INACTIVE'."""
    Portfolio = _import_portfolio()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            # Create prerequisite investor
            investor = InvestorProfile(
                investor_id="INV-STATUS-TEST",
                name="Status Tester",
                risk_category=RiskCategory.MODERATE,
            )
            session.add(investor)
            session.commit()

            # Valid statuses must succeed
            for idx, valid_status in enumerate(["ACTIVE", "INACTIVE"]):
                port = Portfolio(
                    portfolio_id=f"PORT-VAL-{idx}",
                    investor_id="INV-STATUS-TEST",
                    portfolio_name=f"Portfolio {valid_status}",
                    base_currency="USD",
                    status=valid_status,
                )
                session.add(port)
            session.commit()

            # Invalid status must be rejected
            with pytest.raises((IntegrityError, StatementError, ValueError)):
                invalid_port = Portfolio(
                    portfolio_id="PORT-INVALID-STATUS",
                    investor_id="INV-STATUS-TEST",
                    portfolio_name="Invalid Portfolio",
                    base_currency="USD",
                    status="PENDING",
                )
                session.add(invalid_port)
                session.commit()
    finally:
        engine.dispose()


def test_created_at_has_timestamp_default():
    """Verify created_at has a timestamp default configured."""
    Portfolio = _import_portfolio()
    created_col = Portfolio.__table__.c.created_at

    has_default = (created_col.default is not None) or (
        created_col.server_default is not None
    )
    assert has_default, "created_at must have a default or server_default timestamp"


def test_model_registered_in_metadata():
    """Verify portfolio table is registered in Base.metadata."""
    _import_portfolio()
    assert "portfolio" in Base.metadata.tables, (
        "'portfolio' table must be registered in Base.metadata"
    )


# ==============================================================================
# SQLite In-Memory CRUD & Relationship Tests
# ==============================================================================


def test_insert_and_retrieve_portfolio_sqlite():
    """Verify a valid portfolio can be inserted and retrieved with SQLite."""
    Portfolio = _import_portfolio()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            # Create parent investor
            investor = InvestorProfile(
                investor_id="INV-001",
                name="Jane Doe",
                risk_category=RiskCategory.HIGH,
            )
            session.add(investor)
            session.commit()

            # Create portfolio
            new_port = Portfolio(
                portfolio_id="PORT-001",
                investor_id="INV-001",
                portfolio_name="Growth Portfolio",
                base_currency="USD",
                status="ACTIVE",
            )
            session.add(new_port)
            session.commit()

            # Retrieve and verify
            retrieved = session.scalar(
                select(Portfolio).where(Portfolio.portfolio_id == "PORT-001")
            )
            assert retrieved is not None, "Failed to retrieve inserted Portfolio"
            assert retrieved.portfolio_id == "PORT-001"
            assert retrieved.investor_id == "INV-001"
            assert retrieved.portfolio_name == "Growth Portfolio"
            assert retrieved.base_currency == "USD"
            assert (
                retrieved.status == "ACTIVE"
                or getattr(retrieved.status, "value", None) == "ACTIVE"
            )
            assert retrieved.created_at is not None
            assert isinstance(retrieved.created_at, datetime)
    finally:
        engine.dispose()


def test_portfolio_cannot_reference_nonexistent_investor():
    """Verify that a portfolio cannot reference a nonexistent investor (foreign key check)."""
    Portfolio = _import_portfolio()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            port = Portfolio(
                portfolio_id="PORT-ORPHAN",
                investor_id="NONEXISTENT-INV",
                portfolio_name="Orphan Portfolio",
                base_currency="USD",
                status="ACTIVE",
            )
            session.add(port)
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()


def test_portfolio_relationship_to_investor_profile():
    """Verify relationship navigation between Portfolio and InvestorProfile."""
    Portfolio = _import_portfolio()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            investor = InvestorProfile(
                investor_id="INV-REL-01",
                name="Robert Johnson",
                risk_category=RiskCategory.LOW,
            )
            session.add(investor)
            session.commit()

            port = Portfolio(
                portfolio_id="PORT-REL-01",
                investor_id="INV-REL-01",
                portfolio_name="Conservative Core",
                base_currency="USD",
                status="ACTIVE",
            )
            session.add(port)
            session.commit()

            # Refresh and inspect relationship
            loaded_port = session.scalar(
                select(Portfolio).where(Portfolio.portfolio_id == "PORT-REL-01")
            )
            rel_investor = getattr(loaded_port, "investor", None) or getattr(
                loaded_port, "investor_profile", None
            )
            assert rel_investor is not None, (
                "Portfolio must define a relationship to InvestorProfile (e.g. .investor or .investor_profile)"
            )
            assert rel_investor.investor_id == "INV-REL-01"
            assert rel_investor.name == "Robert Johnson"
    finally:
        engine.dispose()

