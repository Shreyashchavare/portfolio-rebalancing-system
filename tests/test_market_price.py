"""Tests for SQLAlchemy MarketPrice entity.

Following Test-Driven Development (TDD), these tests define the specifications
and contracts for the MarketPrice model before implementation.
"""

from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import BigInteger, Date, Numeric, String, UniqueConstraint, create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.instrument import Instrument


def _import_market_price():
    """Dynamically import MarketPrice model."""
    try:
        from app.models.market_price import MarketPrice
        return MarketPrice
    except (ImportError, ModuleNotFoundError):
        from app.models import MarketPrice
        return MarketPrice


def _create_sqlite_engine():
    """Create an in-memory SQLite engine with foreign key enforcement enabled."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def _setup_prerequisite_instrument(session: Session) -> Instrument:
    """Create a prerequisite Instrument record for foreign-key testing."""
    instrument = Instrument(
        instrument_id="INST-MP-01",
        symbol="AAPL",
        instrument_name="Apple Inc.",
        asset_class="EQUITY",
        lot_size=Decimal("1.0"),
        is_active=True,
    )
    session.add(instrument)
    session.commit()
    return instrument


# ==============================================================================
# Model Definition & Metadata Tests
# ==============================================================================


def test_market_price_inherits_from_base():
    """Verify MarketPrice inherits from the shared declarative Base."""
    MarketPrice = _import_market_price()
    assert issubclass(MarketPrice, Base), (
        "MarketPrice must inherit from app.models.base.Base"
    )


def test_table_name_is_market_price():
    """Verify table name is exactly 'market_price'."""
    MarketPrice = _import_market_price()
    assert MarketPrice.__tablename__ == "market_price"


def test_id_is_bigint_primary_key():
    """Verify id is BIGINT identity and the primary key."""
    MarketPrice = _import_market_price()
    col = MarketPrice.__table__.c.id

    assert col.primary_key is True, "id must be the primary key"
    assert isinstance(col.type, BigInteger), "id must be BigInteger type"
    assert col.nullable is False, "Primary key id must not be nullable"


def test_instrument_id_is_foreign_key_varchar_20():
    """Verify instrument_id is a required foreign key referencing instrument.instrument_id."""
    MarketPrice = _import_market_price()
    col = MarketPrice.__table__.c.instrument_id

    assert col.nullable is False, "instrument_id must not be nullable"
    assert isinstance(col.type, String), "instrument_id must be String/VARCHAR"
    assert col.type.length == 20, "instrument_id must be VARCHAR(20)"

    fk_targets = {fk.target_fullname for fk in col.foreign_keys}
    assert "instrument.instrument_id" in fk_targets, (
        "instrument_id must have a foreign key to instrument.instrument_id"
    )


def test_required_fields_and_types():
    """Verify price, price_date, and source are required fields with correct types."""
    MarketPrice = _import_market_price()
    table = MarketPrice.__table__

    price_col = table.c.price
    assert isinstance(price_col.type, Numeric), "price must be Numeric/Decimal type"
    assert price_col.nullable is False, "price must not be nullable"

    date_col = table.c.price_date
    assert isinstance(date_col.type, Date), "price_date must be Date type"
    assert date_col.nullable is False, "price_date must not be nullable"

    source_col = table.c.source
    assert isinstance(source_col.type, String), "source must be String type"
    assert source_col.nullable is False, "source must not be nullable"


def test_price_check_constraint_rejects_non_positive():
    """Verify strictly positive price is enforced by database CHECK constraint."""
    MarketPrice = _import_market_price()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisite_instrument(session)

            # Positive price is allowed
            valid_price = MarketPrice(
                instrument_id="INST-MP-01",
                price=Decimal("150.25"),
                price_date=date(2026, 1, 1),
                source="MANUAL",
            )
            session.add(valid_price)
            session.commit()

            # Zero price must be rejected
            with pytest.raises(IntegrityError):
                zero_price = MarketPrice(
                    instrument_id="INST-MP-01",
                    price=Decimal("0.0"),
                    price_date=date(2026, 1, 2),
                    source="MANUAL",
                )
                session.add(zero_price)
                session.commit()
            session.rollback()

            # Negative price must be rejected
            with pytest.raises(IntegrityError):
                neg_price = MarketPrice(
                    instrument_id="INST-MP-01",
                    price=Decimal("-5.0"),
                    price_date=date(2026, 1, 3),
                    source="MANUAL",
                )
                session.add(neg_price)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_unique_constraint_on_instrument_and_price_date():
    """Verify unique constraint on (instrument_id, price_date)."""
    MarketPrice = _import_market_price()
    table = MarketPrice.__table__

    expected_cols = {"instrument_id", "price_date"}
    has_unique = any(
        set(c.name for c in uc.columns) == expected_cols
        for uc in table.constraints
        if isinstance(uc, UniqueConstraint)
    ) or any(
        set(idx.columns.keys()) == expected_cols
        for idx in table.indexes
        if idx.unique
    )
    assert has_unique, (
        "MarketPrice must have a UniqueConstraint on (instrument_id, price_date)"
    )


def test_model_registered_in_metadata():
    """Verify market_price table is registered in Base.metadata."""
    _import_market_price()
    assert "market_price" in Base.metadata.tables, (
        "'market_price' table must be registered in Base.metadata"
    )


# ==============================================================================
# SQLite In-Memory CRUD & Constraint Tests
# ==============================================================================


def test_valid_insert_and_retrieval_sqlite():
    """Verify valid MarketPrice can be inserted and retrieved with SQLite."""
    MarketPrice = _import_market_price()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisite_instrument(session)

            mp = MarketPrice(
                instrument_id="INST-MP-01",
                price=Decimal("185.50"),
                price_date=date(2026, 3, 10),
                source="BLOOMBERG",
            )
            session.add(mp)
            session.commit()

            retrieved = session.scalar(
                select(MarketPrice).where(
                    MarketPrice.instrument_id == "INST-MP-01",
                    MarketPrice.price_date == date(2026, 3, 10),
                )
            )
            assert retrieved is not None, "Failed to retrieve inserted MarketPrice"
            assert retrieved.id is not None
            assert retrieved.instrument_id == "INST-MP-01"
            assert retrieved.price == Decimal("185.50")
            assert retrieved.price_date == date(2026, 3, 10)
            assert retrieved.source == "BLOOMBERG"
    finally:
        engine.dispose()


def test_invalid_foreign_key_rejected():
    """Verify invalid foreign-key references are rejected."""
    MarketPrice = _import_market_price()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            invalid_mp = MarketPrice(
                instrument_id="NONEXISTENT-INST",
                price=Decimal("100.0"),
                price_date=date(2026, 1, 1),
                source="MANUAL",
            )
            session.add(invalid_mp)
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()


def test_duplicate_price_same_date_rejected():
    """Verify duplicate price for the same instrument and date is rejected."""
    MarketPrice = _import_market_price()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisite_instrument(session)

            p1 = MarketPrice(
                instrument_id="INST-MP-01",
                price=Decimal("180.0"),
                price_date=date(2026, 1, 1),
                source="EXCHANGE_1",
            )
            session.add(p1)
            session.commit()

            p2 = MarketPrice(
                instrument_id="INST-MP-01",
                price=Decimal("182.5"),
                price_date=date(2026, 1, 1),
                source="EXCHANGE_2",
            )
            session.add(p2)
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()

