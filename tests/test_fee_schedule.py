"""Tests for SQLAlchemy FeeSchedule entity.

Following Test-Driven Development (TDD), these tests define the specifications
and contracts for the FeeSchedule model before implementation.
"""

from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import (
    Boolean,
    Date,
    Numeric,
    String,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.base import Base


def _import_fee_schedule():
    """Dynamically import FeeSchedule model."""
    try:
        from app.models.fee_schedule import FeeSchedule
        return FeeSchedule
    except (ImportError, ModuleNotFoundError):
        from app.models import FeeSchedule
        return FeeSchedule


def _import_trade_side():
    """Dynamically import TradeSide enum if defined."""
    try:
        from app.models.fee_schedule import TradeSide
        return TradeSide
    except (ImportError, ModuleNotFoundError):
        from app.models import TradeSide
        return TradeSide


def _create_sqlite_engine():
    """Create an in-memory SQLite engine."""
    return create_engine("sqlite:///:memory:")


# ==============================================================================
# Model Definition & Metadata Tests
# ==============================================================================


def test_fee_schedule_inherits_from_base():
    """Verify FeeSchedule inherits from the shared declarative Base."""
    FeeSchedule = _import_fee_schedule()
    assert issubclass(FeeSchedule, Base), (
        "FeeSchedule must inherit from app.models.base.Base"
    )


def test_table_name_is_fee_schedule():
    """Verify table name is exactly 'fee_schedule'."""
    FeeSchedule = _import_fee_schedule()
    assert FeeSchedule.__tablename__ == "fee_schedule"


def test_fee_schedule_id_is_primary_key_varchar_20():
    """Verify fee_schedule_id is String(20) primary key."""
    FeeSchedule = _import_fee_schedule()
    col = FeeSchedule.__table__.c.fee_schedule_id

    assert col.primary_key is True, "fee_schedule_id must be the primary key"
    assert isinstance(col.type, String), "fee_schedule_id must be String"
    assert col.type.length == 20, "fee_schedule_id must be String(20)"
    assert col.nullable is False, "Primary key must not be nullable"


def test_required_columns_and_types():
    """Verify column definitions, types, precision/scale, and nullability."""
    FeeSchedule = _import_fee_schedule()
    table = FeeSchedule.__table__

    # asset_class: String(50), required
    ac_col = table.c.asset_class
    assert isinstance(ac_col.type, String), "asset_class must be String"
    assert ac_col.type.length == 50, "asset_class must be String(50)"
    assert ac_col.nullable is False, "asset_class must not be nullable"

    # trade_side: String(4), required
    ts_col = table.c.trade_side
    assert isinstance(ts_col.type, String), "trade_side must be String"
    assert ts_col.type.length == 4, "trade_side must be String(4)"
    assert ts_col.nullable is False, "trade_side must not be nullable"

    # min_trade_value: Numeric(18, 4), required
    min_col = table.c.min_trade_value
    assert isinstance(min_col.type, Numeric), "min_trade_value must be Numeric"
    assert min_col.type.precision == 18, "min_trade_value precision must be 18"
    assert min_col.type.scale == 4, "min_trade_value scale must be 4"
    assert min_col.nullable is False, "min_trade_value must not be nullable"

    # max_trade_value: Numeric(18, 4), nullable
    max_col = table.c.max_trade_value
    assert isinstance(max_col.type, Numeric), "max_trade_value must be Numeric"
    assert max_col.type.precision == 18, "max_trade_value precision must be 18"
    assert max_col.type.scale == 4, "max_trade_value scale must be 4"
    assert max_col.nullable is True, "max_trade_value must be nullable"

    # fee_rate_bps: Numeric(10, 4), required
    bps_col = table.c.fee_rate_bps
    assert isinstance(bps_col.type, Numeric), "fee_rate_bps must be Numeric"
    assert bps_col.type.precision == 10, "fee_rate_bps precision must be 10"
    assert bps_col.type.scale == 4, "fee_rate_bps scale must be 4"
    assert bps_col.nullable is False, "fee_rate_bps must not be nullable"

    # fixed_fee: Numeric(18, 4), required
    ff_col = table.c.fixed_fee
    assert isinstance(ff_col.type, Numeric), "fixed_fee must be Numeric"
    assert ff_col.type.precision == 18, "fixed_fee precision must be 18"
    assert ff_col.type.scale == 4, "fixed_fee scale must be 4"
    assert ff_col.nullable is False, "fixed_fee must not be nullable"

    # minimum_fee: Numeric(18, 4), required
    min_fee_col = table.c.minimum_fee
    assert isinstance(min_fee_col.type, Numeric), "minimum_fee must be Numeric"
    assert min_fee_col.type.precision == 18, "minimum_fee precision must be 18"
    assert min_fee_col.type.scale == 4, "minimum_fee scale must be 4"
    assert min_fee_col.nullable is False, "minimum_fee must not be nullable"

    # maximum_fee: Numeric(18, 4), nullable
    max_fee_col = table.c.maximum_fee
    assert isinstance(max_fee_col.type, Numeric), "maximum_fee must be Numeric"
    assert max_fee_col.type.precision == 18, "maximum_fee precision must be 18"
    assert max_fee_col.type.scale == 4, "maximum_fee scale must be 4"
    assert max_fee_col.nullable is True, "maximum_fee must be nullable"

    # currency: String(3), required
    curr_col = table.c.currency
    assert isinstance(curr_col.type, String), "currency must be String"
    assert curr_col.type.length == 3, "currency must be String(3)"
    assert curr_col.nullable is False, "currency must not be nullable"

    # effective_from: Date, required
    ef_col = table.c.effective_from
    assert isinstance(ef_col.type, Date), "effective_from must be Date"
    assert ef_col.nullable is False, "effective_from must not be nullable"

    # effective_to: Date, nullable
    et_col = table.c.effective_to
    assert isinstance(et_col.type, Date), "effective_to must be Date"
    assert et_col.nullable is True, "effective_to must be nullable"

    # is_active: Boolean, required, with default
    active_col = table.c.is_active
    assert isinstance(active_col.type, Boolean), "is_active must be Boolean"
    assert active_col.nullable is False, "is_active must not be nullable"
    has_default = (active_col.default is not None) or (
        active_col.server_default is not None
    )
    assert has_default, "is_active must have a default"


def test_trade_value_range_check_constraint():
    """Verify check constraint on min_trade_value >= 0 and max_trade_value >= min_trade_value."""
    FeeSchedule = _import_fee_schedule()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            # Valid tier: unbounded upper value (max_trade_value=None)
            unbounded = FeeSchedule(
                fee_schedule_id="FEE-VAL-01",
                asset_class="EQUITY",
                trade_side="BUY",
                min_trade_value=Decimal("10000.0000"),
                max_trade_value=None,
                fee_rate_bps=Decimal("15.0000"),
                fixed_fee=Decimal("1.0000"),
                minimum_fee=Decimal("2.0000"),
                maximum_fee=None,
                currency="USD",
                effective_from=date(2026, 1, 1),
            )
            session.add(unbounded)

            # Valid tier: bounded upper value
            bounded = FeeSchedule(
                fee_schedule_id="FEE-VAL-02",
                asset_class="EQUITY",
                trade_side="BUY",
                min_trade_value=Decimal("0.0000"),
                max_trade_value=Decimal("9999.9999"),
                fee_rate_bps=Decimal("25.0000"),
                fixed_fee=Decimal("1.5000"),
                minimum_fee=Decimal("2.5000"),
                maximum_fee=Decimal("100.0000"),
                currency="USD",
                effective_from=date(2026, 1, 1),
            )
            session.add(bounded)
            session.commit()

            # Invalid: min_trade_value < 0 must be rejected
            with pytest.raises(IntegrityError):
                neg_min = FeeSchedule(
                    fee_schedule_id="FEE-INV-01",
                    asset_class="EQUITY",
                    trade_side="SELL",
                    min_trade_value=Decimal("-1.0000"),
                    max_trade_value=Decimal("1000.0000"),
                    fee_rate_bps=Decimal("10.0000"),
                    fixed_fee=Decimal("0.0000"),
                    minimum_fee=Decimal("0.0000"),
                    maximum_fee=None,
                    currency="USD",
                    effective_from=date(2026, 1, 1),
                )
                session.add(neg_min)
                session.commit()
            session.rollback()

            # Invalid: max_trade_value < min_trade_value must be rejected
            with pytest.raises(IntegrityError):
                inverted = FeeSchedule(
                    fee_schedule_id="FEE-INV-02",
                    asset_class="EQUITY",
                    trade_side="SELL",
                    min_trade_value=Decimal("5000.0000"),
                    max_trade_value=Decimal("4999.0000"),
                    fee_rate_bps=Decimal("10.0000"),
                    fixed_fee=Decimal("0.0000"),
                    minimum_fee=Decimal("0.0000"),
                    maximum_fee=None,
                    currency="USD",
                    effective_from=date(2026, 1, 1),
                )
                session.add(inverted)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_fees_nonnegative_check_constraint():
    """Verify fee_rate_bps, fixed_fee, and minimum_fee must be nonnegative."""
    FeeSchedule = _import_fee_schedule()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            # Zero fees are valid
            zero_fee = FeeSchedule(
                fee_schedule_id="FEE-ZERO-01",
                asset_class="CASH",
                trade_side="BUY",
                min_trade_value=Decimal("0.0000"),
                max_trade_value=None,
                fee_rate_bps=Decimal("0.0000"),
                fixed_fee=Decimal("0.0000"),
                minimum_fee=Decimal("0.0000"),
                maximum_fee=None,
                currency="USD",
                effective_from=date(2026, 1, 1),
            )
            session.add(zero_fee)
            session.commit()

            # Negative fee_rate_bps rejected
            with pytest.raises(IntegrityError):
                neg_bps = FeeSchedule(
                    fee_schedule_id="FEE-NEG-BPS",
                    asset_class="EQUITY",
                    trade_side="BUY",
                    min_trade_value=Decimal("0.0000"),
                    fee_rate_bps=Decimal("-0.0001"),
                    fixed_fee=Decimal("0.0000"),
                    minimum_fee=Decimal("0.0000"),
                    currency="USD",
                    effective_from=date(2026, 1, 1),
                )
                session.add(neg_bps)
                session.commit()
            session.rollback()

            # Negative fixed_fee rejected
            with pytest.raises(IntegrityError):
                neg_fixed = FeeSchedule(
                    fee_schedule_id="FEE-NEG-FIXED",
                    asset_class="EQUITY",
                    trade_side="BUY",
                    min_trade_value=Decimal("0.0000"),
                    fee_rate_bps=Decimal("10.0000"),
                    fixed_fee=Decimal("-0.0100"),
                    minimum_fee=Decimal("0.0000"),
                    currency="USD",
                    effective_from=date(2026, 1, 1),
                )
                session.add(neg_fixed)
                session.commit()
            session.rollback()

            # Negative minimum_fee rejected
            with pytest.raises(IntegrityError):
                neg_min_fee = FeeSchedule(
                    fee_schedule_id="FEE-NEG-MINFEE",
                    asset_class="EQUITY",
                    trade_side="BUY",
                    min_trade_value=Decimal("0.0000"),
                    fee_rate_bps=Decimal("10.0000"),
                    fixed_fee=Decimal("0.0000"),
                    minimum_fee=Decimal("-1.0000"),
                    currency="USD",
                    effective_from=date(2026, 1, 1),
                )
                session.add(neg_min_fee)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_maximum_fee_check_constraint():
    """Verify maximum_fee must be NULL or >= minimum_fee."""
    FeeSchedule = _import_fee_schedule()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            # maximum_fee == minimum_fee is valid (flat fee ceiling)
            equal_fee = FeeSchedule(
                fee_schedule_id="FEE-EQUAL-01",
                asset_class="FIXED_INCOME",
                trade_side="BUY",
                min_trade_value=Decimal("0.0000"),
                fee_rate_bps=Decimal("5.0000"),
                fixed_fee=Decimal("2.0000"),
                minimum_fee=Decimal("5.0000"),
                maximum_fee=Decimal("5.0000"),
                currency="USD",
                effective_from=date(2026, 1, 1),
            )
            session.add(equal_fee)
            session.commit()

            # maximum_fee < minimum_fee must be rejected
            with pytest.raises(IntegrityError):
                invalid_max = FeeSchedule(
                    fee_schedule_id="FEE-INV-MAX",
                    asset_class="FIXED_INCOME",
                    trade_side="SELL",
                    min_trade_value=Decimal("0.0000"),
                    fee_rate_bps=Decimal("5.0000"),
                    fixed_fee=Decimal("2.0000"),
                    minimum_fee=Decimal("10.0000"),
                    maximum_fee=Decimal("9.9999"),
                    currency="USD",
                    effective_from=date(2026, 1, 1),
                )
                session.add(invalid_max)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_effective_dates_check_constraint():
    """Verify effective date range must be valid: effective_to IS NULL OR >= effective_from."""
    FeeSchedule = _import_fee_schedule()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            # Open-ended schedule
            open_ended = FeeSchedule(
                fee_schedule_id="FEE-DATE-01",
                asset_class="EQUITY",
                trade_side="BUY",
                min_trade_value=Decimal("0.0000"),
                fee_rate_bps=Decimal("10.0000"),
                fixed_fee=Decimal("0.0000"),
                minimum_fee=Decimal("0.0000"),
                currency="USD",
                effective_from=date(2026, 1, 1),
                effective_to=None,
            )
            session.add(open_ended)

            # Same day schedule
            same_day = FeeSchedule(
                fee_schedule_id="FEE-DATE-02",
                asset_class="EQUITY",
                trade_side="SELL",
                min_trade_value=Decimal("0.0000"),
                fee_rate_bps=Decimal("10.0000"),
                fixed_fee=Decimal("0.0000"),
                minimum_fee=Decimal("0.0000"),
                currency="USD",
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 1, 1),
            )
            session.add(same_day)
            session.commit()

            # Invalid: effective_to < effective_from
            with pytest.raises(IntegrityError):
                inverted_dates = FeeSchedule(
                    fee_schedule_id="FEE-DATE-INV",
                    asset_class="COMMODITY",
                    trade_side="BUY",
                    min_trade_value=Decimal("0.0000"),
                    fee_rate_bps=Decimal("10.0000"),
                    fixed_fee=Decimal("0.0000"),
                    minimum_fee=Decimal("0.0000"),
                    currency="USD",
                    effective_from=date(2026, 6, 1),
                    effective_to=date(2026, 5, 31),
                )
                session.add(inverted_dates)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_trade_side_check_constraint():
    """Verify trade_side allows only 'BUY' and 'SELL'."""
    FeeSchedule = _import_fee_schedule()
    TradeSide = _import_trade_side()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            # Valid BUY
            buy_sched = FeeSchedule(
                fee_schedule_id="FEE-SIDE-BUY",
                asset_class="EQUITY",
                trade_side="BUY" if TradeSide is None else TradeSide.BUY,
                min_trade_value=Decimal("0.0000"),
                fee_rate_bps=Decimal("10.0000"),
                fixed_fee=Decimal("0.0000"),
                minimum_fee=Decimal("0.0000"),
                currency="USD",
                effective_from=date(2026, 1, 1),
            )
            session.add(buy_sched)

            # Valid SELL
            sell_sched = FeeSchedule(
                fee_schedule_id="FEE-SIDE-SELL",
                asset_class="EQUITY",
                trade_side="SELL" if TradeSide is None else TradeSide.SELL,
                min_trade_value=Decimal("0.0000"),
                fee_rate_bps=Decimal("10.0000"),
                fixed_fee=Decimal("0.0000"),
                minimum_fee=Decimal("0.0000"),
                currency="USD",
                effective_from=date(2026, 1, 1),
            )
            session.add(sell_sched)
            session.commit()

            # Invalid trade_side must be rejected
            with pytest.raises((IntegrityError, ValueError)):
                invalid_side = FeeSchedule(
                    fee_schedule_id="FEE-SIDE-INV",
                    asset_class="EQUITY",
                    trade_side="HOLD",
                    min_trade_value=Decimal("0.0000"),
                    fee_rate_bps=Decimal("10.0000"),
                    fixed_fee=Decimal("0.0000"),
                    minimum_fee=Decimal("0.0000"),
                    currency="USD",
                    effective_from=date(2026, 1, 1),
                )
                session.add(invalid_side)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_composite_unique_constraint_on_tier():
    """Verify UNIQUE (asset_class, trade_side, min_trade_value, effective_from)."""
    FeeSchedule = _import_fee_schedule()
    table = FeeSchedule.__table__

    expected_cols = {"asset_class", "trade_side", "min_trade_value", "effective_from"}
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
        "FeeSchedule must have a UniqueConstraint on "
        "(asset_class, trade_side, min_trade_value, effective_from)"
    )


def test_duplicate_tier_rejected_sqlite():
    """Verify duplicate tier with same asset_class, trade_side, min_trade_value, and effective_from is rejected."""
    FeeSchedule = _import_fee_schedule()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            f1 = FeeSchedule(
                fee_schedule_id="FEE-DUP-01",
                asset_class="EQUITY",
                trade_side="BUY",
                min_trade_value=Decimal("0.0000"),
                max_trade_value=Decimal("10000.0000"),
                fee_rate_bps=Decimal("15.0000"),
                fixed_fee=Decimal("1.0000"),
                minimum_fee=Decimal("2.0000"),
                currency="USD",
                effective_from=date(2026, 1, 1),
            )
            session.add(f1)
            session.commit()

            # Duplicate tier configuration (different ID, same tier key)
            f2 = FeeSchedule(
                fee_schedule_id="FEE-DUP-02",
                asset_class="EQUITY",
                trade_side="BUY",
                min_trade_value=Decimal("0.0000"),
                max_trade_value=Decimal("20000.0000"),
                fee_rate_bps=Decimal("12.0000"),
                fixed_fee=Decimal("1.0000"),
                minimum_fee=Decimal("2.0000"),
                currency="USD",
                effective_from=date(2026, 1, 1),
            )
            session.add(f2)
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_model_registered_in_metadata():
    """Verify fee_schedule table is registered in Base.metadata."""
    _import_fee_schedule()
    assert "fee_schedule" in Base.metadata.tables, (
        "'fee_schedule' table must be registered in Base.metadata"
    )


def test_valid_insert_and_retrieval_sqlite():
    """Verify valid FeeSchedule insertion and retrieval with SQLite in-memory."""
    FeeSchedule = _import_fee_schedule()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            tier = FeeSchedule(
                fee_schedule_id="FEE-USD-EQ-B1",
                asset_class="EQUITY",
                trade_side="BUY",
                min_trade_value=Decimal("1000.0000"),
                max_trade_value=Decimal("50000.0000"),
                fee_rate_bps=Decimal("12.5000"),
                fixed_fee=Decimal("2.0000"),
                minimum_fee=Decimal("5.0000"),
                maximum_fee=Decimal("250.0000"),
                currency="USD",
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 31),
                is_active=True,
            )
            session.add(tier)
            session.commit()

            retrieved = session.scalar(
                select(FeeSchedule).where(FeeSchedule.fee_schedule_id == "FEE-USD-EQ-B1")
            )
            assert retrieved is not None
            assert retrieved.fee_schedule_id == "FEE-USD-EQ-B1"
            assert retrieved.asset_class == "EQUITY"
            assert retrieved.trade_side == "BUY"
            assert retrieved.min_trade_value == Decimal("1000.0000")
            assert retrieved.max_trade_value == Decimal("50000.0000")
            assert retrieved.fee_rate_bps == Decimal("12.5000")
            assert retrieved.fixed_fee == Decimal("2.0000")
            assert retrieved.minimum_fee == Decimal("5.0000")
            assert retrieved.maximum_fee == Decimal("250.0000")
            assert retrieved.currency == "USD"
            assert retrieved.effective_from == date(2026, 1, 1)
            assert retrieved.effective_to == date(2026, 12, 31)
            assert retrieved.is_active is True
    finally:
        engine.dispose()

