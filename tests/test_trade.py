"""Tests for SQLAlchemy Trade entity.

Following Test-Driven Development (TDD), these tests define the specifications
and contracts for the Trade model before implementation.
"""

from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import (
    DateTime,
    Numeric,
    String,
    create_engine,
    event,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.fee_schedule import FeeSchedule
from app.models.instrument import Instrument
from app.models.investor_profile import InvestorProfile, RiskCategory
from app.models.portfolio import Portfolio, PortfolioStatus


def _import_trade_models():
    """Dynamically import Trade and associated enums."""
    try:
        from app.models.trade import Trade, TradeStatus
    except (ImportError, ModuleNotFoundError):
        from app.models import Trade, TradeStatus

    try:
        from app.models.rebalance_proposal import RebalanceProposal
    except (ImportError, ModuleNotFoundError):
        from app.models import RebalanceProposal

    return {
        "Trade": Trade,
        "TradeStatus": TradeStatus,
        "RebalanceProposal": RebalanceProposal,
    }


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
    """Seed test investor, portfolio, proposal, instrument, and fee schedule."""
    models = _import_trade_models()
    RebalanceProposal = models["RebalanceProposal"]

    investor = InvestorProfile(
        investor_id="INV-TR-01",
        name="Trade Test Investor",
        risk_category=RiskCategory.HIGH,
    )
    session.add(investor)
    session.flush()

    portfolio = Portfolio(
        portfolio_id="PORT-TR-01",
        investor_id="INV-TR-01",
        portfolio_name="Trading Portfolio",
        base_currency="USD",
        status=PortfolioStatus.ACTIVE,
    )
    session.add(portfolio)
    session.flush()

    proposal = RebalanceProposal(
        proposal_id="RB-2026-000100",
        portfolio_id="PORT-TR-01",
        status="DRAFT",
        review_decision="PENDING",
    )
    session.add(proposal)

    instrument = Instrument(
        instrument_id="INST-TR-AAPL",
        symbol="AAPL",
        instrument_name="Apple Inc.",
        asset_class="EQUITY",
        lot_size=Decimal("1.0000"),
        is_active=True,
    )
    session.add(instrument)

    fee_schedule = FeeSchedule(
        fee_schedule_id="FEE-TR-EQ-01",
        asset_class="EQUITY",
        trade_side="BUY",
        min_trade_value=Decimal("0.0000"),
        max_trade_value=None,
        fee_rate_bps=Decimal("10.0000"),
        fixed_fee=Decimal("1.0000"),
        minimum_fee=Decimal("2.0000"),
        currency="USD",
        effective_from=date(2026, 1, 1),
    )
    session.add(fee_schedule)
    session.commit()

    return portfolio, proposal, instrument, fee_schedule


# ==============================================================================
# Model Definition & Metadata Tests
# ==============================================================================


def test_trade_inherits_from_base():
    """Verify Trade inherits from the shared declarative Base."""
    models = _import_trade_models()
    Trade = models["Trade"]
    assert issubclass(Trade, Base), "Trade must inherit from app.models.base.Base"


def test_table_name_is_trade():
    """Verify table name is exactly 'trade'."""
    models = _import_trade_models()
    assert models["Trade"].__tablename__ == "trade"


def test_trade_id_is_primary_key_varchar_40():
    """Verify trade_id is String(40) primary key."""
    models = _import_trade_models()
    col = models["Trade"].__table__.c.trade_id

    assert col.primary_key is True, "trade_id must be primary key"
    assert isinstance(col.type, String), "trade_id must be String"
    assert col.type.length == 40, "trade_id must be String(40)"
    assert col.nullable is False, "trade_id must not be nullable"


def test_foreign_keys_and_nullability():
    """Verify foreign keys for proposal_id, instrument_id, and nullable fee_schedule_id."""
    models = _import_trade_models()
    table = models["Trade"].__table__

    # proposal_id: String(30), required FK to rebalance_proposal.proposal_id
    prop_col = table.c.proposal_id
    assert prop_col.nullable is False
    assert isinstance(prop_col.type, String)
    assert prop_col.type.length == 30
    prop_fks = {fk.target_fullname for fk in prop_col.foreign_keys}
    assert "rebalance_proposal.proposal_id" in prop_fks

    # instrument_id: String(20), required FK to instrument.instrument_id
    inst_col = table.c.instrument_id
    assert inst_col.nullable is False
    assert isinstance(inst_col.type, String)
    assert inst_col.type.length == 20
    inst_fks = {fk.target_fullname for fk in inst_col.foreign_keys}
    assert "instrument.instrument_id" in inst_fks

    # fee_schedule_id: String(20), nullable FK to fee_schedule.fee_schedule_id
    fee_col = table.c.fee_schedule_id
    assert fee_col.nullable is True, "fee_schedule_id must be nullable for anomaly handling"
    assert isinstance(fee_col.type, String)
    assert fee_col.type.length == 20
    fee_fks = {fk.target_fullname for fk in fee_col.foreign_keys}
    assert "fee_schedule.fee_schedule_id" in fee_fks


def test_required_and_numeric_columns_and_types():
    """Verify column definitions, precision, scale, and nullability."""
    models = _import_trade_models()
    table = models["Trade"].__table__

    # trade_side: String(4), required
    ts_col = table.c.trade_side
    assert isinstance(ts_col.type, String)
    assert ts_col.type.length == 4
    assert ts_col.nullable is False

    # quantity: Numeric(18, 4), required
    qty_col = table.c.quantity
    assert isinstance(qty_col.type, Numeric)
    assert qty_col.type.precision == 18
    assert qty_col.type.scale == 4
    assert qty_col.nullable is False

    # unit_price: Numeric(18, 4), required
    price_col = table.c.unit_price
    assert isinstance(price_col.type, Numeric)
    assert price_col.type.precision == 18
    assert price_col.type.scale == 4
    assert price_col.nullable is False

    # trade_value: Numeric(18, 4), required
    val_col = table.c.trade_value
    assert isinstance(val_col.type, Numeric)
    assert val_col.type.precision == 18
    assert val_col.type.scale == 4
    assert val_col.nullable is False

    # fee_amount: Numeric(18, 4), required
    fee_col = table.c.fee_amount
    assert isinstance(fee_col.type, Numeric)
    assert fee_col.type.precision == 18
    assert fee_col.type.scale == 4
    assert fee_col.nullable is False

    # status: String(20), required
    status_col = table.c.status
    assert isinstance(status_col.type, String)
    assert status_col.type.length == 20
    assert status_col.nullable is False

    # created_at: DateTime(timezone=True), required, default
    created_col = table.c.created_at
    assert isinstance(created_col.type, DateTime)
    assert created_col.type.timezone is True
    assert created_col.nullable is False
    has_default = (created_col.default is not None) or (
        created_col.server_default is not None
    )
    assert has_default, "created_at must have a default"


# ==============================================================================
# Database Constraint Validation Tests
# ==============================================================================


def test_trade_side_check_constraint():
    """Verify trade_side accepts BUY and SELL, and rejects other values."""
    models = _import_trade_models()
    Trade = models["Trade"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _, proposal, instrument, fee_sched = _setup_prerequisites(session)

            for side in ["BUY", "SELL"]:
                t = Trade(
                    trade_id=f"TR-SIDE-{side}",
                    proposal_id=proposal.proposal_id,
                    instrument_id=instrument.instrument_id,
                    fee_schedule_id=fee_sched.fee_schedule_id,
                    trade_side=side,
                    quantity=Decimal("10.0000"),
                    unit_price=Decimal("150.0000"),
                    trade_value=Decimal("1500.0000"),
                    fee_amount=Decimal("2.5000"),
                    status="PROPOSED",
                )
                session.add(t)
            session.commit()

            # Invalid trade_side rejected
            with pytest.raises(IntegrityError):
                t_bad = Trade(
                    trade_id="TR-SIDE-BAD",
                    proposal_id=proposal.proposal_id,
                    instrument_id=instrument.instrument_id,
                    trade_side="HOLD",
                    quantity=Decimal("10.0000"),
                    unit_price=Decimal("150.0000"),
                    trade_value=Decimal("1500.0000"),
                    fee_amount=Decimal("2.5000"),
                    status="PROPOSED",
                )
                session.add(t_bad)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_trade_status_check_constraint():
    """Verify status accepts PROPOSED, BLOCKED, APPROVED, REJECTED, and rejects others."""
    models = _import_trade_models()
    Trade = models["Trade"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _, proposal, instrument, fee_sched = _setup_prerequisites(session)

            valid_statuses = ["PROPOSED", "BLOCKED", "APPROVED", "REJECTED"]
            for idx, st in enumerate(valid_statuses):
                t = Trade(
                    trade_id=f"TR-STAT-{idx}",
                    proposal_id=proposal.proposal_id,
                    instrument_id=instrument.instrument_id,
                    trade_side="BUY",
                    quantity=Decimal("5.0000"),
                    unit_price=Decimal("100.0000"),
                    trade_value=Decimal("500.0000"),
                    fee_amount=Decimal("1.0000"),
                    status=st,
                )
                session.add(t)
            session.commit()

            # Invalid status rejected
            with pytest.raises(IntegrityError):
                t_bad = Trade(
                    trade_id="TR-STAT-BAD",
                    proposal_id=proposal.proposal_id,
                    instrument_id=instrument.instrument_id,
                    trade_side="BUY",
                    quantity=Decimal("5.0000"),
                    unit_price=Decimal("100.0000"),
                    trade_value=Decimal("500.0000"),
                    fee_amount=Decimal("1.0000"),
                    status="EXECUTED",
                )
                session.add(t_bad)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_strictly_positive_numeric_check_constraints():
    """Verify quantity, unit_price, and trade_value must be strictly positive (> 0)."""
    models = _import_trade_models()
    Trade = models["Trade"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _, proposal, instrument, _ = _setup_prerequisites(session)

            # Zero quantity rejected
            with pytest.raises(IntegrityError):
                t_zero_qty = Trade(
                    trade_id="TR-ZERO-QTY",
                    proposal_id=proposal.proposal_id,
                    instrument_id=instrument.instrument_id,
                    trade_side="BUY",
                    quantity=Decimal("0.0000"),
                    unit_price=Decimal("100.0000"),
                    trade_value=Decimal("100.0000"),
                    fee_amount=Decimal("1.0000"),
                    status="PROPOSED",
                )
                session.add(t_zero_qty)
                session.commit()
            session.rollback()

            # Negative quantity rejected
            with pytest.raises(IntegrityError):
                t_neg_qty = Trade(
                    trade_id="TR-NEG-QTY",
                    proposal_id=proposal.proposal_id,
                    instrument_id=instrument.instrument_id,
                    trade_side="BUY",
                    quantity=Decimal("-1.0000"),
                    unit_price=Decimal("100.0000"),
                    trade_value=Decimal("100.0000"),
                    fee_amount=Decimal("1.0000"),
                    status="PROPOSED",
                )
                session.add(t_neg_qty)
                session.commit()
            session.rollback()

            # Zero unit_price rejected
            with pytest.raises(IntegrityError):
                t_zero_price = Trade(
                    trade_id="TR-ZERO-PRICE",
                    proposal_id=proposal.proposal_id,
                    instrument_id=instrument.instrument_id,
                    trade_side="BUY",
                    quantity=Decimal("1.0000"),
                    unit_price=Decimal("0.0000"),
                    trade_value=Decimal("100.0000"),
                    fee_amount=Decimal("1.0000"),
                    status="PROPOSED",
                )
                session.add(t_zero_price)
                session.commit()
            session.rollback()

            # Zero trade_value rejected
            with pytest.raises(IntegrityError):
                t_zero_val = Trade(
                    trade_id="TR-ZERO-VAL",
                    proposal_id=proposal.proposal_id,
                    instrument_id=instrument.instrument_id,
                    trade_side="BUY",
                    quantity=Decimal("1.0000"),
                    unit_price=Decimal("100.0000"),
                    trade_value=Decimal("0.0000"),
                    fee_amount=Decimal("1.0000"),
                    status="PROPOSED",
                )
                session.add(t_zero_val)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_fee_amount_nonnegative_check_constraint():
    """Verify fee_amount must be nonnegative (>= 0)."""
    models = _import_trade_models()
    Trade = models["Trade"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _, proposal, instrument, _ = _setup_prerequisites(session)

            # Zero fee_amount is valid (e.g. commission-free trade)
            t_zero_fee = Trade(
                trade_id="TR-ZERO-FEE",
                proposal_id=proposal.proposal_id,
                instrument_id=instrument.instrument_id,
                trade_side="BUY",
                quantity=Decimal("1.0000"),
                unit_price=Decimal("100.0000"),
                trade_value=Decimal("100.0000"),
                fee_amount=Decimal("0.0000"),
                status="PROPOSED",
            )
            session.add(t_zero_fee)
            session.commit()

            # Negative fee_amount rejected
            with pytest.raises(IntegrityError):
                t_neg_fee = Trade(
                    trade_id="TR-NEG-FEE",
                    proposal_id=proposal.proposal_id,
                    instrument_id=instrument.instrument_id,
                    trade_side="BUY",
                    quantity=Decimal("1.0000"),
                    unit_price=Decimal("100.0000"),
                    trade_value=Decimal("100.0000"),
                    fee_amount=Decimal("-0.0100"),
                    status="PROPOSED",
                )
                session.add(t_neg_fee)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_trade_with_null_fee_schedule_id_allowed():
    """Verify a Trade may have a NULL fee_schedule_id for missing-fee anomaly representation."""
    models = _import_trade_models()
    Trade = models["Trade"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _, proposal, instrument, _ = _setup_prerequisites(session)

            t_null_fee = Trade(
                trade_id="TR-NULL-FEE-SCHED",
                proposal_id=proposal.proposal_id,
                instrument_id=instrument.instrument_id,
                fee_schedule_id=None,
                trade_side="SELL",
                quantity=Decimal("20.0000"),
                unit_price=Decimal("50.0000"),
                trade_value=Decimal("1000.0000"),
                fee_amount=Decimal("0.0000"),
                status="BLOCKED",
            )
            session.add(t_null_fee)
            session.commit()

            retrieved = session.scalar(
                select(Trade).where(Trade.trade_id == "TR-NULL-FEE-SCHED")
            )
            assert retrieved is not None
            assert retrieved.fee_schedule_id is None
            assert retrieved.status == "BLOCKED"
    finally:
        engine.dispose()


def test_model_registered_in_metadata():
    """Verify trade table is registered in Base.metadata."""
    _import_trade_models()
    assert "trade" in Base.metadata.tables


# ==============================================================================
# SQLite In-Memory CRUD & Relationship Tests
# ==============================================================================


def test_trade_sqlite_insert_and_retrieval():
    """Verify valid Trade insertion and retrieval with SQLite."""
    models = _import_trade_models()
    Trade = models["Trade"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _, proposal, instrument, fee_sched = _setup_prerequisites(session)

            t = Trade(
                trade_id="TR-2026-000001",
                proposal_id=proposal.proposal_id,
                instrument_id=instrument.instrument_id,
                fee_schedule_id=fee_sched.fee_schedule_id,
                trade_side="BUY",
                quantity=Decimal("25.0000"),
                unit_price=Decimal("180.5000"),
                trade_value=Decimal("4512.5000"),
                fee_amount=Decimal("4.5125"),
                status="PROPOSED",
            )
            session.add(t)
            session.commit()

            retrieved = session.scalar(
                select(Trade).where(Trade.trade_id == "TR-2026-000001")
            )
            assert retrieved is not None
            assert retrieved.trade_id == "TR-2026-000001"
            assert retrieved.proposal_id == proposal.proposal_id
            assert retrieved.instrument_id == instrument.instrument_id
            assert retrieved.fee_schedule_id == fee_sched.fee_schedule_id
            assert retrieved.trade_side == "BUY"
            assert retrieved.quantity == Decimal("25.0000")
            assert retrieved.unit_price == Decimal("180.5000")
            assert retrieved.trade_value == Decimal("4512.5000")
            assert retrieved.fee_amount == Decimal("4.5125")
            assert retrieved.status == "PROPOSED"
            assert retrieved.created_at is not None
    finally:
        engine.dispose()


def test_invalid_foreign_keys_rejected_sqlite():
    """Verify foreign key violations are rejected with SQLite FK enforcement."""
    models = _import_trade_models()
    Trade = models["Trade"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _, proposal, instrument, fee_sched = _setup_prerequisites(session)

            # Invalid proposal_id
            with pytest.raises(IntegrityError):
                t_bad_prop = Trade(
                    trade_id="TR-BAD-PROP",
                    proposal_id="NONEXISTENT-PROP",
                    instrument_id=instrument.instrument_id,
                    trade_side="BUY",
                    quantity=Decimal("1.0000"),
                    unit_price=Decimal("10.0000"),
                    trade_value=Decimal("10.0000"),
                    fee_amount=Decimal("1.0000"),
                    status="PROPOSED",
                )
                session.add(t_bad_prop)
                session.commit()
            session.rollback()

            # Invalid instrument_id
            with pytest.raises(IntegrityError):
                t_bad_inst = Trade(
                    trade_id="TR-BAD-INST",
                    proposal_id=proposal.proposal_id,
                    instrument_id="NONEXISTENT-INST",
                    trade_side="BUY",
                    quantity=Decimal("1.0000"),
                    unit_price=Decimal("10.0000"),
                    trade_value=Decimal("10.0000"),
                    fee_amount=Decimal("1.0000"),
                    status="PROPOSED",
                )
                session.add(t_bad_inst)
                session.commit()
            session.rollback()

            # Invalid fee_schedule_id
            with pytest.raises(IntegrityError):
                t_bad_fee = Trade(
                    trade_id="TR-BAD-FEE",
                    proposal_id=proposal.proposal_id,
                    instrument_id=instrument.instrument_id,
                    fee_schedule_id="NONEXISTENT-FEE",
                    trade_side="BUY",
                    quantity=Decimal("1.0000"),
                    unit_price=Decimal("10.0000"),
                    trade_value=Decimal("10.0000"),
                    fee_amount=Decimal("1.0000"),
                    status="PROPOSED",
                )
                session.add(t_bad_fee)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_relationships():
    """Verify bidirectional navigation across Trade, RebalanceProposal, Instrument, and FeeSchedule."""
    models = _import_trade_models()
    Trade = models["Trade"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _, proposal, instrument, fee_sched = _setup_prerequisites(session)

            t = Trade(
                trade_id="TR-REL-01",
                proposal_id=proposal.proposal_id,
                instrument_id=instrument.instrument_id,
                fee_schedule_id=fee_sched.fee_schedule_id,
                trade_side="BUY",
                quantity=Decimal("10.0000"),
                unit_price=Decimal("50.0000"),
                trade_value=Decimal("500.0000"),
                fee_amount=Decimal("2.0000"),
                status="PROPOSED",
            )
            session.add(t)
            session.commit()

            reloaded_trade = session.scalar(
                select(Trade).where(Trade.trade_id == "TR-REL-01")
            )
            assert reloaded_trade is not None
            assert reloaded_trade.proposal.proposal_id == proposal.proposal_id
            assert reloaded_trade.instrument.instrument_id == instrument.instrument_id
            assert reloaded_trade.fee_schedule.fee_schedule_id == fee_sched.fee_schedule_id

            # Reverse relationships
            assert any(tr.trade_id == "TR-REL-01" for tr in proposal.trades)
            assert any(tr.trade_id == "TR-REL-01" for tr in instrument.trades)
            assert any(tr.trade_id == "TR-REL-01" for tr in fee_sched.trades)
    finally:
        engine.dispose()

