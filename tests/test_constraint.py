"""Tests for SQLAlchemy Constraint and ConstraintInstrument entities.

Following Test-Driven Development (TDD), these tests define the specifications
and contracts for Constraint and ConstraintInstrument before implementation.
"""

from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import (
    Boolean,
    Date,
    Numeric,
    String,
    Text,
    create_engine,
    event,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.instrument import Instrument
from app.models.investor_profile import InvestorProfile, RiskCategory
from app.models.portfolio import Portfolio, PortfolioStatus


def _import_constraint_models():
    """Dynamically import Constraint, ConstraintInstrument, and associated enums/helpers."""
    try:
        from app.models.constraint import (
            Constraint,
            ConstraintSeverity,
            ConstraintType,
            ScopeType,
            validate_scope_reference,
        )
    except (ImportError, ModuleNotFoundError):
        from app.models import (
            Constraint,
            ConstraintSeverity,
            ConstraintType,
            ScopeType,
            validate_scope_reference,
        )

    try:
        from app.models.constraint_instrument import ConstraintInstrument
    except (ImportError, ModuleNotFoundError):
        from app.models import ConstraintInstrument

    return {
        "Constraint": Constraint,
        "ConstraintInstrument": ConstraintInstrument,
        "ConstraintType": ConstraintType,
        "ScopeType": ScopeType,
        "ConstraintSeverity": ConstraintSeverity,
        "validate_scope_reference": validate_scope_reference,
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
    """Seed test investor, portfolio, and instruments."""
    investor = InvestorProfile(
        investor_id="INV-CONST-01",
        name="Constraint Test Investor",
        risk_category=RiskCategory.MODERATE,
    )
    session.add(investor)
    session.flush()

    portfolio = Portfolio(
        portfolio_id="PORT-CONST-01",
        investor_id="INV-CONST-01",
        portfolio_name="Constraint Portfolio",
        base_currency="USD",
        status=PortfolioStatus.ACTIVE,
    )
    session.add(portfolio)

    inst1 = Instrument(
        instrument_id="INST-CONST-01",
        symbol="AAPL",
        instrument_name="Apple Inc.",
        asset_class="EQUITY",
        lot_size=Decimal("1.0000"),
        is_active=True,
    )
    inst2 = Instrument(
        instrument_id="INST-CONST-02",
        symbol="MSFT",
        instrument_name="Microsoft Corp.",
        asset_class="EQUITY",
        lot_size=Decimal("1.0000"),
        is_active=True,
    )
    session.add_all([inst1, inst2])
    session.commit()
    return portfolio, inst1, inst2


# ==============================================================================
# Model Definition & Metadata Tests
# ==============================================================================


def test_constraint_inherits_from_base():
    """Verify Constraint inherits from the shared declarative Base."""
    models = _import_constraint_models()
    Constraint = models["Constraint"]
    assert issubclass(Constraint, Base), "Constraint must inherit from Base"


def test_constraint_instrument_inherits_from_base():
    """Verify ConstraintInstrument inherits from the shared declarative Base."""
    models = _import_constraint_models()
    ConstraintInstrument = models["ConstraintInstrument"]
    assert issubclass(ConstraintInstrument, Base), (
        "ConstraintInstrument must inherit from Base"
    )


def test_table_names():
    """Verify table names are 'constraint' and 'constraint_instrument'."""
    models = _import_constraint_models()
    assert models["Constraint"].__tablename__ == "constraint"
    assert models["ConstraintInstrument"].__tablename__ == "constraint_instrument"


def test_constraint_primary_key_and_column_types():
    """Verify column definitions, types, precision/scale, and nullability for Constraint."""
    models = _import_constraint_models()
    table = models["Constraint"].__table__

    # constraint_id: String(30), PK
    cid_col = table.c.constraint_id
    assert cid_col.primary_key is True, "constraint_id must be primary key"
    assert isinstance(cid_col.type, String)
    assert cid_col.type.length == 30
    assert cid_col.nullable is False

    # constraint_name: String(100), required
    cname_col = table.c.constraint_name
    assert isinstance(cname_col.type, String)
    assert cname_col.type.length == 100
    assert cname_col.nullable is False

    # constraint_type: String(50), required
    ctype_col = table.c.constraint_type
    assert isinstance(ctype_col.type, String)
    assert ctype_col.type.length == 50
    assert ctype_col.nullable is False

    # scope_type: String(20), required
    stype_col = table.c.scope_type
    assert isinstance(stype_col.type, String)
    assert stype_col.type.length == 20
    assert stype_col.nullable is False

    # scope_reference_id: String(50), required, polymorphic (no plain FK)
    sref_col = table.c.scope_reference_id
    assert isinstance(sref_col.type, String)
    assert sref_col.type.length == 50
    assert sref_col.nullable is False
    assert len(sref_col.foreign_keys) == 0, (
        "scope_reference_id is polymorphic; must not have a direct foreign key"
    )

    # severity: String(10), required
    sev_col = table.c.severity
    assert isinstance(sev_col.type, String)
    assert sev_col.type.length == 10
    assert sev_col.nullable is False

    # threshold_value: Numeric(18, 4), nullable
    tval_col = table.c.threshold_value
    assert isinstance(tval_col.type, Numeric)
    assert tval_col.type.precision == 18
    assert tval_col.type.scale == 4
    assert tval_col.nullable is True

    # threshold_unit: String(20), nullable
    tunit_col = table.c.threshold_unit
    assert isinstance(tunit_col.type, String)
    assert tunit_col.type.length == 20
    assert tunit_col.nullable is True

    # effective_from: Date, required
    ef_col = table.c.effective_from
    assert isinstance(ef_col.type, Date)
    assert ef_col.nullable is False

    # effective_to: Date, nullable
    et_col = table.c.effective_to
    assert isinstance(et_col.type, Date)
    assert et_col.nullable is True

    # is_active: Boolean, required, with default
    active_col = table.c.is_active
    assert isinstance(active_col.type, Boolean)
    assert active_col.nullable is False
    has_default = (active_col.default is not None) or (
        active_col.server_default is not None
    )
    assert has_default, "is_active must have a default"

    # description: Text, nullable
    desc_col = table.c.description
    assert isinstance(desc_col.type, Text)
    assert desc_col.nullable is True


def test_constraint_instrument_composite_primary_key_and_types():
    """Verify ConstraintInstrument has composite primary key and foreign keys."""
    models = _import_constraint_models()
    table = models["ConstraintInstrument"].__table__

    # Composite primary key
    pk_cols = {col.name for col in table.primary_key.columns}
    assert pk_cols == {"constraint_id", "instrument_id"}, (
        "ConstraintInstrument must have composite PK (constraint_id, instrument_id)"
    )

    # constraint_id: String(30), FK to constraint.constraint_id
    cid_col = table.c.constraint_id
    assert isinstance(cid_col.type, String)
    assert cid_col.type.length == 30
    cid_fks = {fk.target_fullname for fk in cid_col.foreign_keys}
    assert "constraint.constraint_id" in cid_fks

    # instrument_id: String(20), FK to instrument.instrument_id
    iid_col = table.c.instrument_id
    assert isinstance(iid_col.type, String)
    assert iid_col.type.length == 20
    iid_fks = {fk.target_fullname for fk in iid_col.foreign_keys}
    assert "instrument.instrument_id" in iid_fks


# ==============================================================================
# Constraint CHECK Validation Tests
# ==============================================================================


def test_scope_type_check_constraint():
    """Verify scope_type allows PORTFOLIO, ASSET_CLASS, INSTRUMENT, and rejects others."""
    models = _import_constraint_models()
    Constraint = models["Constraint"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            for valid_scope in ["PORTFOLIO", "ASSET_CLASS", "INSTRUMENT"]:
                c = Constraint(
                    constraint_id=f"C-SCOPE-{valid_scope}",
                    constraint_name=f"Test {valid_scope}",
                    constraint_type="MAX_POSITION_WEIGHT",
                    scope_type=valid_scope,
                    scope_reference_id="REF-1",
                    severity="HARD",
                    effective_from=date(2026, 1, 1),
                )
                session.add(c)
            session.commit()

            with pytest.raises(IntegrityError):
                invalid_c = Constraint(
                    constraint_id="C-SCOPE-INV",
                    constraint_name="Invalid Scope",
                    constraint_type="MAX_POSITION_WEIGHT",
                    scope_type="GLOBAL",
                    scope_reference_id="REF-INV",
                    severity="HARD",
                    effective_from=date(2026, 1, 1),
                )
                session.add(invalid_c)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_severity_check_constraint():
    """Verify severity allows HARD and SOFT, and rejects other values."""
    models = _import_constraint_models()
    Constraint = models["Constraint"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            for valid_sev in ["HARD", "SOFT"]:
                c = Constraint(
                    constraint_id=f"C-SEV-{valid_sev}",
                    constraint_name=f"Test {valid_sev}",
                    constraint_type="MAX_POSITION_WEIGHT",
                    scope_type="PORTFOLIO",
                    scope_reference_id="PORT-1",
                    severity=valid_sev,
                    effective_from=date(2026, 1, 1),
                )
                session.add(c)
            session.commit()

            with pytest.raises(IntegrityError):
                invalid_sev = Constraint(
                    constraint_id="C-SEV-INV",
                    constraint_name="Invalid Severity",
                    constraint_type="MAX_POSITION_WEIGHT",
                    scope_type="PORTFOLIO",
                    scope_reference_id="PORT-1",
                    severity="MEDIUM",
                    effective_from=date(2026, 1, 1),
                )
                session.add(invalid_sev)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_effective_dates_check_constraint():
    """Verify effective date range must be valid: effective_to IS NULL OR >= effective_from."""
    models = _import_constraint_models()
    Constraint = models["Constraint"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            # Open-ended
            c1 = Constraint(
                constraint_id="C-DATE-OPEN",
                constraint_name="Open Ended",
                constraint_type="MAX_POSITION_WEIGHT",
                scope_type="PORTFOLIO",
                scope_reference_id="PORT-1",
                severity="HARD",
                effective_from=date(2026, 1, 1),
                effective_to=None,
            )
            # Same day
            c2 = Constraint(
                constraint_id="C-DATE-SAME",
                constraint_name="Same Day",
                constraint_type="MAX_POSITION_WEIGHT",
                scope_type="PORTFOLIO",
                scope_reference_id="PORT-1",
                severity="HARD",
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 1, 1),
            )
            session.add_all([c1, c2])
            session.commit()

            # Invalid: effective_to < effective_from
            with pytest.raises(IntegrityError):
                c_inv = Constraint(
                    constraint_id="C-DATE-INV",
                    constraint_name="Inverted Dates",
                    constraint_type="MAX_POSITION_WEIGHT",
                    scope_type="PORTFOLIO",
                    scope_reference_id="PORT-1",
                    severity="HARD",
                    effective_from=date(2026, 6, 1),
                    effective_to=date(2026, 5, 31),
                )
                session.add(c_inv)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_threshold_value_check_constraint():
    """Verify threshold_value must be nonnegative when supplied."""
    models = _import_constraint_models()
    Constraint = models["Constraint"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            # NULL threshold is allowed (e.g. EXCLUDED_INSTRUMENT)
            c_null = Constraint(
                constraint_id="C-THRESH-NULL",
                constraint_name="Null Threshold",
                constraint_type="EXCLUDED_INSTRUMENT",
                scope_type="INSTRUMENT",
                scope_reference_id="INST-1",
                severity="HARD",
                threshold_value=None,
                effective_from=date(2026, 1, 1),
            )
            # Zero threshold is allowed
            c_zero = Constraint(
                constraint_id="C-THRESH-ZERO",
                constraint_name="Zero Threshold",
                constraint_type="MIN_TRADE_VALUE",
                scope_type="PORTFOLIO",
                scope_reference_id="PORT-1",
                severity="SOFT",
                threshold_value=Decimal("0.0000"),
                effective_from=date(2026, 1, 1),
            )
            # Positive threshold is allowed
            c_pos = Constraint(
                constraint_id="C-THRESH-POS",
                constraint_name="Positive Threshold",
                constraint_type="MAX_POSITION_WEIGHT",
                scope_type="PORTFOLIO",
                scope_reference_id="PORT-1",
                severity="HARD",
                threshold_value=Decimal("20.0000"),
                threshold_unit="PERCENT",
                effective_from=date(2026, 1, 1),
            )
            session.add_all([c_null, c_zero, c_pos])
            session.commit()

            # Negative threshold rejected
            with pytest.raises(IntegrityError):
                c_neg = Constraint(
                    constraint_id="C-THRESH-NEG",
                    constraint_name="Negative Threshold",
                    constraint_type="MAX_POSITION_WEIGHT",
                    scope_type="PORTFOLIO",
                    scope_reference_id="PORT-1",
                    severity="HARD",
                    threshold_value=Decimal("-0.0001"),
                    effective_from=date(2026, 1, 1),
                )
                session.add(c_neg)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_constraint_type_check_constraint():
    """Verify supported constraint_type values are accepted and unsupported rejected."""
    models = _import_constraint_models()
    Constraint = models["Constraint"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            supported = [
                "MAX_POSITION_WEIGHT",
                "MIN_TRADE_VALUE",
                "MIN_TRADE_QUANTITY",
                "EXCLUDED_INSTRUMENT",
                "LIQUIDITY_LIMIT",
            ]
            for ctype in supported:
                c = Constraint(
                    constraint_id=f"C-TYPE-{ctype}",
                    constraint_name=f"Test {ctype}",
                    constraint_type=ctype,
                    scope_type="PORTFOLIO",
                    scope_reference_id="PORT-1",
                    severity="HARD",
                    effective_from=date(2026, 1, 1),
                )
                session.add(c)
            session.commit()

            with pytest.raises(IntegrityError):
                c_unsupported = Constraint(
                    constraint_id="C-TYPE-INV",
                    constraint_name="Unsupported Type",
                    constraint_type="RANDOM_CUSTOM_RULE",
                    scope_type="PORTFOLIO",
                    scope_reference_id="PORT-1",
                    severity="HARD",
                    effective_from=date(2026, 1, 1),
                )
                session.add(c_unsupported)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_models_registered_in_metadata():
    """Verify constraint and constraint_instrument tables are registered in Base.metadata."""
    _import_constraint_models()
    assert "constraint" in Base.metadata.tables
    assert "constraint_instrument" in Base.metadata.tables


# ==============================================================================
# SQLite In-Memory CRUD & Relationship Tests
# ==============================================================================


def test_constraint_sqlite_insert_and_retrieval():
    """Verify valid Constraint insertion and retrieval with SQLite."""
    models = _import_constraint_models()
    Constraint = models["Constraint"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            c = Constraint(
                constraint_id="CONST-POS-LIMIT-01",
                constraint_name="Max Equity Position 15%",
                constraint_type="MAX_POSITION_WEIGHT",
                scope_type="PORTFOLIO",
                scope_reference_id="PORT-CONST-01",
                severity="HARD",
                threshold_value=Decimal("15.0000"),
                threshold_unit="PERCENT",
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 31),
                is_active=True,
                description="Limits any single position to 15% of portfolio total value.",
            )
            session.add(c)
            session.commit()

            retrieved = session.scalar(
                select(Constraint).where(
                    Constraint.constraint_id == "CONST-POS-LIMIT-01"
                )
            )
            assert retrieved is not None
            assert retrieved.constraint_name == "Max Equity Position 15%"
            assert retrieved.constraint_type == "MAX_POSITION_WEIGHT"
            assert retrieved.scope_type == "PORTFOLIO"
            assert retrieved.scope_reference_id == "PORT-CONST-01"
            assert retrieved.severity == "HARD"
            assert retrieved.threshold_value == Decimal("15.0000")
            assert retrieved.threshold_unit == "PERCENT"
            assert retrieved.effective_from == date(2026, 1, 1)
            assert retrieved.effective_to == date(2026, 12, 31)
            assert retrieved.is_active is True
            assert (
                retrieved.description
                == "Limits any single position to 15% of portfolio total value."
            )
    finally:
        engine.dispose()


def test_bridge_foreign_keys_enforced_sqlite():
    """Verify SQLite foreign key enforcement on ConstraintInstrument."""
    models = _import_constraint_models()
    Constraint = models["Constraint"]
    ConstraintInstrument = models["ConstraintInstrument"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _, inst1, _ = _setup_prerequisites(session)

            c = Constraint(
                constraint_id="C-BRIDGE-FK",
                constraint_name="Bridge Test",
                constraint_type="EXCLUDED_INSTRUMENT",
                scope_type="INSTRUMENT",
                scope_reference_id=inst1.instrument_id,
                severity="HARD",
                effective_from=date(2026, 1, 1),
            )
            session.add(c)
            session.commit()

            # Invalid constraint_id
            with pytest.raises(IntegrityError):
                bad_cid = ConstraintInstrument(
                    constraint_id="NONEXISTENT-C",
                    instrument_id=inst1.instrument_id,
                )
                session.add(bad_cid)
                session.commit()
            session.rollback()

            # Invalid instrument_id
            with pytest.raises(IntegrityError):
                bad_iid = ConstraintInstrument(
                    constraint_id="C-BRIDGE-FK",
                    instrument_id="NONEXISTENT-INST",
                )
                session.add(bad_iid)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_bridge_duplicate_association_rejected():
    """Verify duplicate (constraint_id, instrument_id) is rejected by composite PK."""
    models = _import_constraint_models()
    Constraint = models["Constraint"]
    ConstraintInstrument = models["ConstraintInstrument"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _, inst1, _ = _setup_prerequisites(session)
            inst_id = inst1.instrument_id

            c = Constraint(
                constraint_id="C-DUP-BRIDGE",
                constraint_name="Bridge Dup Test",
                constraint_type="EXCLUDED_INSTRUMENT",
                scope_type="INSTRUMENT",
                scope_reference_id=inst_id,
                severity="HARD",
                effective_from=date(2026, 1, 1),
            )
            session.add(c)
            session.commit()

            b1 = ConstraintInstrument(
                constraint_id="C-DUP-BRIDGE",
                instrument_id=inst_id,
            )
            session.add(b1)
            session.commit()

        # In a separate session to test database composite PK rejection without identity map collision
        with Session(engine) as session2:
            b2 = ConstraintInstrument(
                constraint_id="C-DUP-BRIDGE",
                instrument_id=inst_id,
            )
            session2.add(b2)
            with pytest.raises(IntegrityError):
                session2.commit()
    finally:
        engine.dispose()


def test_many_to_many_relationship_loading():
    """Verify many-to-many relationship navigation between Constraint and Instrument."""
    models = _import_constraint_models()
    Constraint = models["Constraint"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _, inst1, inst2 = _setup_prerequisites(session)

            c = Constraint(
                constraint_id="C-M2M-01",
                constraint_name="Restricted Tech Stocks",
                constraint_type="EXCLUDED_INSTRUMENT",
                scope_type="INSTRUMENT",
                scope_reference_id="TECH-GROUP",
                severity="HARD",
                effective_from=date(2026, 1, 1),
            )
            # Associate through relationship
            c.instruments.extend([inst1, inst2])
            session.add(c)
            session.commit()

            # Reload and check Constraint -> instruments
            reloaded_c = session.scalar(
                select(Constraint).where(Constraint.constraint_id == "C-M2M-01")
            )
            assert reloaded_c is not None
            assert len(reloaded_c.instruments) == 2
            inst_ids = {inst.instrument_id for inst in reloaded_c.instruments}
            assert inst_ids == {inst1.instrument_id, inst2.instrument_id}

            # Check Instrument -> constraints reverse navigation
            reloaded_inst1 = session.scalar(
                select(Instrument).where(
                    Instrument.instrument_id == inst1.instrument_id
                )
            )
            assert hasattr(reloaded_inst1, "constraints"), (
                "Instrument should expose reverse 'constraints' relationship"
            )
            assert any(
                cn.constraint_id == "C-M2M-01" for cn in reloaded_inst1.constraints
            )
    finally:
        engine.dispose()


def test_scope_reference_validation_helper():
    """Verify scope_reference_id validation helper correctly verifies polymorphic targets."""
    models = _import_constraint_models()
    validate_scope = models["validate_scope_reference"]
    ScopeType = models["ScopeType"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            portfolio, inst1, _ = _setup_prerequisites(session)

            # Valid PORTFOLIO scope reference
            assert validate_scope(
                scope_type=ScopeType.PORTFOLIO if ScopeType else "PORTFOLIO",
                scope_reference_id=portfolio.portfolio_id,
                session=session,
            ) is True

            # Invalid PORTFOLIO scope reference
            assert validate_scope(
                scope_type=ScopeType.PORTFOLIO if ScopeType else "PORTFOLIO",
                scope_reference_id="NONEXISTENT-PORT",
                session=session,
            ) is False

            # Valid INSTRUMENT scope reference
            assert validate_scope(
                scope_type=ScopeType.INSTRUMENT if ScopeType else "INSTRUMENT",
                scope_reference_id=inst1.instrument_id,
                session=session,
            ) is True

            # Invalid INSTRUMENT scope reference
            assert validate_scope(
                scope_type=ScopeType.INSTRUMENT if ScopeType else "INSTRUMENT",
                scope_reference_id="NONEXISTENT-INST",
                session=session,
            ) is False

            # Valid ASSET_CLASS scope reference (non-empty string identifier)
            assert validate_scope(
                scope_type=ScopeType.ASSET_CLASS if ScopeType else "ASSET_CLASS",
                scope_reference_id="EQUITY",
                session=session,
            ) is True

            # Invalid empty ASSET_CLASS scope reference
            assert validate_scope(
                scope_type=ScopeType.ASSET_CLASS if ScopeType else "ASSET_CLASS",
                scope_reference_id="",
                session=session,
            ) is False
    finally:
        engine.dispose()
