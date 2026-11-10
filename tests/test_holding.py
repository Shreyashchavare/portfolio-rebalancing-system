"""Tests for SQLAlchemy Holding entity.

Following Test-Driven Development (TDD), these tests define the specifications
and contracts for the Holding model before implementation.
"""

from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import Date, Numeric, String, create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.instrument import Instrument
from app.models.investor_profile import InvestorProfile, RiskCategory
from app.models.portfolio import Portfolio, PortfolioStatus


def _import_holding():
    """Dynamically import Holding model."""
    try:
        from app.models.holding import Holding
        return Holding
    except (ImportError, ModuleNotFoundError):
        from app.models import Holding
        return Holding


def _create_sqlite_engine():
    """Create an in-memory SQLite engine with foreign key enforcement enabled."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def _setup_prerequisites(session: Session):
    """Create standard prerequisite records: InvestorProfile, Portfolio, and Instrument."""
    investor = InvestorProfile(
        investor_id="INV-H-01",
        name="Holding Investor",
        risk_category=RiskCategory.MODERATE,
    )
    session.add(investor)
    session.flush()

    portfolio = Portfolio(
        portfolio_id="PORT-H-01",
        investor_id="INV-H-01",
        portfolio_name="Holding Test Portfolio",
        base_currency="USD",
        status=PortfolioStatus.ACTIVE,
    )
    session.add(portfolio)

    instrument = Instrument(
        instrument_id="INST-H-01",
        symbol="AAPL",
        instrument_name="Apple Inc.",
        asset_class="EQUITY",
        lot_size=Decimal("1.0"),
        is_active=True,
    )
    session.add(instrument)
    session.commit()


# ==============================================================================
# Model Definition & Metadata Tests
# ==============================================================================


def test_holding_inherits_from_base():
    """Verify Holding inherits from the shared declarative Base."""
    Holding = _import_holding()
    assert issubclass(Holding, Base), (
        "Holding must inherit from app.models.base.Base"
    )


def test_table_name_is_holding():
    """Verify table name is exactly 'holding'."""
    Holding = _import_holding()
    assert Holding.__tablename__ == "holding"


def test_holding_id_is_primary_key_varchar_100():
    """Verify holding_id is VARCHAR(100) and the primary key."""
    Holding = _import_holding()
    col = Holding.__table__.c.holding_id

    assert col.primary_key is True, "holding_id must be the primary key"
    assert isinstance(col.type, String), "holding_id must be String/VARCHAR"
    assert col.type.length == 100, "holding_id must be VARCHAR(100)"
    assert col.nullable is False, "Primary key holding_id must not be nullable"


def test_portfolio_id_is_foreign_key_varchar_40():
    """Verify portfolio_id is a required foreign key referencing portfolio.portfolio_id."""
    Holding = _import_holding()
    col = Holding.__table__.c.portfolio_id

    assert col.nullable is False, "portfolio_id must not be nullable"
    assert isinstance(col.type, String), "portfolio_id must be String/VARCHAR"
    assert col.type.length == 40, "portfolio_id must be VARCHAR(40)"

    fk_targets = {fk.target_fullname for fk in col.foreign_keys}
    assert "portfolio.portfolio_id" in fk_targets, (
        "portfolio_id must have a foreign key to portfolio.portfolio_id"
    )


def test_instrument_id_is_foreign_key_varchar_20():
    """Verify instrument_id is a required foreign key referencing instrument.instrument_id."""
    Holding = _import_holding()
    col = Holding.__table__.c.instrument_id

    assert col.nullable is False, "instrument_id must not be nullable"
    assert isinstance(col.type, String), "instrument_id must be String/VARCHAR"
    assert col.type.length == 20, "instrument_id must be VARCHAR(20)"

    fk_targets = {fk.target_fullname for fk in col.foreign_keys}
    assert "instrument.instrument_id" in fk_targets, (
        "instrument_id must have a foreign key to instrument.instrument_id"
    )


def test_required_fields_and_types():
    """Verify quantity and as_of_date are required fields with correct types."""
    Holding = _import_holding()
    table = Holding.__table__

    qty_col = table.c.quantity
    assert isinstance(qty_col.type, Numeric), "quantity must be Numeric/Decimal type"
    assert qty_col.nullable is False, "quantity must not be nullable"

    date_col = table.c.as_of_date
    assert isinstance(date_col.type, Date), "as_of_date must be Date type"
    assert date_col.nullable is False, "as_of_date must not be nullable"


def test_quantity_check_constraint_rejects_negative():
    """Verify non-negative quantity is enforced by database CHECK constraint."""
    Holding = _import_holding()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisites(session)

            # Zero quantity is allowed (non-negative)
            zero_holding = Holding(
                holding_id="HOLD-ZERO",
                portfolio_id="PORT-H-01",
                instrument_id="INST-H-01",
                quantity=Decimal("0.0"),
                as_of_date=date(2026, 1, 1),
            )
            session.add(zero_holding)
            session.commit()

            # Positive quantity is allowed
            pos_holding = Holding(
                holding_id="HOLD-POS",
                portfolio_id="PORT-H-01",
                instrument_id="INST-H-01",
                quantity=Decimal("150.5"),
                as_of_date=date(2026, 1, 2),
            )
            session.add(pos_holding)
            session.commit()

            # Negative quantity must be rejected
            with pytest.raises(IntegrityError):
                neg_holding = Holding(
                    holding_id="HOLD-NEG",
                    portfolio_id="PORT-H-01",
                    instrument_id="INST-H-01",
                    quantity=Decimal("-1.0"),
                    as_of_date=date(2026, 1, 3),
                )
                session.add(neg_holding)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_unique_constraint_on_portfolio_instrument_date():
    """Verify unique constraint on (portfolio_id, instrument_id, as_of_date)."""
    Holding = _import_holding()
    table = Holding.__table__

    from sqlalchemy import UniqueConstraint

    expected_cols = {"portfolio_id", "instrument_id", "as_of_date"}
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
        "Holding must have a UniqueConstraint on (portfolio_id, instrument_id, as_of_date)"
    )


def test_model_registered_in_metadata():
    """Verify holding table is registered in Base.metadata."""
    _import_holding()
    assert "holding" in Base.metadata.tables, (
        "'holding' table must be registered in Base.metadata"
    )


# ==============================================================================
# SQLite In-Memory CRUD & Constraint Tests
# ==============================================================================


def test_valid_insert_and_retrieval_sqlite():
    """Verify valid Holding can be inserted and retrieved with SQLite."""
    Holding = _import_holding()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisites(session)

            holding = Holding(
                holding_id="HOLD-PORT-H-01-INST-H-01",
                portfolio_id="PORT-H-01",
                instrument_id="INST-H-01",
                quantity=Decimal("250.75"),
                as_of_date=date(2026, 3, 15),
            )
            session.add(holding)
            session.commit()

            retrieved = session.scalar(
                select(Holding).where(Holding.holding_id == "HOLD-PORT-H-01-INST-H-01")
            )
            assert retrieved is not None, "Failed to retrieve inserted Holding"
            assert retrieved.holding_id == "HOLD-PORT-H-01-INST-H-01"
            assert retrieved.portfolio_id == "PORT-H-01"
            assert retrieved.instrument_id == "INST-H-01"
            assert retrieved.quantity == Decimal("250.75")
            assert retrieved.as_of_date == date(2026, 3, 15)
    finally:
        engine.dispose()


def test_invalid_foreign_keys_rejected():
    """Verify invalid foreign-key references are rejected."""
    Holding = _import_holding()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisites(session)

            # Invalid portfolio_id
            invalid_port = Holding(
                holding_id="HOLD-BAD-PORT",
                portfolio_id="NONEXISTENT-PORT",
                instrument_id="INST-H-01",
                quantity=Decimal("10.0"),
                as_of_date=date(2026, 1, 1),
            )
            session.add(invalid_port)
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            # Invalid instrument_id
            invalid_inst = Holding(
                holding_id="HOLD-BAD-INST",
                portfolio_id="PORT-H-01",
                instrument_id="NONEXISTENT-INST",
                quantity=Decimal("10.0"),
                as_of_date=date(2026, 1, 1),
            )
            session.add(invalid_inst)
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_historical_snapshots_on_different_dates_allowed():
    """Verify multiple historical snapshots for the same portfolio and instrument are allowed."""
    Holding = _import_holding()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisites(session)

            snap1 = Holding(
                holding_id="HOLD-P1-I1-20260101",
                portfolio_id="PORT-H-01",
                instrument_id="INST-H-01",
                quantity=Decimal("100"),
                as_of_date=date(2026, 1, 1),
            )
            snap2 = Holding(
                holding_id="HOLD-P1-I1-20260102",
                portfolio_id="PORT-H-01",
                instrument_id="INST-H-01",
                quantity=Decimal("120"),
                as_of_date=date(2026, 1, 2),
            )
            session.add_all([snap1, snap2])
            session.commit()

            results = session.scalars(
                select(Holding)
                .where(
                    Holding.portfolio_id == "PORT-H-01",
                    Holding.instrument_id == "INST-H-01",
                )
                .order_by(Holding.as_of_date)
            ).all()

            assert len(results) == 2
            assert results[0].as_of_date == date(2026, 1, 1)
            assert results[1].as_of_date == date(2026, 1, 2)
    finally:
        engine.dispose()


def test_duplicate_snapshot_same_date_rejected():
    """Verify duplicate snapshot for the same portfolio, instrument and date is rejected."""
    Holding = _import_holding()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisites(session)

            h1 = Holding(
                holding_id="HOLD-DUP-1",
                portfolio_id="PORT-H-01",
                instrument_id="INST-H-01",
                quantity=Decimal("100"),
                as_of_date=date(2026, 1, 1),
            )
            session.add(h1)
            session.commit()

            h2 = Holding(
                holding_id="HOLD-DUP-2",
                portfolio_id="PORT-H-01",
                instrument_id="INST-H-01",
                quantity=Decimal("150"),
                as_of_date=date(2026, 1, 1),
            )
            session.add(h2)
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()
