"""Tests for Core Portfolio Analytics Service and Schemas.

Following strict TDD, these tests define the contract and expected behavior
for portfolio valuation, asset-class allocation, and allocation drift before implementation.
"""

from datetime import date, timedelta
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.holding import Holding
from app.models.instrument import Instrument
from app.models.investor_profile import InvestorProfile, RiskCategory
from app.models.market_price import MarketPrice
from app.models.portfolio import Portfolio, PortfolioStatus
from app.models.target_allocation import TargetAllocation


def _create_sqlite_session() -> Session:
    """Create an in-memory SQLite database session with foreign keys enabled."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return Session(engine)


def _seed_base_data(session: Session):
    """Seed base investor, portfolio, and instruments."""
    investor = InvestorProfile(
        investor_id="INV-001",
        name="Alice Walker",
        risk_category=RiskCategory.MODERATE,
    )
    session.add(investor)
    session.flush()

    portfolio = Portfolio(
        portfolio_id="PORT-001",
        investor_id="INV-001",
        portfolio_name="Alice Growth Portfolio",
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
            instrument_name="Total Bond Market ETF",
            asset_class="DEBT",
            lot_size=Decimal("1.0000"),
            is_active=True,
        ),
        Instrument(
            instrument_id="INS-GLD",
            symbol="GLD",
            instrument_name="SPDR Gold Trust",
            asset_class="COMMODITIES",
            lot_size=Decimal("1.0000"),
            is_active=True,
        ),
        Instrument(
            instrument_id="INS-CASH",
            symbol="CASH-USD",
            instrument_name="Cash Equivalents USD",
            asset_class="CASH",
            lot_size=Decimal("1.0000"),
            is_active=True,
        ),
    ]
    session.add_all(instruments)
    session.commit()


# ==============================================================================
# 1. Correct position market value
# ==============================================================================

def test_correct_position_market_value():
    from app.services.portfolio_analytics_service import PortfolioAnalyticsService

    session = _create_sqlite_session()
    _seed_base_data(session)

    as_of = date(2026, 1, 15)
    # Add price: AAPL = 150.2500
    session.add(MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("150.2500"), price_date=as_of, source="TEST"))
    # Add holding: AAPL = 10 units
    session.add(Holding(holding_id="H-01", portfolio_id="PORT-001", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=as_of))
    session.commit()

    service = PortfolioAnalyticsService(session)
    valuation = service.get_portfolio_valuation("PORT-001", as_of)

    assert len(valuation.positions) == 1
    pos = valuation.positions[0]
    assert pos.instrument_id == "INS-AAPL"
    assert pos.quantity == Decimal("10.0000")
    assert pos.unit_price == Decimal("150.2500")
    assert pos.market_value == Decimal("1502.5000")
    assert isinstance(pos.market_value, Decimal)


# ==============================================================================
# 2. Correct total portfolio valuation
# ==============================================================================

def test_correct_total_portfolio_valuation():
    from app.services.portfolio_analytics_service import PortfolioAnalyticsService

    session = _create_sqlite_session()
    _seed_base_data(session)

    as_of = date(2026, 1, 15)
    # AAPL: 10 * 150 = 1500; BND: 20 * 50 = 1000; CASH: 500 * 1 = 500. Total = 3000
    session.add_all([
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("150.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=2, instrument_id="INS-BND", price=Decimal("50.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=3, instrument_id="INS-CASH", price=Decimal("1.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-001", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=as_of),
        Holding(holding_id="H-02", portfolio_id="PORT-001", instrument_id="INS-BND", quantity=Decimal("20.0000"), as_of_date=as_of),
        Holding(holding_id="H-03", portfolio_id="PORT-001", instrument_id="INS-CASH", quantity=Decimal("500.0000"), as_of_date=as_of),
    ])
    session.commit()

    service = PortfolioAnalyticsService(session)
    valuation = service.get_portfolio_valuation("PORT-001", as_of)

    assert valuation.total_market_value == Decimal("3000.0000")
    assert isinstance(valuation.total_market_value, Decimal)


# ==============================================================================
# 3. Latest market price on or before as-of date
# ==============================================================================

def test_latest_market_price_on_or_before_as_of_date():
    from app.services.portfolio_analytics_service import PortfolioAnalyticsService

    session = _create_sqlite_session()
    _seed_base_data(session)

    # Prices on Jan 10 (140.0), Jan 14 (145.0), and Jan 16 (future: 160.0)
    session.add_all([
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("140.0000"), price_date=date(2026, 1, 10), source="TEST"),
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("145.0000"), price_date=date(2026, 1, 14), source="TEST"),
        MarketPrice(id=3, instrument_id="INS-AAPL", price=Decimal("160.0000"), price_date=date(2026, 1, 16), source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-001", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=date(2026, 1, 15)),
    ])
    session.commit()

    service = PortfolioAnalyticsService(session)
    valuation = service.get_portfolio_valuation("PORT-001", date(2026, 1, 15))

    # Must select price from Jan 14 (145.0000), ignoring future Jan 16 price
    pos = valuation.positions[0]
    assert pos.unit_price == Decimal("145.0000")
    assert pos.price_date == date(2026, 1, 14)
    assert pos.market_value == Decimal("1450.0000")


# ==============================================================================
# 4. Missing market price raises an explicit error
# ==============================================================================

def test_missing_market_price_raises_explicit_error():
    from app.services.portfolio_analytics_service import MissingPriceError, PortfolioAnalyticsService

    session = _create_sqlite_session()
    _seed_base_data(session)

    as_of = date(2026, 1, 15)
    # Holding exists for AAPL, but no MarketPrice exists
    session.add(Holding(holding_id="H-01", portfolio_id="PORT-001", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=as_of))
    session.commit()

    service = PortfolioAnalyticsService(session)
    with pytest.raises(MissingPriceError) as exc_info:
        service.get_portfolio_valuation("PORT-001", as_of)

    assert "INS-AAPL" in str(exc_info.value)
    assert exc_info.value.instrument_id == "INS-AAPL"


# ==============================================================================
# 5. Stale price is diagnosed correctly
# ==============================================================================

def test_stale_price_diagnosed_correctly():
    from app.services.portfolio_analytics_service import PortfolioAnalyticsService

    session = _create_sqlite_session()
    _seed_base_data(session)

    # Price is from Jan 10, as-of is Jan 15 (5 days old).
    # Since no staleness policy/calendar is configured, is_stale must be None (unknown),
    # while price_age_days and diagnostic are exposed.
    session.add_all([
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("150.0000"), price_date=date(2026, 1, 10), source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-001", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=date(2026, 1, 15)),
    ])
    session.commit()

    service = PortfolioAnalyticsService(session)
    valuation = service.get_portfolio_valuation("PORT-001", date(2026, 1, 15))

    pos = valuation.positions[0]
    assert pos.price_age_days == 5
    assert pos.is_stale is None
    assert pos.diagnostic is not None
    assert "5 day(s) old" in pos.diagnostic


def test_current_price_classified_as_not_stale():
    from app.services.portfolio_analytics_service import PortfolioAnalyticsService

    session = _create_sqlite_session()
    _seed_base_data(session)

    as_of = date(2026, 1, 15)
    # Price is from today (Jan 15)
    session.add_all([
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("150.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-001", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=as_of),
    ])
    session.commit()

    service = PortfolioAnalyticsService(session)
    valuation = service.get_portfolio_valuation("PORT-001", as_of)

    pos = valuation.positions[0]
    assert pos.price_age_days == 0
    assert pos.is_stale is False
    assert pos.diagnostic is None


# ==============================================================================
# 6. Effective target allocation date filtering
# ==============================================================================

def test_effective_target_allocation_date_filtering():
    from app.services.portfolio_analytics_service import PortfolioAnalyticsService

    session = _create_sqlite_session()
    _seed_base_data(session)

    as_of = date(2026, 1, 15)

    # Target allocations:
    # 1. Past expired: EQUITY 70% (2025-01-01 to 2025-12-31)
    # 2. Active: EQUITY 60% (2026-01-01 to NULL)
    # 3. Active: DEBT 40% (2026-01-01 to NULL)
    # 4. Future: EQUITY 50% (2026-06-01 to NULL)
    session.add_all([
        TargetAllocation(id=1, portfolio_id="PORT-001", asset_class="EQUITY", target_weight=Decimal("70.0000"), effective_from=date(2025, 1, 1), effective_to=date(2025, 12, 31)),
        TargetAllocation(id=2, portfolio_id="PORT-001", asset_class="EQUITY", target_weight=Decimal("60.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=3, portfolio_id="PORT-001", asset_class="DEBT", target_weight=Decimal("40.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=4, portfolio_id="PORT-001", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 6, 1), effective_to=None),
        # Holdings: 10 AAPL @ 100 = 1000
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-001", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=as_of),
    ])
    session.commit()

    service = PortfolioAnalyticsService(session)
    drift_result = service.get_portfolio_drift("PORT-001", as_of)

    targets = {d.asset_class: d.target_weight for d in drift_result.drifts}
    assert targets["EQUITY"] == Decimal("60.0000")
    assert targets["DEBT"] == Decimal("40.0000")
    assert len(targets) == 2


# ==============================================================================
# 7. Target asset class without holdings has negative drift
# ==============================================================================

def test_target_asset_class_without_holdings_has_negative_drift():
    from app.services.portfolio_analytics_service import PortfolioAnalyticsService

    session = _create_sqlite_session()
    _seed_base_data(session)

    as_of = date(2026, 1, 15)

    # 100% held in EQUITY ($10,000)
    # Target: 60% EQUITY, 40% DEBT (0 holding in DEBT)
    session.add_all([
        TargetAllocation(id=1, portfolio_id="PORT-001", asset_class="EQUITY", target_weight=Decimal("60.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-001", asset_class="DEBT", target_weight=Decimal("40.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-001", instrument_id="INS-AAPL", quantity=Decimal("100.0000"), as_of_date=as_of),
    ])
    session.commit()

    service = PortfolioAnalyticsService(session)
    drift_result = service.get_portfolio_drift("PORT-001", as_of)

    drifts = {d.asset_class: d for d in drift_result.drifts}
    debt_drift = drifts["DEBT"]
    assert debt_drift.current_weight == Decimal("0.0000")
    assert debt_drift.target_weight == Decimal("40.0000")
    # Percentage drift = 0 - 40 = -40.0000%
    assert debt_drift.percentage_drift == Decimal("-40.0000")
    # Monetary drift = -40% * 10,000 = -4,000.0000
    assert debt_drift.monetary_drift == Decimal("-4000.0000")


# ==============================================================================
# 8. Positive and negative monetary drift calculations
# ==============================================================================

def test_positive_and_negative_monetary_drift():
    from app.services.portfolio_analytics_service import PortfolioAnalyticsService

    session = _create_sqlite_session()
    _seed_base_data(session)

    as_of = date(2026, 1, 15)

    # Portfolio value: 8,000 in EQUITY, 2,000 in DEBT. Total = 10,000.
    # Current: EQUITY 80%, DEBT 20%
    # Target: EQUITY 50%, DEBT 50%
    session.add_all([
        TargetAllocation(id=1, portfolio_id="PORT-001", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-001", asset_class="DEBT", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=2, instrument_id="INS-BND", price=Decimal("50.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-001", instrument_id="INS-AAPL", quantity=Decimal("80.0000"), as_of_date=as_of),
        Holding(holding_id="H-02", portfolio_id="PORT-001", instrument_id="INS-BND", quantity=Decimal("40.0000"), as_of_date=as_of),
    ])
    session.commit()

    service = PortfolioAnalyticsService(session)
    drift_result = service.get_portfolio_drift("PORT-001", as_of)

    drifts = {d.asset_class: d for d in drift_result.drifts}
    eq = drifts["EQUITY"]
    debt = drifts["DEBT"]

    # EQUITY is overweight: +30% -> +3,000.0000 (potential SELL)
    assert eq.percentage_drift == Decimal("30.0000")
    assert eq.monetary_drift == Decimal("3000.0000")

    # DEBT is underweight: -30% -> -3,000.0000 (potential BUY)
    assert debt.percentage_drift == Decimal("-30.0000")
    assert debt.monetary_drift == Decimal("-3000.0000")


# ==============================================================================
# 9. Monetary drift reconciliation across asset classes
# ==============================================================================

def test_monetary_drift_reconciliation_across_asset_classes():
    from app.services.portfolio_analytics_service import PortfolioAnalyticsService

    session = _create_sqlite_session()
    _seed_base_data(session)

    as_of = date(2026, 1, 15)

    # 3 asset classes with irregular splits: Total = 10,000
    # Holdings: AAPL: 5500, BND: 3500, GLD: 1000
    # Targets: AAPL: 40%, BND: 40%, GLD: 20%
    session.add_all([
        TargetAllocation(id=1, portfolio_id="PORT-001", asset_class="EQUITY", target_weight=Decimal("40.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-001", asset_class="DEBT", target_weight=Decimal("40.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=3, portfolio_id="PORT-001", asset_class="COMMODITIES", target_weight=Decimal("20.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=2, instrument_id="INS-BND", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=3, instrument_id="INS-GLD", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-001", instrument_id="INS-AAPL", quantity=Decimal("55.0000"), as_of_date=as_of),
        Holding(holding_id="H-02", portfolio_id="PORT-001", instrument_id="INS-BND", quantity=Decimal("35.0000"), as_of_date=as_of),
        Holding(holding_id="H-03", portfolio_id="PORT-001", instrument_id="INS-GLD", quantity=Decimal("10.0000"), as_of_date=as_of),
    ])
    session.commit()

    service = PortfolioAnalyticsService(session)
    drift_result = service.get_portfolio_drift("PORT-001", as_of)

    # Sum of percentage drifts must equal exactly 0.0000%
    total_pct_drift = sum(d.percentage_drift for d in drift_result.drifts)
    assert total_pct_drift == Decimal("0.0000")

    # Sum of monetary drifts must reconcile to 0.0000
    total_monetary_drift = sum(d.monetary_drift for d in drift_result.drifts)
    assert total_monetary_drift == Decimal("0.0000")


# ==============================================================================
# 10. Largest-weight rounding residual assignment
# ==============================================================================

def test_largest_weight_rounding_residual_assignment():
    from app.services.portfolio_analytics_service import PortfolioAnalyticsService

    session = _create_sqlite_session()
    _seed_base_data(session)

    as_of = date(2026, 1, 15)

    # 3 positions dividing into repeating thirds:
    # 300, 300, 300 -> each 33.3333% -> sum = 99.9999%
    # But if one is larger: 400, 300, 300 -> total 1000
    # 40.0000%, 30.0000%, 30.0000%
    # Let's test a case with rounding drift:
    # 7000 in EQUITY, 1500 in DEBT, 1500 in COMMODITIES -> 70%, 15%, 15%
    # Let's create an uneven split where 1/3, 1/3, 1/3 produces 0.0001 residue:
    # AAPL: 6000 (largest), BND: 1999, GLD: 2001. Total = 10,000.
    # What about total 3000: AAPL=1000 (33.3333%), BND=1000 (33.3333%), GLD=1000 (33.3333%)?
    # Sum = 99.9999%. Residual is +0.0001%.
    # If weights are [EQUITY: 5000, DEBT: 3000, CASH: 2000]:
    # Suppose we have values: 7000 (EQUITY), 2000 (DEBT), 1000 (CASH) with total 10001:
    # 7000/10001 = 69.9930%, 2000/10001 = 19.9980%, 1001/10001 = 10.0090%
    # Sum = 70.0000%
    # Let's test specifically that the residual is assigned to the largest weight asset class.
    session.add_all([
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("1.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=2, instrument_id="INS-BND", price=Decimal("1.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=3, instrument_id="INS-GLD", price=Decimal("1.0000"), price_date=as_of, source="TEST"),
        # Total = 3000. Each is 1000. But make AAPL 1000.0001?
        # Say AAPL=1600, BND=700, GLD=700. Total = 3000.
        # AAPL: 1600/3000 = 53.333333... -> 53.3333%
        # BND: 700/3000 = 23.333333... -> 23.3333%
        # GLD: 700/3000 = 23.333333... -> 23.3333%
        # Sum = 53.3333 + 23.3333 + 23.3333 = 99.9999%.
        # Drift = +0.0001%.
        # Largest is EQUITY (53.3333%).
        # It must receive the +0.0001%, becoming 53.3334%!
        Holding(holding_id="H-01", portfolio_id="PORT-001", instrument_id="INS-AAPL", quantity=Decimal("1600.0000"), as_of_date=as_of),
        Holding(holding_id="H-02", portfolio_id="PORT-001", instrument_id="INS-BND", quantity=Decimal("700.0000"), as_of_date=as_of),
        Holding(holding_id="H-03", portfolio_id="PORT-001", instrument_id="INS-GLD", quantity=Decimal("700.0000"), as_of_date=as_of),
    ])
    session.commit()

    service = PortfolioAnalyticsService(session)
    valuation = service.get_portfolio_valuation("PORT-001", as_of)

    ac_weights = {a.asset_class: a.current_weight for a in valuation.asset_classes}
    # EQUITY was the largest (1600), so it absorbs the +0.0001% residue
    assert ac_weights["EQUITY"] == Decimal("53.3334")
    assert ac_weights["DEBT"] == Decimal("23.3333")
    assert ac_weights["COMMODITIES"] == Decimal("23.3333")
    assert sum(ac_weights.values()) == Decimal("100.0000")


# ==============================================================================
# 11. Empty portfolio behavior
# ==============================================================================

def test_empty_portfolio_behavior():
    from app.services.portfolio_analytics_service import PortfolioAnalyticsService

    session = _create_sqlite_session()
    _seed_base_data(session)

    as_of = date(2026, 1, 15)
    # Portfolio PORT-001 has zero holdings on or before as_of

    service = PortfolioAnalyticsService(session)
    valuation = service.get_portfolio_valuation("PORT-001", as_of)

    assert valuation.portfolio_id == "PORT-001"
    assert valuation.total_market_value == Decimal("0.0000")
    assert len(valuation.positions) == 0
    assert len(valuation.asset_classes) == 0

    # Drift on empty portfolio with target allocations
    session.add(TargetAllocation(id=1, portfolio_id="PORT-001", asset_class="EQUITY", target_weight=Decimal("100.0000"), effective_from=date(2026, 1, 1), effective_to=None))
    session.commit()

    drift_result = service.get_portfolio_drift("PORT-001", as_of)
    assert drift_result.total_market_value == Decimal("0.0000")
    assert len(drift_result.drifts) == 1
    d = drift_result.drifts[0]
    assert d.current_weight == Decimal("0.0000")
    assert d.target_weight == Decimal("100.0000")
    assert d.percentage_drift == Decimal("-100.0000")
    assert d.monetary_drift == Decimal("0.0000")


# ==============================================================================
# 12. Unknown portfolio handling
# ==============================================================================

def test_unknown_portfolio_raises_portfolio_not_found_error():
    from app.services.portfolio_analytics_service import PortfolioAnalyticsService, PortfolioNotFoundError

    session = _create_sqlite_session()
    _seed_base_data(session)

    service = PortfolioAnalyticsService(session)
    with pytest.raises(PortfolioNotFoundError) as exc_info:
        service.get_portfolio_valuation("NON-EXISTENT-PORTFOLIO", date(2026, 1, 15))

    assert "NON-EXISTENT-PORTFOLIO" in str(exc_info.value)

    with pytest.raises(PortfolioNotFoundError):
        service.get_portfolio_drift("NON-EXISTENT-PORTFOLIO", date(2026, 1, 15))


# ==============================================================================
# 13. Decimal precision preservation
# ==============================================================================

def test_decimal_precision_preservation():
    from app.services.portfolio_analytics_service import PortfolioAnalyticsService

    session = _create_sqlite_session()
    _seed_base_data(session)

    as_of = date(2026, 1, 15)
    # High precision inputs
    session.add_all([
        MarketPrice(id=1, instrument_id="INS-AAPL", price=Decimal("123.4567"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-01", portfolio_id="PORT-001", instrument_id="INS-AAPL", quantity=Decimal("10.1234"), as_of_date=as_of),
    ])
    session.commit()

    service = PortfolioAnalyticsService(session)
    valuation = service.get_portfolio_valuation("PORT-001", as_of)

    pos = valuation.positions[0]
    # 10.1234 * 123.4567 = 1249.80164678 -> 1249.8016
    assert pos.market_value == Decimal("1249.8016")
    assert isinstance(pos.market_value, Decimal)
    assert valuation.total_market_value == Decimal("1249.8016")
    assert isinstance(valuation.total_market_value, Decimal)
