"""Tests for Portfolio Analytics API endpoints and rebalance trigger evaluation.

Following strict TDD, these tests verify the FastAPI router endpoints,
response schemas, error handling, and constraint-based trigger evaluation.
"""

from datetime import date
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
from app.models.holding import Holding
from app.models.instrument import Instrument
from app.models.investor_profile import InvestorProfile, RiskCategory
from app.models.market_price import MarketPrice
from app.models.portfolio import Portfolio, PortfolioStatus
from app.models.target_allocation import TargetAllocation


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


def _seed_test_data(session: Session):
    """Seed standard test entities."""
    investor = InvestorProfile(
        investor_id="INV-API-01",
        name="Bob Taylor",
        risk_category=RiskCategory.HIGH,
    )
    session.add(investor)
    session.flush()

    portfolio = Portfolio(
        portfolio_id="PORT-API-01",
        investor_id="INV-API-01",
        portfolio_name="Bob Growth",
        base_currency="USD",
        status=PortfolioStatus.ACTIVE,
    )
    session.add(portfolio)

    instruments = [
        Instrument(
            instrument_id="INS-AAPL",
            symbol="AAPL",
            instrument_name="Apple Inc.",
            asset_class="EQUITY",
            lot_size=Decimal("1.0000"),
            is_active=True,
        ),
        Instrument(
            instrument_id="INS-BND",
            symbol="BND",
            instrument_name="Vanguard Total Bond",
            asset_class="DEBT",
            lot_size=Decimal("1.0000"),
            is_active=True,
        ),
        Instrument(
            instrument_id="INS-GLD",
            symbol="GLD",
            instrument_name="SPDR Gold",
            asset_class="COMMODITIES",
            lot_size=Decimal("1.0000"),
            is_active=True,
        ),
    ]
    session.add_all(instruments)
    session.commit()


@pytest.fixture
def client_and_session():
    """Fixture providing a FastAPI TestClient bound to an in-memory SQLite session."""
    session = _create_sqlite_session()
    _seed_test_data(session)

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client, session
    app.dependency_overrides.clear()
    session.close()


# ==============================================================================
# 1. GET /api/v1/portfolios/{portfolio_id}/valuation
# ==============================================================================

def test_get_portfolio_valuation_success(client_and_session):
    client, session = client_and_session
    as_of = date(2026, 1, 15)

    session.add_all([
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("150.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=2, instrument_id="INS-BND", price=Decimal("50.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-API-01", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=as_of),
        Holding(holding_id="H-02", portfolio_id="PORT-API-01", instrument_id="INS-BND", quantity=Decimal("20.0000"), as_of_date=as_of),
    ])
    session.commit()

    resp = client.get("/api/v1/portfolios/PORT-API-01/valuation?as_of_date=2026-01-15")
    assert resp.status_code == 200
    data = resp.json()

    assert data["portfolio_id"] == "PORT-API-01"
    assert data["as_of_date"] == "2026-01-15"
    assert Decimal(str(data["total_market_value"])) == Decimal("2500.0000")
    assert len(data["positions"]) == 2
    assert len(data["asset_classes"]) == 2


def test_get_portfolio_valuation_optional_as_of_date(client_and_session):
    client, session = client_and_session
    today = date.today()

    session.add_all([
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("150.0000"), price_date=today, source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-API-01", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=today),
    ])
    session.commit()

    resp = client.get("/api/v1/portfolios/PORT-API-01/valuation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["as_of_date"] == today.isoformat()
    assert Decimal(str(data["total_market_value"])) == Decimal("1500.0000")


# ==============================================================================
# 2. GET /api/v1/portfolios/{portfolio_id}/drift
# ==============================================================================

def test_get_portfolio_drift_success(client_and_session):
    client, session = client_and_session
    as_of = date(2026, 1, 15)

    session.add_all([
        # Current holdings: 10 AAPL @ 100 = 1000 (100% Equity)
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-API-01", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=as_of),
        # Target: 60% Equity, 40% Commodities (Commodities has 0 holdings)
        TargetAllocation(id=1, portfolio_id="PORT-API-01", asset_class="EQUITY", target_weight=Decimal("60.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-API-01", asset_class="COMMODITIES", target_weight=Decimal("40.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    session.commit()

    resp = client.get("/api/v1/portfolios/PORT-API-01/drift?as_of_date=2026-01-15")
    assert resp.status_code == 200
    data = resp.json()

    assert data["portfolio_id"] == "PORT-API-01"
    assert Decimal(str(data["total_market_value"])) == Decimal("1000.0000")

    drifts = {d["asset_class"]: d for d in data["drifts"]}
    assert "COMMODITIES" in drifts
    assert Decimal(str(drifts["COMMODITIES"]["current_weight"])) == Decimal("0.0000")
    assert Decimal(str(drifts["COMMODITIES"]["target_weight"])) == Decimal("40.0000")
    assert Decimal(str(drifts["COMMODITIES"]["percentage_drift"])) == Decimal("-40.0000")
    assert Decimal(str(drifts["COMMODITIES"]["monetary_drift"])) == Decimal("-400.0000")
    assert drifts["COMMODITIES"]["action_signal"] == "BUY"

    assert Decimal(str(drifts["EQUITY"]["percentage_drift"])) == Decimal("40.0000")
    assert Decimal(str(drifts["EQUITY"]["monetary_drift"])) == Decimal("400.0000")
    assert drifts["EQUITY"]["action_signal"] == "SELL"


# ==============================================================================
# 3. Error Handling
# ==============================================================================

def test_unknown_portfolio_returns_404(client_and_session):
    client, _ = client_and_session

    resp_val = client.get("/api/v1/portfolios/NON-EXISTENT-ID/valuation")
    assert resp_val.status_code == 404
    assert "Portfolio not found" in resp_val.json()["detail"]

    resp_drift = client.get("/api/v1/portfolios/NON-EXISTENT-ID/drift")
    assert resp_drift.status_code == 404
    assert "Portfolio not found" in resp_drift.json()["detail"]


def test_missing_market_price_returns_client_error(client_and_session):
    client, session = client_and_session
    as_of = date(2026, 1, 15)

    # Holding exists but no MarketPrice
    session.add(Holding(holding_id="H-01", portfolio_id="PORT-API-01", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=as_of))
    session.commit()

    resp = client.get("/api/v1/portfolios/PORT-API-01/valuation?as_of_date=2026-01-15")
    assert resp.status_code == 422
    assert "Missing market price" in resp.json()["detail"]


def test_invalid_date_format_returns_422(client_and_session):
    client, _ = client_and_session
    resp = client.get("/api/v1/portfolios/PORT-API-01/valuation?as_of_date=not-a-valid-date")
    assert resp.status_code == 422


# ==============================================================================
# 4. Rebalance Trigger Evaluation
# ==============================================================================

def test_rebalance_trigger_not_configured_when_no_policy_exists(client_and_session):
    client, session = client_and_session
    as_of = date(2026, 1, 15)

    session.add_all([
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-API-01", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-API-01", asset_class="EQUITY", target_weight=Decimal("100.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    session.commit()

    resp = client.get("/api/v1/portfolios/PORT-API-01/drift?as_of_date=2026-01-15")
    assert resp.status_code == 200
    trigger = resp.json()["rebalance_trigger"]
    assert trigger["status"] == "NOT_CONFIGURED"
    assert trigger["rebalance_required"] is None
    assert "No explicit rebalance threshold policy configured" in trigger["policy_description"]


def test_rebalance_trigger_triggered_when_configured_constraint_breached(client_and_session):
    client, session = client_and_session
    as_of = date(2026, 1, 15)

    # AAPL is 100% of portfolio.
    # Add a MAX_POSITION_WEIGHT constraint capped at 40.0000%
    constraint = Constraint(
        constraint_id="CST-001",
        constraint_name="Equity Allocation Limit",
        constraint_type=ConstraintType.MAX_POSITION_WEIGHT.value,
        scope_type=ScopeType.PORTFOLIO.value,
        scope_reference_id="PORT-API-01",
        severity=ConstraintSeverity.HARD.value,
        threshold_value=Decimal("40.0000"),
        threshold_unit="PERCENT",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        is_active=True,
    )
    session.add_all([
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-API-01", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-API-01", asset_class="EQUITY", target_weight=Decimal("40.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        constraint,
    ])
    session.commit()

    resp = client.get("/api/v1/portfolios/PORT-API-01/drift?as_of_date=2026-01-15")
    assert resp.status_code == 200
    trigger = resp.json()["rebalance_trigger"]
    assert trigger["status"] == "TRIGGERED"
    assert trigger["rebalance_required"] is True
    assert "EQUITY" in trigger["triggered_asset_classes"]


def test_rebalance_trigger_not_triggered_when_within_configured_constraint(client_and_session):
    client, session = client_and_session
    as_of = date(2026, 1, 15)

    # AAPL is 50%, BND is 50%.
    # Add a MAX_POSITION_WEIGHT constraint capped at 60.0000% (within bounds)
    constraint = Constraint(
        constraint_id="CST-002",
        constraint_name="General Allocation Limit",
        constraint_type=ConstraintType.MAX_POSITION_WEIGHT.value,
        scope_type=ScopeType.PORTFOLIO.value,
        scope_reference_id="PORT-API-01",
        severity=ConstraintSeverity.HARD.value,
        threshold_value=Decimal("60.0000"),
        threshold_unit="PERCENT",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        is_active=True,
    )
    session.add_all([
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=2, instrument_id="INS-BND", price=Decimal("50.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-API-01", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=as_of),
        Holding(holding_id="H-02", portfolio_id="PORT-API-01", instrument_id="INS-BND", quantity=Decimal("20.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-API-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-API-01", asset_class="DEBT", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        constraint,
    ])
    session.commit()

    resp = client.get("/api/v1/portfolios/PORT-API-01/drift?as_of_date=2026-01-15")
    assert resp.status_code == 200
    trigger = resp.json()["rebalance_trigger"]
    assert trigger["status"] == "NOT_TRIGGERED"
    assert trigger["rebalance_required"] is False
    assert len(trigger["triggered_asset_classes"]) == 0


def test_rebalance_trigger_inactive_or_expired_constraint_ignored(client_and_session):
    client, session = client_and_session
    as_of = date(2026, 1, 15)

    # Inactive constraint
    inactive_c = Constraint(
        constraint_id="CST-INACT",
        constraint_name="Inactive Limit",
        constraint_type=ConstraintType.MAX_POSITION_WEIGHT.value,
        scope_type=ScopeType.PORTFOLIO.value,
        scope_reference_id="PORT-API-01",
        severity=ConstraintSeverity.HARD.value,
        threshold_value=Decimal("10.0000"),
        threshold_unit="PERCENT",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        is_active=False,
    )
    # Expired constraint
    expired_c = Constraint(
        constraint_id="CST-EXP",
        constraint_name="Expired Limit",
        constraint_type=ConstraintType.MAX_POSITION_WEIGHT.value,
        scope_type=ScopeType.PORTFOLIO.value,
        scope_reference_id="PORT-API-01",
        severity=ConstraintSeverity.HARD.value,
        threshold_value=Decimal("10.0000"),
        threshold_unit="PERCENT",
        effective_from=date(2025, 1, 1),
        effective_to=date(2025, 12, 31),
        is_active=True,
    )
    session.add_all([
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-API-01", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-API-01", asset_class="EQUITY", target_weight=Decimal("100.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        inactive_c,
        expired_c,
    ])
    session.commit()

    resp = client.get("/api/v1/portfolios/PORT-API-01/drift?as_of_date=2026-01-15")
    assert resp.status_code == 200
    trigger = resp.json()["rebalance_trigger"]
    assert trigger["status"] == "NOT_CONFIGURED"
    assert trigger["rebalance_required"] is None


def test_rebalance_trigger_min_weight_breach(client_and_session):
    client, session = client_and_session
    as_of = date(2026, 1, 15)

    # AAPL is 10%, BND is 90%.
    # Add a MIN_POSITION_WEIGHT constraint requiring at least 20.0000%
    constraint = Constraint(
        constraint_id="CST-MIN",
        constraint_name="Minimum Equity Weight",
        constraint_type=ConstraintType.MIN_POSITION_WEIGHT.value,
        scope_type=ScopeType.PORTFOLIO.value,
        scope_reference_id="PORT-API-01",
        severity=ConstraintSeverity.HARD.value,
        threshold_value=Decimal("20.0000"),
        threshold_unit="PERCENT",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        is_active=True,
    )
    session.add_all([
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("10.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=2, instrument_id="INS-BND", price=Decimal("90.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-API-01", instrument_id="INS-AAPL", quantity=Decimal("1.0000"), as_of_date=as_of),
        Holding(holding_id="H-02", portfolio_id="PORT-API-01", instrument_id="INS-BND", quantity=Decimal("1.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-API-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-API-01", asset_class="DEBT", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        constraint,
    ])
    session.commit()

    resp = client.get("/api/v1/portfolios/PORT-API-01/drift?as_of_date=2026-01-15")
    assert resp.status_code == 200
    trigger = resp.json()["rebalance_trigger"]
    assert trigger["status"] == "TRIGGERED"
    assert trigger["rebalance_required"] is True
    assert "EQUITY" in trigger["triggered_asset_classes"]


def test_empty_portfolio_valuation_via_api(client_and_session):
    client, _ = client_and_session
    # PORT-API-01 has no holdings seeded yet
    resp = client.get("/api/v1/portfolios/PORT-API-01/valuation?as_of_date=2026-01-15")
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(str(data["total_market_value"])) == Decimal("0.0000")
    assert len(data["positions"]) == 0
    assert len(data["asset_classes"]) == 0


def test_unexpected_error_returns_500_without_leak(client_and_session, monkeypatch):
    client, _ = client_and_session

    def boom(*args, **kwargs):
        raise RuntimeError("Sensitive internal database detail or exception trace")

    from app.services.portfolio_analytics_service import PortfolioAnalyticsService
    monkeypatch.setattr(PortfolioAnalyticsService, "get_portfolio_valuation", boom)

    resp = client.get("/api/v1/portfolios/PORT-API-01/valuation")
    assert resp.status_code == 500
    assert resp.json() == {"detail": "An internal error occurred."}
    assert "Sensitive" not in resp.text


def test_max_position_weight_evaluates_individual_positions_not_asset_classes(client_and_session):
    """Confirm evaluator checks instrument-level position weights, not aggregate asset-class weights."""
    client, session = client_and_session
    as_of = date(2026, 1, 15)

    # Seed 2 equity instruments (AAPL, MSFT) and 2 debt instruments (BND, TIP), plus GLD (COMMODITIES)
    inst_msft = Instrument(
        instrument_id="INS-MSFT",
        symbol="MSFT",
        instrument_name="Microsoft Corp.",
        asset_class="EQUITY",
        lot_size=Decimal("1.0000"),
        is_active=True,
    )
    inst_tip = Instrument(
        instrument_id="INS-TIP",
        symbol="TIP",
        instrument_name="iShares TIPS Bond",
        asset_class="DEBT",
        lot_size=Decimal("1.0000"),
        is_active=True,
    )
    session.add_all([inst_msft, inst_tip])

    # Portfolio value = 5 positions of $200 each = $1,000 total (each position is exactly 20.0000%)
    # Aggregate asset classes:
    # - EQUITY: AAPL ($200) + MSFT ($200) = $400 (40.0000%)
    # - DEBT: BND ($200) + TIP ($200) = $400 (40.0000%)
    # - COMMODITIES: GLD ($200) = $200 (20.0000%)
    session.add_all([
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=2, instrument_id="INS-MSFT", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=3, instrument_id="INS-BND", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=4, instrument_id="INS-TIP", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=5, instrument_id="INS-GLD", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-API-01", instrument_id="INS-AAPL", quantity=Decimal("2.0000"), as_of_date=as_of),
        Holding(holding_id="H-02", portfolio_id="PORT-API-01", instrument_id="INS-MSFT", quantity=Decimal("2.0000"), as_of_date=as_of),
        Holding(holding_id="H-03", portfolio_id="PORT-API-01", instrument_id="INS-BND", quantity=Decimal("2.0000"), as_of_date=as_of),
        Holding(holding_id="H-04", portfolio_id="PORT-API-01", instrument_id="INS-TIP", quantity=Decimal("2.0000"), as_of_date=as_of),
        Holding(holding_id="H-05", portfolio_id="PORT-API-01", instrument_id="INS-GLD", quantity=Decimal("2.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-API-01", asset_class="EQUITY", target_weight=Decimal("40.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-API-01", asset_class="DEBT", target_weight=Decimal("40.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=3, portfolio_id="PORT-API-01", asset_class="COMMODITIES", target_weight=Decimal("20.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])

    # Single position cap: 25.0000%
    # No single position exceeds 25.0000% (each is 20.0000%).
    # But aggregate EQUITY is 40.0000% and aggregate DEBT is 40.0000%.
    constraint = Constraint(
        constraint_id="CST-CAP-25",
        constraint_name="Single Position Cap 25%",
        constraint_type=ConstraintType.MAX_POSITION_WEIGHT.value,
        scope_type=ScopeType.PORTFOLIO.value,
        scope_reference_id="PORT-API-01",
        severity=ConstraintSeverity.HARD.value,
        threshold_value=Decimal("25.0000"),
        threshold_unit="PERCENT",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        is_active=True,
    )
    session.add(constraint)
    session.commit()

    resp = client.get("/api/v1/portfolios/PORT-API-01/drift?as_of_date=2026-01-15")
    assert resp.status_code == 200
    trigger = resp.json()["rebalance_trigger"]

    # Since all 5 individual positions are 20% <= 25%, rebalance must NOT be triggered!
    assert trigger["status"] == "NOT_TRIGGERED"
    assert trigger["rebalance_required"] is False
    assert len(trigger["triggered_asset_classes"]) == 0
    assert len(trigger["triggered_positions"]) == 0


def test_max_position_weight_breach_identifies_specific_breaching_positions(client_and_session):
    """Confirm evaluator identifies the specific breaching position and its asset class."""
    client, session = client_and_session
    as_of = date(2026, 1, 15)

    # AAPL is $350 (35%), MSFT is $150 (15%), BND is $500 (50%). Total = $1000.
    # Cap = 30.0000%.
    # AAPL breaches (35% > 30%), MSFT does not (15% <= 30%).
    # BND breaches (50% > 30%).
    inst_msft = Instrument(
        instrument_id="INS-MSFT",
        symbol="MSFT",
        instrument_name="Microsoft Corp.",
        asset_class="EQUITY",
        lot_size=Decimal("1.0000"),
        is_active=True,
    )
    session.add(inst_msft)

    session.add_all([
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=2, instrument_id="INS-MSFT", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=3, instrument_id="INS-BND", price=Decimal("50.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-API-01", instrument_id="INS-AAPL", quantity=Decimal("3.5000"), as_of_date=as_of),
        Holding(holding_id="H-02", portfolio_id="PORT-API-01", instrument_id="INS-MSFT", quantity=Decimal("1.5000"), as_of_date=as_of),
        Holding(holding_id="H-03", portfolio_id="PORT-API-01", instrument_id="INS-BND", quantity=Decimal("10.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-API-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-API-01", asset_class="DEBT", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        Constraint(
            constraint_id="CST-CAP-30",
            constraint_name="Single Position Cap 30%",
            constraint_type=ConstraintType.MAX_POSITION_WEIGHT.value,
            scope_type=ScopeType.PORTFOLIO.value,
            scope_reference_id="PORT-API-01",
            severity=ConstraintSeverity.HARD.value,
            threshold_value=Decimal("30.0000"),
            threshold_unit="PERCENT",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            is_active=True,
        ),
    ])
    session.commit()

    resp = client.get("/api/v1/portfolios/PORT-API-01/drift?as_of_date=2026-01-15")
    assert resp.status_code == 200
    trigger = resp.json()["rebalance_trigger"]

    assert trigger["status"] == "TRIGGERED"
    assert trigger["rebalance_required"] is True
    # Breaching positions: AAPL (35%) and BND (50%). MSFT (15%) did NOT breach.
    assert "AAPL" in trigger["triggered_positions"]
    assert "BND" in trigger["triggered_positions"]
    assert "MSFT" not in trigger["triggered_positions"]
    # Associated asset classes:
    assert "EQUITY" in trigger["triggered_asset_classes"]
    assert "DEBT" in trigger["triggered_asset_classes"]



