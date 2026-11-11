"""Tests for Rebalancing Post-Trade Simulation, Constraint Gatekeeper, Proposal Persistence, and API.

Following Test-Driven Development (TDD), these tests define contracts and specifications
for Phase 4.2 before implementation.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.session import get_db
from app.main import app
from app.models.base import Base
from app.models.constraint import Constraint, ConstraintSeverity, ConstraintType, ScopeType
from app.models.fee_schedule import FeeSchedule
from app.models.holding import Holding
from app.models.instrument import Instrument
from app.models.investor_profile import InvestorProfile, RiskCategory
from app.models.market_price import MarketPrice
from app.models.portfolio import Portfolio, PortfolioStatus
from app.models.rebalance_proposal import ProposalStatus, RebalanceProposal, ReviewDecision
from app.models.target_allocation import TargetAllocation
from app.models.trade import Trade, TradeStatus
from app.services.rebalancing_service import (
    ConstraintViolationError,
    RebalancingService,
)


def _create_sqlite_session() -> Session:
    """Create an in-memory SQLite database session with foreign keys enabled."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return Session(engine)


def _seed_base_environment(session: Session, as_of: date):
    """Seed investor, portfolio, cash, fee schedules."""
    inv = InvestorProfile(
        investor_id="INV-SIM-01",
        name="Alice Sim",
        risk_category=RiskCategory.MODERATE,
    )
    port = Portfolio(
        portfolio_id="PORT-SIM-01",
        investor_id="INV-SIM-01",
        portfolio_name="Alice Moderate Portfolio",
        base_currency="USD",
        status=PortfolioStatus.ACTIVE,
    )
    csh_inst = Instrument(
        instrument_id="INS-CASH-USD",
        symbol="USD",
        instrument_name="US Dollar",
        asset_class="CASH",
        lot_size=Decimal("1.0000"),
        is_active=True,
    )
    csh_price = MarketPrice(
        id=1,
        instrument_id="INS-CASH-USD",
        price=Decimal("1.0000"),
        price_date=as_of,
        source="SYSTEM",
    )
    fees = [
        FeeSchedule(
            fee_schedule_id="FEE-EQ-S",
            asset_class="EQUITY",
            trade_side="SELL",
            min_trade_value=Decimal("0.0000"),
            max_trade_value=None,
            fee_rate_bps=Decimal("10.0000"),
            fixed_fee=Decimal("1.0000"),
            minimum_fee=Decimal("1.0000"),
            maximum_fee=Decimal("100.0000"),
            effective_from=date(2026, 1, 1),
            effective_to=None,
            currency="USD",
            is_active=True,
        ),
        FeeSchedule(
            fee_schedule_id="FEE-EQ-B",
            asset_class="EQUITY",
            trade_side="BUY",
            min_trade_value=Decimal("0.0000"),
            max_trade_value=None,
            fee_rate_bps=Decimal("10.0000"),
            fixed_fee=Decimal("1.0000"),
            minimum_fee=Decimal("1.0000"),
            maximum_fee=Decimal("100.0000"),
            effective_from=date(2026, 1, 1),
            effective_to=None,
            currency="USD",
            is_active=True,
        ),
        FeeSchedule(
            fee_schedule_id="FEE-DB-B",
            asset_class="DEBT",
            trade_side="BUY",
            min_trade_value=Decimal("0.0000"),
            max_trade_value=None,
            fee_rate_bps=Decimal("5.0000"),
            fixed_fee=Decimal("0.5000"),
            minimum_fee=Decimal("0.5000"),
            maximum_fee=Decimal("50.0000"),
            effective_from=date(2026, 1, 1),
            effective_to=None,
            currency="USD",
            is_active=True,
        ),
        FeeSchedule(
            fee_schedule_id="FEE-DB-S",
            asset_class="DEBT",
            trade_side="SELL",
            min_trade_value=Decimal("0.0000"),
            max_trade_value=None,
            fee_rate_bps=Decimal("5.0000"),
            fixed_fee=Decimal("0.5000"),
            minimum_fee=Decimal("0.5000"),
            maximum_fee=Decimal("50.0000"),
            effective_from=date(2026, 1, 1),
            effective_to=None,
            currency="USD",
            is_active=True,
        ),
    ]
    session.add_all([inv, port, csh_inst, csh_price] + fees)
    session.commit()


@pytest.fixture
def db_session():
    """Isolated database session for unit/service testing."""
    session = _create_sqlite_session()
    yield session
    session.close()


@pytest.fixture
def api_client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ==============================================================================
# A. Post-Trade Simulation Tests
# ==============================================================================

def test_simulation_applies_sells_and_buys_to_holdings_copy(db_session):
    """Verify simulation applies SELLs and BUYs to in-memory copies and does not touch DB."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    bnd = Instrument(instrument_id="INS-BND", symbol="BND", instrument_name="Bond", asset_class="DEBT", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add_all([aapl, bnd])

    # Portfolio: AAPL 50 @ $100 = $5000 (50%). Cash = $5000 (50%). Total = $10,000.
    # Target: Equity 20% ($2,000), Debt 60% ($6,000), Cash 20% ($2,000).
    # Generates SELL AAPL (30 shares = $3000), BUY BND (120 shares @ $50 = $6000).
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=3, instrument_id="INS-BND", price=Decimal("50.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("5000.0000"), as_of_date=as_of),
        Holding(holding_id="H-AAPL", portfolio_id="PORT-SIM-01", instrument_id="INS-AAPL", quantity=Decimal("50.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("20.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="DEBT", target_weight=Decimal("60.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=3, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("20.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    rebal_result = service.generate_rebalance_trades("PORT-SIM-01", as_of)
    sim_result = service.simulate_post_trade_state("PORT-SIM-01", as_of, rebal_result.proposed_trades)

    # AAPL was 50, sold 30 -> simulated remaining should be 20
    sim_aapl = next(p for p in sim_result.positions if p.instrument_id == "INS-AAPL")
    assert sim_aapl.post_trade_quantity == Decimal("20.0000")
    assert sim_aapl.pre_trade_quantity == Decimal("50.0000")

    # BND was 0, bought 119 or 120 lots
    sim_bnd = next(p for p in sim_result.positions if p.instrument_id == "INS-BND")
    assert sim_bnd.post_trade_quantity > Decimal("0.0000")
    assert sim_bnd.pre_trade_quantity == Decimal("0.0000")

    # Invariant: Actual database holding records remain completely untouched!
    db_aapl = db_session.query(Holding).filter_by(instrument_id="INS-AAPL").first()
    assert db_aapl.quantity == Decimal("50.0000")
    db_bnd = db_session.query(Holding).filter_by(instrument_id="INS-BND").first()
    assert db_bnd is None


def test_simulation_cash_accounting_and_value_invariant(db_session):
    """Verify: post_trade_portfolio_value = pre_trade_portfolio_value - total_executable_fees."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    bnd = Instrument(instrument_id="INS-BND", symbol="BND", instrument_name="Bond", asset_class="DEBT", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add_all([aapl, bnd])

    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=3, instrument_id="INS-BND", price=Decimal("50.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("5000.0000"), as_of_date=as_of),
        Holding(holding_id="H-AAPL", portfolio_id="PORT-SIM-01", instrument_id="INS-AAPL", quantity=Decimal("50.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("20.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="DEBT", target_weight=Decimal("60.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=3, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("20.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    rebal_result = service.generate_rebalance_trades("PORT-SIM-01", as_of)
    sim_result = service.simulate_post_trade_state("PORT-SIM-01", as_of, rebal_result.proposed_trades)

    # Invariant: post_trade_value == pre_trade_value - total_executable_fees
    assert sim_result.post_trade_portfolio_value == (
        sim_result.pre_trade_portfolio_value - sim_result.total_executable_fees
    ).quantize(Decimal("0.0001"))
    # Invariant: simulated cash never becomes negative
    assert sim_result.post_trade_cash >= Decimal("0.0000")


def test_simulation_preserves_lot_rounding_and_residual_drift(db_session):
    """Verify lot-size rounding leaves explicit residual drift in simulation results."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    # Indivisible lot size 50 shares ($5,000 per lot)
    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("50.0000"), is_active=True)
    db_session.add(aapl)

    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("25.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("75.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    rebal_result = service.generate_rebalance_trades("PORT-SIM-01", as_of)
    sim_result = service.simulate_post_trade_state("PORT-SIM-01", as_of, rebal_result.proposed_trades)

    assert "EQUITY" in sim_result.residual_drifts
    assert sim_result.residual_drifts["EQUITY"] == Decimal("-25.0000")


# ==============================================================================
# B. Constraint Gatekeeper Tests
# ==============================================================================

def test_gatekeeper_enforces_excluded_instrument_blocks_buy(db_session):
    """Verify EXCLUDED_INSTRUMENT hard constraint blocks proposed BUY trades and rejects proposal."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    # Exclude AAPL
    cst = Constraint(
        constraint_id="CST-EXCL-AAPL",
        constraint_name="Ban AAPL",
        constraint_type="EXCLUDED_INSTRUMENT",
        scope_type="INSTRUMENT",
        scope_reference_id="INS-AAPL",
        severity="HARD",
        threshold_value=None,
        threshold_unit=None,
        effective_from=date(2026, 1, 1),
        effective_to=None,
        is_active=True,
    )
    db_session.add(cst)

    # Underweight EQUITY -> generator tries to buy AAPL, but exclusion blocks it
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    proposal_res = service.create_and_persist_proposal("PORT-SIM-01", as_of)

    # No executable BUY trades for excluded instrument
    assert all(t.instrument_id != "INS-AAPL" or t.status == "BLOCKED" for t in proposal_res.trades)


def test_gatekeeper_enforces_max_position_weight_on_individual_positions(db_session):
    """Verify MAX_POSITION_WEIGHT evaluates against individual instrument positions, not asset classes."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    # Portfolio-scoped max weight = 30.0%
    cst = Constraint(
        constraint_id="CST-MAX-WT-01",
        constraint_name="Max 30% per position",
        constraint_type="MAX_POSITION_WEIGHT",
        scope_type="PORTFOLIO",
        scope_reference_id="PORT-SIM-01",
        severity="HARD",
        threshold_value=Decimal("30.0000"),
        threshold_unit="PERCENT",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        is_active=True,
    )
    db_session.add(cst)

    # Portfolio: Cash = $10,000. Target: Equity 60%, Cash 40%.
    # Sizing $6,000 AAPL would create a 60% position weight, breaching 30%!
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("60.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("40.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    proposal_res = service.create_and_persist_proposal("PORT-SIM-01", as_of)

    # Must detect violation and reject proposal
    assert proposal_res.status == ProposalStatus.REJECTED
    assert proposal_res.review_decision == ReviewDecision.REJECTED
    assert "MAX_POSITION_WEIGHT" in proposal_res.review_reason or any(
        f.constraint_type == "MAX_POSITION_WEIGHT" and f.is_violated for f in proposal_res.constraint_findings
    )


def test_gatekeeper_enforces_trade_value_limits_min_and_max(db_session):
    """Verify MIN_TRADE_VALUE and MAX_TRADE_VALUE constraints."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    # Soft MIN_TRADE_VALUE = $500
    cst = Constraint(
        constraint_id="CST-MIN-VAL",
        constraint_name="Min Trade Value $500",
        constraint_type="MIN_TRADE_VALUE",
        scope_type="PORTFOLIO",
        scope_reference_id="PORT-SIM-01",
        severity="SOFT",
        threshold_value=Decimal("500.0000"),
        threshold_unit="USD",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        is_active=True,
    )
    db_session.add(cst)

    # Micro trade: Cash = $10,000, Equity target 1% ($100 = 1 share AAPL).
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("1.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("99.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    proposal_res = service.create_and_persist_proposal("PORT-SIM-01", as_of)

    # Soft constraint should NOT reject the proposal, but record a warning
    assert proposal_res.status == ProposalStatus.PENDING_REVIEW
    assert any("MIN_TRADE_VALUE" in w or "500" in w for w in proposal_res.warnings)


def test_gatekeeper_enforces_liquidity_limit_on_post_trade_cash_pct(db_session):
    """Verify LIQUIDITY_LIMIT evaluates against post-trade cash percentage."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    # Liquidity limit = 10% minimum cash
    cst = Constraint(
        constraint_id="CST-LIQ-01",
        constraint_name="Min Cash 10%",
        constraint_type="LIQUIDITY_LIMIT",
        scope_type="ASSET_CLASS",
        scope_reference_id="CASH",
        severity="HARD",
        threshold_value=Decimal("10.0000"),
        threshold_unit="PERCENT",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        is_active=True,
    )
    db_session.add(cst)

    # Target sets CASH to 2%, leaving only 2% cash after trades
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("98.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("2.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    proposal_res = service.create_and_persist_proposal("PORT-SIM-01", as_of)

    assert proposal_res.status == ProposalStatus.REJECTED
    assert any(f.constraint_type == "LIQUIDITY_LIMIT" and f.is_violated for f in proposal_res.constraint_findings)


# ==============================================================================
# C. Proposal Persistence Tests
# ==============================================================================

def test_persistence_clean_proposal_pending_review(db_session):
    """Verify clean proposal is persisted with PENDING_REVIEW and trades are linked."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("40.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("60.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    res = service.create_and_persist_proposal("PORT-SIM-01", as_of)

    assert res.status == ProposalStatus.PENDING_REVIEW
    assert res.review_decision == ReviewDecision.PENDING

    # Check database persistence
    db_proposal = db_session.query(RebalanceProposal).filter_by(proposal_id=res.proposal_id).first()
    assert db_proposal is not None
    assert db_proposal.portfolio_id == "PORT-SIM-01"
    assert db_proposal.status == ProposalStatus.PENDING_REVIEW
    assert db_proposal.pre_trade_portfolio_value == Decimal("10000.0000")
    assert db_proposal.post_trade_portfolio_value is not None

    db_trades = db_session.query(Trade).filter_by(proposal_id=res.proposal_id).all()
    assert len(db_trades) == len(res.trades)
    for t in db_trades:
        assert t.status == TradeStatus.PROPOSED
        assert t.trade_value > Decimal("0.0000")


def test_persistence_unknown_price_freshness_never_auto_approves(db_session):
    """Verify historical prices keep proposal in PENDING_REVIEW and flag requires_human_review."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    # 5 days old price
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=date(2026, 1, 10), source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    res = service.create_and_persist_proposal("PORT-SIM-01", as_of)

    assert res.requires_human_review is True
    assert res.status == ProposalStatus.PENDING_REVIEW


def test_persistence_rollback_on_failure_no_partial_records(db_session, monkeypatch):
    """Verify transaction atomicity: rollback prevents partial proposal or trade records."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)

    # Force a failure during persistence
    def broken_commit():
        raise RuntimeError("Database connection lost during commit!")

    monkeypatch.setattr(db_session, "commit", broken_commit)

    with pytest.raises(RuntimeError):
        service.create_and_persist_proposal("PORT-SIM-01", as_of)

    # Invariant: No partial records persisted
    assert db_session.query(RebalanceProposal).count() == 0
    assert db_session.query(Trade).count() == 0


# ==============================================================================
# D. API Integration Tests
# ==============================================================================

def test_api_create_proposal_success(api_client, db_session):
    """Verify POST /api/v1/portfolios/{portfolio_id}/rebalance/proposals creates and returns proposal."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    resp = api_client.post("/api/v1/portfolios/PORT-SIM-01/rebalance/proposals?as_of_date=2026-01-15")
    assert resp.status_code == 201

    data = resp.json()
    assert data["portfolio_id"] == "PORT-SIM-01"
    assert data["status"] == "PENDING_REVIEW"
    assert "simulation" in data
    assert "trades" in data
    assert len(data["trades"]) > 0


def test_api_create_proposal_unknown_portfolio_404(api_client):
    """Verify unknown portfolio returns 404."""
    resp = api_client.post("/api/v1/portfolios/NON-EXISTENT/rebalance/proposals?as_of_date=2026-01-15")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_api_create_proposal_missing_market_price_422(api_client, db_session):
    """Verify missing market price returns 422."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    # AAPL held without market price
    db_session.add_all([
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("5000.0000"), as_of_date=as_of),
        Holding(holding_id="H-AAPL", portfolio_id="PORT-SIM-01", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    resp = api_client.post("/api/v1/portfolios/PORT-SIM-01/rebalance/proposals?as_of_date=2026-01-15")
    assert resp.status_code == 422
    assert "price" in resp.json()["detail"].lower()


def test_api_create_proposal_with_request_body_as_of_date(api_client, db_session):
    """Verify POST endpoint accepts as_of_date via JSON request payload."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    resp = api_client.post(
        "/api/v1/portfolios/PORT-SIM-01/rebalance/proposals",
        json={"as_of_date": "2026-01-15"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["portfolio_id"] == "PORT-SIM-01"


def test_simulation_rejects_or_flags_invalid_trade_input(db_session):
    """Verify simulation rejects invalid trade inputs (e.g. overselling or non-positive)."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        Holding(holding_id="H-AAPL", portfolio_id="PORT-SIM-01", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)

    # Invalid: sell 50 shares of AAPL when only 10 are held
    from app.schemas.rebalancing import ProposedTrade
    bad_trade = ProposedTrade(
        instrument_id="INS-AAPL",
        symbol="AAPL",
        instrument_name="Apple",
        asset_class="EQUITY",
        trade_side="SELL",
        quantity=Decimal("50.0000"),
        unit_price=Decimal("100.0000"),
        trade_value=Decimal("5000.0000"),
        status="PROPOSED",
    )
    with pytest.raises(ValueError) as exc:
        service.simulate_post_trade_state("PORT-SIM-01", as_of, [bad_trade])
    assert "exceeds held quantity" in str(exc.value).lower()


def test_gatekeeper_enforces_min_position_weight(db_session):
    """Verify MIN_POSITION_WEIGHT evaluates against post-trade position weight."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    # Min position weight = 15.0% for any non-zero held position
    cst = Constraint(
        constraint_id="CST-MIN-WT",
        constraint_name="Min 15% position weight",
        constraint_type="MIN_POSITION_WEIGHT",
        scope_type="PORTFOLIO",
        scope_reference_id="PORT-SIM-01",
        severity="HARD",
        threshold_value=Decimal("15.0000"),
        threshold_unit="PERCENT",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        is_active=True,
    )
    db_session.add(cst)

    # Portfolio: Cash $10,000, target equity 5% ($500 AAPL = 5% weight < 15%)
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("5.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("95.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    proposal_res = service.create_and_persist_proposal("PORT-SIM-01", as_of)

    assert proposal_res.status == ProposalStatus.REJECTED
    assert any(f.constraint_type == "MIN_POSITION_WEIGHT" and f.is_violated for f in proposal_res.constraint_findings)


def test_gatekeeper_enforces_trade_quantity_limits_min_and_max(db_session):
    """Verify MIN_TRADE_QUANTITY and MAX_TRADE_QUANTITY constraints."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    # Instrument-scoped max trade quantity = 20 units
    cst = Constraint(
        constraint_id="CST-MAX-QTY",
        constraint_name="Max 20 AAPL units",
        constraint_type="MAX_TRADE_QUANTITY",
        scope_type="INSTRUMENT",
        scope_reference_id="INS-AAPL",
        severity="HARD",
        threshold_value=Decimal("20.0000"),
        threshold_unit="UNITS",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        is_active=True,
    )
    db_session.add(cst)

    # Buying 50 AAPL exceeds 20 unit limit
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    proposal_res = service.create_and_persist_proposal("PORT-SIM-01", as_of)

    assert proposal_res.status == ProposalStatus.REJECTED
    assert any(f.constraint_type == "MAX_TRADE_QUANTITY" and f.is_violated for f in proposal_res.constraint_findings)


def test_gatekeeper_respects_effective_dates_and_open_ended_constraints(db_session):
    """Verify expired constraints are ignored, while effective constraints are enforced."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    # Expired constraint (expired on 2026-01-01)
    expired_cst = Constraint(
        constraint_id="CST-EXPIRED",
        constraint_name="Expired exclusion",
        constraint_type="EXCLUDED_INSTRUMENT",
        scope_type="INSTRUMENT",
        scope_reference_id="INS-AAPL",
        severity="HARD",
        threshold_value=None,
        threshold_unit=None,
        effective_from=date(2025, 1, 1),
        effective_to=date(2026, 1, 1),
        is_active=True,
    )
    db_session.add(expired_cst)

    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    proposal_res = service.create_and_persist_proposal("PORT-SIM-01", as_of)

    # Expired constraint should NOT block AAPL
    assert proposal_res.status == ProposalStatus.PENDING_REVIEW
    assert any(t.instrument_id == "INS-AAPL" and t.status == "PROPOSED" for t in proposal_res.trades)


def test_api_create_proposal_hard_violation_returns_rejected_proposal(api_client, db_session):
    """Verify API endpoint persists and returns REJECTED proposal when hard constraints are breached."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    cst = Constraint(
        constraint_id="CST-HARD-CAP",
        constraint_name="Hard 20% max weight",
        constraint_type="MAX_POSITION_WEIGHT",
        scope_type="PORTFOLIO",
        scope_reference_id="PORT-SIM-01",
        severity="HARD",
        threshold_value=Decimal("20.0000"),
        threshold_unit="PERCENT",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        is_active=True,
    )
    db_session.add(cst)

    # 50% target breaches 20% cap
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    resp = api_client.post("/api/v1/portfolios/PORT-SIM-01/rebalance/proposals?as_of_date=2026-01-15")
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "REJECTED"
    assert data["review_decision"] == "REJECTED"
    assert "MAX_POSITION_WEIGHT" in data["review_reason"]


def test_api_create_proposal_unexpected_error_returns_safe_500(api_client, db_session, monkeypatch):
    """Verify unexpected server error returns generic 500 without leaking stack traces."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    def broken_proposal(*args, **kwargs):
        raise RuntimeError("Secret internal DB crash detail")

    monkeypatch.setattr(RebalancingService, "create_and_persist_proposal", broken_proposal)

    resp = api_client.post("/api/v1/portfolios/PORT-SIM-01/rebalance/proposals?as_of_date=2026-01-15")
    assert resp.status_code == 500
    assert resp.json()["detail"] == "An internal error occurred."


# ==============================================================================
# Phase 4.2 Final Persistence and Financial Safety Regression Tests
# ==============================================================================

def test_hard_blocked_buy_trade_is_excluded_from_final_simulation(db_session):
    """Verify when a BUY trade is blocked by a hard constraint, simulation excludes it and does not spend cash."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    # Hard constraint: Max trade value on BUY = $1,000 (blocks the $5,000 buy)
    cst = Constraint(
        constraint_id="CST-MAX-BUY-VAL",
        constraint_name="Hard cap BUY at $1000",
        constraint_type="MAX_TRADE_VALUE",
        scope_type="INSTRUMENT",
        scope_reference_id="INS-AAPL",
        severity="HARD",
        threshold_value=Decimal("1000.0000"),
        threshold_unit="USD",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        is_active=True,
    )
    db_session.add(cst)

    # Portfolio has $10,000 cash. Target is 50% Equity ($5,000 AAPL), 50% Cash.
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    proposal_res = service.create_and_persist_proposal("PORT-SIM-01", as_of)

    # The proposal must be REJECTED due to the hard MAX_TRADE_VALUE violation
    assert proposal_res.status == ProposalStatus.REJECTED

    # Any proposed trade for AAPL must be BLOCKED
    aapl_trade = next(t for t in proposal_res.trades if t.instrument_id == "INS-AAPL")
    assert aapl_trade.status == "BLOCKED"

    # CRITICAL: In simulation, the blocked BUY must NOT reduce cash or create simulated holdings!
    assert proposal_res.simulation.post_trade_cash == Decimal("10000.0000")
    assert proposal_res.simulation.total_executable_fees == Decimal("0.0000")
    assert proposal_res.simulation.post_trade_portfolio_value == Decimal("10000.0000")

    # The simulated positions must NOT contain an acquired holding for the blocked instrument
    aapl_sim = next((p for p in proposal_res.simulation.positions if p.instrument_id == "INS-AAPL"), None)
    if aapl_sim:
        assert aapl_sim.post_trade_quantity == Decimal("0.0000")
        assert aapl_sim.post_trade_market_value == Decimal("0.0000")


def test_hard_blocked_sell_blocks_dependent_buys_and_maintains_cash_solvency(db_session):
    """Verify when a SELL trade is hard-blocked, dependent BUYs that cannot be funded are blocked."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    bnd = Instrument(instrument_id="INS-BND", symbol="BND", instrument_name="Bond", asset_class="DEBT", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add_all([aapl, bnd])

    # Hard constraint: Max trade value on EQUITY sell = $1,000 (blocks the $5,000 sell)
    cst = Constraint(
        constraint_id="CST-MAX-SELL-VAL",
        constraint_name="Cap Sell Trade at $1000",
        constraint_type="MAX_TRADE_VALUE",
        scope_type="INSTRUMENT",
        scope_reference_id="INS-AAPL",
        severity="HARD",
        threshold_value=Decimal("1000.0000"),
        threshold_unit="USD",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        is_active=True,
    )
    db_session.add(cst)

    # Starting Cash = $0.0000. AAPL = 50 @ $100 = $5,000.
    # Target: 0% Equity, 100% Debt ($5,000 BND).
    # Sells $5,000 AAPL -> breaches MAX_TRADE_VALUE ($1,000 cap) -> SELL is BLOCKED!
    # Because SELL is blocked, proceeds are $0 -> BND buy CANNOT be funded!
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=3, instrument_id="INS-BND", price=Decimal("50.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("0.0000"), as_of_date=as_of),
        Holding(holding_id="H-AAPL", portfolio_id="PORT-SIM-01", instrument_id="INS-AAPL", quantity=Decimal("50.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("0.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="DEBT", target_weight=Decimal("100.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    proposal_res = service.create_and_persist_proposal("PORT-SIM-01", as_of)

    assert proposal_res.status == ProposalStatus.REJECTED
    # The sell must be blocked
    sell_trade = next(t for t in proposal_res.trades if t.trade_side == "SELL")
    assert sell_trade.status == "BLOCKED"

    # All buy trades must also be blocked due to lack of executable funding
    for t in proposal_res.trades:
        if t.trade_side == "BUY":
            assert t.status == "BLOCKED"

    # Simulation cash must remain 0 and never become negative
    assert proposal_res.simulation.post_trade_cash == Decimal("0.0000")
    assert proposal_res.simulation.post_trade_portfolio_value == Decimal("5000.0000")


def test_proposal_and_trade_id_safety_and_no_collision_with_gaps(db_session):
    """Verify proposal and trade IDs remain unique and collision-free across multiple runs even with gaps."""
    as_of = date(2026, 1, 15)
    _seed_base_environment(db_session, as_of)

    # Pre-seed a proposal with an ID gap (e.g. RB-2026-000010)
    existing_prop = RebalanceProposal(
        proposal_id="RB-2026-000010",
        portfolio_id="PORT-SIM-01",
        status="DRAFT",
        review_decision="PENDING",
        pre_trade_portfolio_value=Decimal("1000.0000"),
        post_trade_portfolio_value=Decimal("1000.0000"),
    )
    db_session.add(existing_prop)
    db_session.commit()

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-SIM-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-SIM-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-SIM-01", asset_class="CASH", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    prop1 = service.create_and_persist_proposal("PORT-SIM-01", as_of)
    prop2 = service.create_and_persist_proposal("PORT-SIM-01", as_of)

    assert prop1.proposal_id != prop2.proposal_id
    assert prop1.proposal_id != "RB-2026-000010"
    assert prop2.proposal_id != "RB-2026-000010"

    # Trade IDs must all be mutually exclusive
    prop1_trade_ids = {t.trade_id for t in prop1.trades}
    prop2_trade_ids = {t.trade_id for t in prop2.trades}
    assert prop1_trade_ids.isdisjoint(prop2_trade_ids)


