"""Tests for SQLAlchemy RebalanceProposal entity.

Following Test-Driven Development (TDD), these tests define the specifications
and contracts for the RebalanceProposal model before implementation.
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy import (
    DateTime,
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
from app.models.investor_profile import InvestorProfile, RiskCategory
from app.models.portfolio import Portfolio, PortfolioStatus


def _import_rebalance_proposal_models():
    """Dynamically import RebalanceProposal and associated enums."""
    try:
        from app.models.rebalance_proposal import (
            ProposalStatus,
            RebalanceProposal,
            ReviewDecision,
        )
        return {
            "RebalanceProposal": RebalanceProposal,
            "ProposalStatus": ProposalStatus,
            "ReviewDecision": ReviewDecision,
        }
    except (ImportError, ModuleNotFoundError):
        from app.models import (
            ProposalStatus,
            RebalanceProposal,
            ReviewDecision,
        )
        return {
            "RebalanceProposal": RebalanceProposal,
            "ProposalStatus": ProposalStatus,
            "ReviewDecision": ReviewDecision,
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


def _setup_prerequisites(session: Session) -> Portfolio:
    """Create prerequisite InvestorProfile and Portfolio records."""
    investor = InvestorProfile(
        investor_id="INV-RP-01",
        name="Proposal Investor",
        risk_category=RiskCategory.MODERATE,
    )
    session.add(investor)
    session.flush()

    portfolio = Portfolio(
        portfolio_id="PORT-RP-01",
        investor_id="INV-RP-01",
        portfolio_name="Rebalance Target Portfolio",
        base_currency="USD",
        status=PortfolioStatus.ACTIVE,
    )
    session.add(portfolio)
    session.commit()
    return portfolio


# ==============================================================================
# Model Definition & Metadata Tests
# ==============================================================================


def test_rebalance_proposal_inherits_from_base():
    """Verify RebalanceProposal inherits from the shared declarative Base."""
    models = _import_rebalance_proposal_models()
    RebalanceProposal = models["RebalanceProposal"]
    assert issubclass(RebalanceProposal, Base), (
        "RebalanceProposal must inherit from app.models.base.Base"
    )


def test_table_name_is_rebalance_proposal():
    """Verify table name is exactly 'rebalance_proposal'."""
    models = _import_rebalance_proposal_models()
    assert models["RebalanceProposal"].__tablename__ == "rebalance_proposal"


def test_proposal_id_is_primary_key_varchar_30():
    """Verify proposal_id is String(30) primary key."""
    models = _import_rebalance_proposal_models()
    col = models["RebalanceProposal"].__table__.c.proposal_id

    assert col.primary_key is True, "proposal_id must be the primary key"
    assert isinstance(col.type, String), "proposal_id must be String"
    assert col.type.length == 30, "proposal_id must be String(30)"
    assert col.nullable is False, "Primary key proposal_id must not be nullable"


def test_portfolio_id_is_foreign_key_varchar_40():
    """Verify portfolio_id is a required foreign key referencing portfolio.portfolio_id."""
    models = _import_rebalance_proposal_models()
    col = models["RebalanceProposal"].__table__.c.portfolio_id

    assert col.nullable is False, "portfolio_id must not be nullable"
    assert isinstance(col.type, String), "portfolio_id must be String"
    assert col.type.length == 40, "portfolio_id must be String(40)"

    fk_targets = {fk.target_fullname for fk in col.foreign_keys}
    assert "portfolio.portfolio_id" in fk_targets, (
        "portfolio_id must have foreign key referencing portfolio.portfolio_id"
    )


def test_required_and_nullable_columns_and_types():
    """Verify column definitions, precision, scale, and nullability."""
    models = _import_rebalance_proposal_models()
    table = models["RebalanceProposal"].__table__

    # status: String(20), required
    status_col = table.c.status
    assert isinstance(status_col.type, String)
    assert status_col.type.length == 20
    assert status_col.nullable is False

    # review_decision: String(20), required
    rev_dec_col = table.c.review_decision
    assert isinstance(rev_dec_col.type, String)
    assert rev_dec_col.type.length == 20
    assert rev_dec_col.nullable is False

    # pre_trade_portfolio_value: Numeric(18, 4), nullable
    pre_col = table.c.pre_trade_portfolio_value
    assert isinstance(pre_col.type, Numeric)
    assert pre_col.type.precision == 18
    assert pre_col.type.scale == 4
    assert pre_col.nullable is True

    # post_trade_portfolio_value: Numeric(18, 4), nullable
    post_col = table.c.post_trade_portfolio_value
    assert isinstance(post_col.type, Numeric)
    assert post_col.type.precision == 18
    assert post_col.type.scale == 4
    assert post_col.nullable is True

    # created_at: DateTime(timezone=True), required, default
    created_col = table.c.created_at
    assert isinstance(created_col.type, DateTime)
    assert created_col.type.timezone is True
    assert created_col.nullable is False
    has_default = (created_col.default is not None) or (
        created_col.server_default is not None
    )
    assert has_default, "created_at must have a default"

    # reviewed_at: DateTime(timezone=True), nullable
    rev_at_col = table.c.reviewed_at
    assert isinstance(rev_at_col.type, DateTime)
    assert rev_at_col.type.timezone is True
    assert rev_at_col.nullable is True

    # review_reason: Text, nullable
    reason_col = table.c.review_reason
    assert isinstance(reason_col.type, Text)
    assert reason_col.nullable is True


# ==============================================================================
# Database Constraint Validation Tests
# ==============================================================================


def test_status_check_constraint():
    """Verify status allows DRAFT, PENDING_REVIEW, APPROVED, REJECTED and rejects others."""
    models = _import_rebalance_proposal_models()
    RebalanceProposal = models["RebalanceProposal"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisites(session)
            valid_statuses = ["DRAFT", "PENDING_REVIEW", "APPROVED", "REJECTED"]
            for idx, st in enumerate(valid_statuses):
                p = RebalanceProposal(
                    proposal_id=f"RB-2026-{idx + 1:06d}",
                    portfolio_id="PORT-RP-01",
                    status=st,
                    review_decision="PENDING",
                )
                session.add(p)
            session.commit()

            # Invalid status rejected
            with pytest.raises(IntegrityError):
                invalid_p = RebalanceProposal(
                    proposal_id="RB-2026-999999",
                    portfolio_id="PORT-RP-01",
                    status="COMPLETED",
                    review_decision="PENDING",
                )
                session.add(invalid_p)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_review_decision_check_constraint():
    """Verify review_decision allows PENDING, APPROVED, REJECTED and rejects others."""
    models = _import_rebalance_proposal_models()
    RebalanceProposal = models["RebalanceProposal"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisites(session)
            valid_decisions = ["PENDING", "APPROVED", "REJECTED"]
            for idx, dec in enumerate(valid_decisions):
                p = RebalanceProposal(
                    proposal_id=f"RB-DEC-{idx + 1:04d}",
                    portfolio_id="PORT-RP-01",
                    status="DRAFT",
                    review_decision=dec,
                )
                session.add(p)
            session.commit()

            # Invalid review_decision rejected
            with pytest.raises(IntegrityError):
                invalid_dec = RebalanceProposal(
                    proposal_id="RB-DEC-INV",
                    portfolio_id="PORT-RP-01",
                    status="DRAFT",
                    review_decision="DISMISSED",
                )
                session.add(invalid_dec)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_portfolio_values_nonnegative_check_constraint():
    """Verify pre_trade_portfolio_value and post_trade_portfolio_value reject negative amounts."""
    models = _import_rebalance_proposal_models()
    RebalanceProposal = models["RebalanceProposal"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisites(session)

            # Null values are permitted
            p_null = RebalanceProposal(
                proposal_id="RB-VAL-NULL",
                portfolio_id="PORT-RP-01",
                status="DRAFT",
                review_decision="PENDING",
                pre_trade_portfolio_value=None,
                post_trade_portfolio_value=None,
            )
            # Zero values are permitted
            p_zero = RebalanceProposal(
                proposal_id="RB-VAL-ZERO",
                portfolio_id="PORT-RP-01",
                status="DRAFT",
                review_decision="PENDING",
                pre_trade_portfolio_value=Decimal("0.0000"),
                post_trade_portfolio_value=Decimal("0.0000"),
            )
            session.add_all([p_null, p_zero])
            session.commit()

            # Negative pre_trade_portfolio_value rejected
            with pytest.raises(IntegrityError):
                p_neg_pre = RebalanceProposal(
                    proposal_id="RB-VAL-NEG-PRE",
                    portfolio_id="PORT-RP-01",
                    status="DRAFT",
                    review_decision="PENDING",
                    pre_trade_portfolio_value=Decimal("-0.0001"),
                )
                session.add(p_neg_pre)
                session.commit()
            session.rollback()

            # Negative post_trade_portfolio_value rejected
            with pytest.raises(IntegrityError):
                p_neg_post = RebalanceProposal(
                    proposal_id="RB-VAL-NEG-POST",
                    portfolio_id="PORT-RP-01",
                    status="DRAFT",
                    review_decision="PENDING",
                    post_trade_portfolio_value=Decimal("-10.0000"),
                )
                session.add(p_neg_post)
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_model_registered_in_metadata():
    """Verify rebalance_proposal table is registered in Base.metadata."""
    _import_rebalance_proposal_models()
    assert "rebalance_proposal" in Base.metadata.tables


# ==============================================================================
# SQLite In-Memory CRUD & Relationship Tests
# ==============================================================================


def test_rebalance_proposal_sqlite_insert_and_retrieval():
    """Verify valid RebalanceProposal insertion and retrieval with SQLite."""
    models = _import_rebalance_proposal_models()
    RebalanceProposal = models["RebalanceProposal"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisites(session)

            now_utc = datetime.now(timezone.utc)
            p = RebalanceProposal(
                proposal_id="RB-2026-000001",
                portfolio_id="PORT-RP-01",
                status="PENDING_REVIEW",
                review_decision="PENDING",
                pre_trade_portfolio_value=Decimal("100000.0000"),
                post_trade_portfolio_value=Decimal("100050.0000"),
                reviewed_at=now_utc,
                review_reason="Quarterly drift realignment.",
            )
            session.add(p)
            session.commit()

            retrieved = session.scalar(
                select(RebalanceProposal).where(
                    RebalanceProposal.proposal_id == "RB-2026-000001"
                )
            )
            assert retrieved is not None
            assert retrieved.proposal_id == "RB-2026-000001"
            assert retrieved.portfolio_id == "PORT-RP-01"
            assert retrieved.status == "PENDING_REVIEW"
            assert retrieved.review_decision == "PENDING"
            assert retrieved.pre_trade_portfolio_value == Decimal("100000.0000")
            assert retrieved.post_trade_portfolio_value == Decimal("100050.0000")
            assert retrieved.created_at is not None
            assert retrieved.reviewed_at is not None
            assert retrieved.review_reason == "Quarterly drift realignment."
    finally:
        engine.dispose()


def test_invalid_foreign_key_rejected_sqlite():
    """Verify invalid portfolio_id raises IntegrityError with SQLite FK enforcement."""
    models = _import_rebalance_proposal_models()
    RebalanceProposal = models["RebalanceProposal"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            _setup_prerequisites(session)

            invalid_p = RebalanceProposal(
                proposal_id="RB-BAD-PORT-01",
                portfolio_id="NONEXISTENT-PORT",
                status="DRAFT",
                review_decision="PENDING",
            )
            session.add(invalid_p)
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()


def test_relationship_to_portfolio():
    """Verify bi-directional navigation between Portfolio and RebalanceProposal."""
    models = _import_rebalance_proposal_models()
    RebalanceProposal = models["RebalanceProposal"]
    engine = _create_sqlite_engine()
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            portfolio = _setup_prerequisites(session)

            p = RebalanceProposal(
                proposal_id="RB-REL-01",
                portfolio_id=portfolio.portfolio_id,
                status="DRAFT",
                review_decision="PENDING",
            )
            session.add(p)
            session.commit()

            # Proposal -> portfolio
            reloaded_p = session.scalar(
                select(RebalanceProposal).where(
                    RebalanceProposal.proposal_id == "RB-REL-01"
                )
            )
            assert reloaded_p is not None
            assert reloaded_p.portfolio.portfolio_id == portfolio.portfolio_id

            # Portfolio -> proposals
            reloaded_port = session.scalar(
                select(Portfolio).where(
                    Portfolio.portfolio_id == portfolio.portfolio_id
                )
            )
            assert hasattr(reloaded_port, "proposals"), (
                "Portfolio must expose 'proposals' relationship"
            )
            assert any(prop.proposal_id == "RB-REL-01" for prop in reloaded_port.proposals)
    finally:
        engine.dispose()

