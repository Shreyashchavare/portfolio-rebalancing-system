"""Tests for SQLAlchemy TargetAllocation entity.

Following Test-Driven Development (TDD), these tests define the specifications
and contracts for the TargetAllocation model before implementation.
"""

from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import (
    BigInteger,
    Date,
    Numeric,
    String,
    UniqueConstraint,
    create_engine,
    event,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.investor_profile import InvestorProfile, RiskCategory
from app.models.portfolio import Portfolio, PortfolioStatus


def _import_target_allocation():
    """Dynamically import TargetAllocation model."""
    try:
        from app.models.target_allocation import TargetAllocation
        return TargetAllocation
    except (ImportError, ModuleNotFoundError):
        from app.models import TargetAllocation
        return TargetAllocation


def _create_sqlite_engine():
    """Create an in-memory SQLite engine with foreign key enforcement enabled."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def _setup_prerequisites(session: Session) -> Portfolio:
    """Create prerequisite InvestorProfile and Portfolio records."""
    investor = InvestorProfile(
        investor_id="INV-TA-01",
        name="Target Allocation Investor",
        risk_category=RiskCategory.MODERATE,
    )
    session.add(investor)
    session.flush()

    portfolio = Portfolio(
        portfolio_id="PORT-TA-01",
        investor_id="INV-TA-01",
        portfolio_name="Asset Allocation Portfolio",
        base_currency="USD",
        status=PortfolioStatus.ACTIVE,
    )
    session.add(portfolio)
    session.commit()
    return portfolio


# ==============================================================================
# Model Definition & Metadata Tests
# ==============================================================================


def test_target_allocation_inherits_from_base():
    """Verify TargetAllocation inherits from the shared declarative Base."""
    TargetAllocation = _import_target_allocation()
    assert issubclass(TargetAllocation, Base), (
        "TargetAllocation must inherit from app.models.base.Base"
    )


def test_table_name_is_target_allocation():
    """Verify table name is exactly 'target_allocation'."""
    TargetAllocation = _import_target_allocation()
    assert TargetAllocation.__tablename__ == "target_allocation"


def test_id_is_bigint_primary_key_with_sqlite_variant():
    """Verify id is BIGINT identity primary key."""
    TargetAllocation = _import_target_allocation()
    col = TargetAllocation.__table__.c.id

    assert col.primary_key is True, "id must be the primary key"
    assert isinstance(col.type, BigInteger), "id must be BigInteger type"
    assert col.nullable is False, "Primary key id must not be nullable"


def test_portfolio_id_is_foreign_key_varchar_40():
    """Verify portfolio_id is a required foreign key referencing portfolio.portfolio_id."""
    TargetAllocation = _import_target_allocation()
    col = TargetAllocation.__table__.c.portfolio_id

    assert col.nullable is False, "portfolio_id must not be nullable"
    assert isinstance(col.type, String), "portfolio_id must be String/VARCHAR"
    assert col.type.length == 40, "portfolio_id must be VARCHAR(40)"

    fk_targets = {fk.target_fullname for fk in col.foreign_keys}
    assert "portfolio.portfolio_id" in fk_targets, (
        "portfolio_id must have a foreign key to portfolio.portfolio_id"
    )


def test_required_fields_and_types():
    """Verify columns and nullability for asset_class, target_weight, effective_from, and effective_to."""
    TargetAllocation = _import_target_allocation()
    table = TargetAllocation.__table__

    # asset_class: String(50), required
    ac_col = table.c.asset_class
    assert isinstance(ac_col.type, String), "asset_class must be String"
    assert ac_col.type.length == 50, "asset_class must be String(50)"
    assert ac_col.nullable is False, "asset_class must not be nullable"

    # target_weight: Numeric(7, 4), required
    tw_col = table.c.target_weight
    assert isinstance(tw_col.type, Numeric), "target_weight must be Numeric/Decimal"
    assert tw_col.type.precision == 7, "target_weight precision must be 7"
    assert tw_col.type.scale == 4, "target_weight scale must be 4"
    assert tw_col.nullable is False, "target_weight must not be nullable"

    # effective_from: Date, required
    ef_col = table.c.effective_from
    assert isinstance(ef_col.type, Date), "effective_from must be Date"
    assert ef_col.nullable is False, "effective_from must not be nullable"

    # effective_to: Date, nullable
    et_col = table.c.effective_to
    assert isinstance(et_col.type, Date), "effective_to must be Date"
    assert et_col.nullable is True, "effective_to must be nullable"


def test_target_weight_range_constraint():
    """Verify target_weight allows 0 and 100 inclusive, and rejects < 0 or > 100."""
    TargetAllocation = _import_target_allocation()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisites(session)

            # 0% weight is valid
            alloc_zero = TargetAllocation(
                portfolio_id="PORT-TA-01",
                asset_class="CASH",
                target_weight=Decimal("0.0000"),
                effective_from=date(2026, 1, 1),
            )
            session.add(alloc_zero)

            # 100% weight is valid
            alloc_hundred = TargetAllocation(
                portfolio_id="PORT-TA-01",
                asset_class="EQUITY",
                target_weight=Decimal("100.0000"),
                effective_from=date(2026, 1, 1),
            )
            session.add(alloc_hundred)

            # 50.5% weight is valid
            alloc_mid = TargetAllocation(
                portfolio_id="PORT-TA-01",
                asset_class="FIXED_INCOME",
                target_weight=Decimal("50.5000"),
                effective_from=date(2026, 1, 1),
            )
            session.add(alloc_mid)
            session.commit()

            # Weight < 0 must be rejected
            with pytest.raises(IntegrityError):
                alloc_neg = TargetAllocation(
                    portfolio_id="PORT-TA-01",
                    asset_class="COMMODITIES",
                    target_weight=Decimal("-0.0001"),
                    effective_from=date(2026, 1, 1),
                )
                session.add(alloc_neg)
                session.commit()
            session.rollback()

            # Weight > 100 must be rejected
            with pytest.raises(IntegrityError):
                alloc_over = TargetAllocation(
                    portfolio_id="PORT-TA-01",
                    asset_class="REAL_ESTATE",
                    target_weight=Decimal("100.0001"),
                    effective_from=date(2026, 1, 1),
                )
                session.add(alloc_over)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_effective_dates_validation():
    """Verify effective_to can be null, >= effective_from, and rejects effective_to < effective_from."""
    TargetAllocation = _import_target_allocation()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisites(session)

            # Null effective_to is allowed (open-ended allocation)
            alloc_open = TargetAllocation(
                portfolio_id="PORT-TA-01",
                asset_class="EQUITY",
                target_weight=Decimal("60.0000"),
                effective_from=date(2026, 1, 1),
                effective_to=None,
            )
            session.add(alloc_open)

            # effective_to == effective_from is allowed (single day period)
            alloc_same_day = TargetAllocation(
                portfolio_id="PORT-TA-01",
                asset_class="FIXED_INCOME",
                target_weight=Decimal("30.0000"),
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 1, 1),
            )
            session.add(alloc_same_day)

            # effective_to > effective_from is allowed
            alloc_range = TargetAllocation(
                portfolio_id="PORT-TA-01",
                asset_class="CASH",
                target_weight=Decimal("10.0000"),
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 31),
            )
            session.add(alloc_range)
            session.commit()

            # effective_to < effective_from must be rejected by check constraint
            with pytest.raises(IntegrityError):
                alloc_invalid_dates = TargetAllocation(
                    portfolio_id="PORT-TA-01",
                    asset_class="COMMODITY",
                    target_weight=Decimal("5.0000"),
                    effective_from=date(2026, 6, 1),
                    effective_to=date(2026, 5, 31),
                )
                session.add(alloc_invalid_dates)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_composite_unique_constraint():
    """Verify UNIQUE (portfolio_id, asset_class, effective_from)."""
    TargetAllocation = _import_target_allocation()
    table = TargetAllocation.__table__

    expected_cols = {"portfolio_id", "asset_class", "effective_from"}
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
        "TargetAllocation must have UniqueConstraint on (portfolio_id, asset_class, effective_from)"
    )


def test_model_registered_in_metadata():
    """Verify target_allocation table is registered in Base.metadata."""
    _import_target_allocation()
    assert "target_allocation" in Base.metadata.tables, (
        "'target_allocation' table must be registered in Base.metadata"
    )


# ==============================================================================
# SQLite In-Memory CRUD & FK Tests
# ==============================================================================


def test_valid_insert_and_retrieval_sqlite():
    """Verify valid TargetAllocation can be inserted and retrieved with SQLite."""
    TargetAllocation = _import_target_allocation()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisites(session)

            alloc = TargetAllocation(
                portfolio_id="PORT-TA-01",
                asset_class="EQUITY",
                target_weight=Decimal("70.0000"),
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 31),
            )
            session.add(alloc)
            session.commit()

            retrieved = session.scalar(
                select(TargetAllocation).where(
                    TargetAllocation.portfolio_id == "PORT-TA-01",
                    TargetAllocation.asset_class == "EQUITY",
                )
            )
            assert retrieved is not None, "Failed to retrieve inserted TargetAllocation"
            assert retrieved.id is not None
            assert retrieved.portfolio_id == "PORT-TA-01"
            assert retrieved.asset_class == "EQUITY"
            assert retrieved.target_weight == Decimal("70.0000")
            assert retrieved.effective_from == date(2026, 1, 1)
            assert retrieved.effective_to == date(2026, 12, 31)
    finally:
        engine.dispose()


def test_invalid_foreign_key_rejected():
    """Verify invalid foreign-key references are rejected."""
    TargetAllocation = _import_target_allocation()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisites(session)

            invalid_alloc = TargetAllocation(
                portfolio_id="NONEXISTENT-PORT",
                asset_class="EQUITY",
                target_weight=Decimal("50.0000"),
                effective_from=date(2026, 1, 1),
            )
            session.add(invalid_alloc)
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()


def test_duplicate_allocation_same_effective_from_rejected():
    """Verify duplicate record for same portfolio, asset class and effective_from is rejected."""
    TargetAllocation = _import_target_allocation()
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisites(session)

            a1 = TargetAllocation(
                portfolio_id="PORT-TA-01",
                asset_class="EQUITY",
                target_weight=Decimal("60.0000"),
                effective_from=date(2026, 1, 1),
            )
            session.add(a1)
            session.commit()

            # Duplicate (portfolio_id, asset_class, effective_from)
            a2 = TargetAllocation(
                portfolio_id="PORT-TA-01",
                asset_class="EQUITY",
                target_weight=Decimal("65.0000"),
                effective_from=date(2026, 1, 1),
            )
            session.add(a2)
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()

