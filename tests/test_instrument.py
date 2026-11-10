"""Tests for SQLAlchemy Instrument entity.

Following Test-Driven Development (TDD), these tests define the specifications
and contracts for the Instrument model before implementation.
"""

from decimal import Decimal
import pytest
from sqlalchemy import Boolean, Numeric, String, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.base import Base


def _import_instrument():
    """Dynamically import Instrument model."""
    try:
        from app.models.instrument import Instrument
        return Instrument
    except (ImportError, ModuleNotFoundError):
        from app.models import Instrument
        return Instrument


def _create_sqlite_engine():
    """Create an in-memory SQLite engine for testing."""
    return create_engine("sqlite:///:memory:")


# ==============================================================================
# Model Definition & Metadata Tests
# ==============================================================================


def test_instrument_inherits_from_base():
    """Verify Instrument inherits from the shared declarative Base."""
    Instrument = _import_instrument()
    assert issubclass(Instrument, Base), (
        "Instrument must inherit from app.models.base.Base"
    )


def test_table_name_is_instrument():
    """Verify table name is exactly 'instrument'."""
    Instrument = _import_instrument()
    assert Instrument.__tablename__ == "instrument"


def test_instrument_id_is_primary_key_varchar_20():
    """Verify instrument_id is VARCHAR(20) and the primary key."""
    Instrument = _import_instrument()
    col = Instrument.__table__.c.instrument_id

    assert col.primary_key is True, "instrument_id must be the primary key"
    assert isinstance(col.type, String), "instrument_id must be String/VARCHAR"
    assert col.type.length == 20, "instrument_id must be VARCHAR(20)"
    assert col.nullable is False, "Primary key instrument_id must not be nullable"


def test_symbol_is_required_and_unique():
    """Verify symbol is required and marked with a unique constraint."""
    Instrument = _import_instrument()
    table = Instrument.__table__
    col = table.c.symbol

    assert col.nullable is False, "symbol must not be nullable"
    assert isinstance(col.type, String), "symbol must be a String type"

    has_unique = (
        col.unique is True
        or any(col.name in idx.columns.keys() for idx in table.indexes if idx.unique)
        or any(
            col.name in [c.name for c in uc.columns]
            for uc in table.constraints
            if hasattr(uc, "columns") and getattr(uc, "unique", False)
        )
    )
    assert has_unique, "symbol must have a unique constraint or unique index"


def test_required_name_and_asset_class():
    """Verify instrument_name and asset_class are required string fields."""
    Instrument = _import_instrument()
    table = Instrument.__table__

    name_col = table.c.instrument_name
    assert isinstance(name_col.type, String), "instrument_name must be String"
    assert name_col.nullable is False, "instrument_name must not be nullable"

    asset_col = table.c.asset_class
    assert isinstance(asset_col.type, String), "asset_class must be String"
    assert asset_col.nullable is False, "asset_class must not be nullable"


def test_lot_size_is_numeric_and_positive_type():
    """Verify lot_size is configured with Numeric/Decimal type and is non-nullable."""
    Instrument = _import_instrument()
    col = Instrument.__table__.c.lot_size

    assert col.nullable is False, "lot_size must not be nullable"
    assert isinstance(col.type, Numeric), "lot_size must be a Numeric/Decimal type"


def test_lot_size_check_constraint_rejects_non_positive():
    """Verify zero and negative lot sizes are rejected by database CHECK constraint."""
    Instrument = _import_instrument()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            # Positive lot size must succeed
            valid_inst = Instrument(
                instrument_id="INST-POS",
                symbol="VAL1",
                instrument_name="Valid Instrument",
                asset_class="EQUITY",
                lot_size=Decimal("1.0"),
                is_active=True,
            )
            session.add(valid_inst)
            session.commit()

            # Zero lot size must be rejected
            with pytest.raises(IntegrityError):
                zero_inst = Instrument(
                    instrument_id="INST-ZERO",
                    symbol="ZERO1",
                    instrument_name="Zero Lot",
                    asset_class="EQUITY",
                    lot_size=Decimal("0.0"),
                    is_active=True,
                )
                session.add(zero_inst)
                session.commit()
            session.rollback()

            # Negative lot size must be rejected
            with pytest.raises(IntegrityError):
                neg_inst = Instrument(
                    instrument_id="INST-NEG",
                    symbol="NEG1",
                    instrument_name="Negative Lot",
                    asset_class="EQUITY",
                    lot_size=Decimal("-10.0"),
                    is_active=True,
                )
                session.add(neg_inst)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_is_active_is_boolean_with_default():
    """Verify is_active is Boolean with a configured default."""
    Instrument = _import_instrument()
    col = Instrument.__table__.c.is_active

    assert isinstance(col.type, Boolean), "is_active must be a Boolean type"
    has_default = (col.default is not None) or (col.server_default is not None)
    assert has_default, "is_active must have a default value configured"


def test_model_registered_in_metadata():
    """Verify instrument table is registered in Base.metadata."""
    _import_instrument()
    assert "instrument" in Base.metadata.tables, (
        "'instrument' table must be registered in Base.metadata"
    )


# ==============================================================================
# SQLite In-Memory CRUD & Constraint Tests
# ==============================================================================


def test_insert_and_retrieve_instrument_sqlite():
    """Verify a valid instrument can be inserted and retrieved with SQLite."""
    Instrument = _import_instrument()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            inst = Instrument(
                instrument_id="INST-001",
                symbol="AAPL",
                instrument_name="Apple Inc.",
                asset_class="EQUITY",
                lot_size=Decimal("1"),
                is_active=True,
            )
            session.add(inst)
            session.commit()

            retrieved = session.scalar(
                select(Instrument).where(Instrument.instrument_id == "INST-001")
            )
            assert retrieved is not None, "Failed to retrieve inserted Instrument"
            assert retrieved.instrument_id == "INST-001"
            assert retrieved.symbol == "AAPL"
            assert retrieved.instrument_name == "Apple Inc."
            assert retrieved.asset_class == "EQUITY"
            assert retrieved.lot_size == Decimal("1")
            assert retrieved.is_active is True
    finally:
        engine.dispose()


def test_duplicate_symbol_rejected():
    """Verify duplicate symbols are rejected by the unique constraint."""
    Instrument = _import_instrument()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            inst1 = Instrument(
                instrument_id="INST-001",
                symbol="MSFT",
                instrument_name="Microsoft Corp.",
                asset_class="EQUITY",
                lot_size=Decimal("1"),
                is_active=True,
            )
            session.add(inst1)
            session.commit()

            # Duplicate symbol
            inst2 = Instrument(
                instrument_id="INST-002",
                symbol="MSFT",
                instrument_name="Microsoft Duplicate",
                asset_class="EQUITY",
                lot_size=Decimal("10"),
                is_active=True,
            )
            session.add(inst2)
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()

