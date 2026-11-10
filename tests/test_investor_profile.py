"""Tests for SQLAlchemy Base and InvestorProfile database model.

Following Test-Driven Development (TDD), these tests define the specifications
and contracts for the initial database entity before implementation.
"""

from datetime import datetime
import pytest
from sqlalchemy import String, create_engine, inspect, select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import DeclarativeBase, Session


def _import_base():
    """Dynamically import SQLAlchemy DeclarativeBase."""
    try:
        from app.models.base import Base
        return Base
    except (ImportError, ModuleNotFoundError):
        try:
            from app.database.base import Base
            return Base
        except (ImportError, ModuleNotFoundError):
            from app.models import Base
            return Base


def _import_investor_profile():
    """Dynamically import InvestorProfile model."""
    try:
        from app.models.investor_profile import InvestorProfile
        return InvestorProfile
    except (ImportError, ModuleNotFoundError):
        from app.models import InvestorProfile
        return InvestorProfile


# ==============================================================================
# Model Definition & Metadata Tests
# ==============================================================================


def test_base_exists_and_is_declarative_base():
    """Verify that Base exists and is an instance/subclass of DeclarativeBase."""
    Base = _import_base()
    assert issubclass(Base, DeclarativeBase), (
        "Base must inherit from sqlalchemy.orm.DeclarativeBase"
    )


def test_investor_profile_inherits_from_base():
    """Verify that InvestorProfile inherits from Base."""
    Base = _import_base()
    InvestorProfile = _import_investor_profile()
    assert issubclass(InvestorProfile, Base), (
        "InvestorProfile must inherit from DeclarativeBase Base"
    )


def test_table_name_is_investor_profile():
    """Verify that table name is exactly 'investor_profile'."""
    InvestorProfile = _import_investor_profile()
    assert InvestorProfile.__tablename__ == "investor_profile"


def test_investor_id_is_primary_key_varchar_20():
    """Verify investor_id is VARCHAR(20) and the primary key."""
    InvestorProfile = _import_investor_profile()
    table = InvestorProfile.__table__
    col = table.c.investor_id

    assert col.primary_key is True, "investor_id must be the primary key"
    assert isinstance(col.type, String), "investor_id must be a String/VARCHAR type"
    assert col.type.length == 20, "investor_id must be VARCHAR(20)"
    assert col.nullable is False, "Primary key investor_id must not be nullable"


def test_required_columns_and_types():
    """Verify required fields exist with correct nullability and types."""
    InvestorProfile = _import_investor_profile()
    table = InvestorProfile.__table__

    # Required columns
    expected_columns = {"investor_id", "name", "risk_category", "created_at"}
    actual_columns = set(table.c.keys())
    assert expected_columns.issubset(actual_columns), (
        f"Missing columns: {expected_columns - actual_columns}"
    )

    # name: required string
    name_col = table.c.name
    assert isinstance(name_col.type, String), "name must be a String type"
    assert name_col.nullable is False, "name is a required field (non-nullable)"

    # risk_category: required
    risk_col = table.c.risk_category
    assert risk_col.nullable is False, "risk_category is a required field (non-nullable)"

    # created_at: required timestamp
    created_col = table.c.created_at
    assert created_col.nullable is False or created_col.default is not None, (
        "created_at must be populated with default"
    )


def test_risk_category_constraint():
    """Verify risk_category allows only 'LOW', 'MODERATE', and 'HIGH'."""
    Base = _import_base()
    InvestorProfile = _import_investor_profile()

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            # Valid categories must succeed
            for idx, valid_cat in enumerate(["LOW", "MODERATE", "HIGH"]):
                profile = InvestorProfile(
                    investor_id=f"INV-VAL-{idx}",
                    name=f"Valid Investor {idx}",
                    risk_category=valid_cat,
                )
                session.add(profile)
            session.commit()

            # Invalid category must be rejected
            with pytest.raises((IntegrityError, StatementError, ValueError)):
                invalid_profile = InvestorProfile(
                    investor_id="INV-INVALID",
                    name="Invalid Category User",
                    risk_category="EXTREME",
                )
                session.add(invalid_profile)
                session.commit()
    finally:
        engine.dispose()


def test_created_at_has_timestamp_default():
    """Verify created_at has a timestamp default configured."""
    InvestorProfile = _import_investor_profile()
    created_col = InvestorProfile.__table__.c.created_at

    has_default = (created_col.default is not None) or (
        created_col.server_default is not None
    )
    assert has_default, "created_at must have a default or server_default timestamp"


def test_model_registered_in_metadata():
    """Verify InvestorProfile is registered in Base.metadata."""
    Base = _import_base()
    _import_investor_profile()

    assert "investor_profile" in Base.metadata.tables, (
        "'investor_profile' table must be registered in Base.metadata"
    )


# ==============================================================================
# SQLite In-Memory CRUD Test
# ==============================================================================


def test_insert_and_retrieve_investor_profile_sqlite():
    """Verify a valid InvestorProfile can be inserted and retrieved using SQLite in-memory."""
    Base = _import_base()
    InvestorProfile = _import_investor_profile()

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            new_profile = InvestorProfile(
                investor_id="INV-001",
                name="John Doe",
                risk_category="MODERATE",
            )
            session.add(new_profile)
            session.commit()

            # Retrieve by primary key
            stmt = select(InvestorProfile).where(
                InvestorProfile.investor_id == "INV-001"
            )
            retrieved = session.scalar(stmt)

            assert retrieved is not None, "Failed to retrieve inserted InvestorProfile"
            assert retrieved.investor_id == "INV-001"
            assert retrieved.name == "John Doe"
            assert (
                retrieved.risk_category == "MODERATE"
                or getattr(retrieved.risk_category, "value", None) == "MODERATE"
            )
            assert retrieved.created_at is not None, (
                "created_at timestamp should be automatically populated"
            )
            assert isinstance(retrieved.created_at, datetime)
    finally:
        engine.dispose()

