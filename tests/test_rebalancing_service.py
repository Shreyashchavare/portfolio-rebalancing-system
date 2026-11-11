"""Tests for Deterministic Rebalancing Trade Generation Service.

Following strict TDD, these tests verify the rebalancing service's contract,
deterministic trade generation, fee accounting, lot-size rounding, cash solvency,
excluded instrument blocking, and residual drift tracking.
"""

from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.constraint import Constraint, ConstraintSeverity, ConstraintType, ScopeType
from app.models.fee_schedule import FeeSchedule
from app.models.holding import Holding
from app.models.instrument import Instrument
from app.models.investor_profile import InvestorProfile, RiskCategory
from app.models.market_price import MarketPrice
from app.models.portfolio import Portfolio, PortfolioStatus
from app.models.target_allocation import TargetAllocation
from app.services.portfolio_analytics_service import MissingPriceError
from app.services.rebalancing_service import RebalancingService


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


def _seed_standard_environment(session: Session, as_of: date):
    """Seed baseline investor, portfolio, cash instrument, fee schedules, and market prices."""
    investor = InvestorProfile(
        investor_id="INV-REBAL-01",
        name="Alice Rebalance",
        risk_category=RiskCategory.MODERATE,
    )
    session.add(investor)
    session.flush()

    portfolio = Portfolio(
        portfolio_id="PORT-REBAL-01",
        investor_id="INV-REBAL-01",
        portfolio_name="Alice Growth",
        base_currency="USD",
        status=PortfolioStatus.ACTIVE,
    )
    session.add(portfolio)

    cash_inst = Instrument(
        instrument_id="INS-CASH-USD",
        symbol="CSH-USD-MM",
        instrument_name="USD Cash Money Market",
        asset_class="CASH",
        lot_size=Decimal("1.0000"),
        is_active=True,
    )
    session.add(cash_inst)

    prices = [
        MarketPrice(id=1, instrument_id="INS-CASH-USD", price=Decimal("1.0000"), price_date=as_of, source="TEST"),
    ]
    session.add_all(prices)

    # Standard flat fee schedule tiers across all asset classes
    fee_schedules = []
    classes = ["EQUITY", "DEBT", "COMMODITIES", "CASH"]
    f_counter = 1
    for ac in classes:
        for side in ["BUY", "SELL"]:
            fee_schedules.append(
                FeeSchedule(
                    fee_schedule_id=f"FEE-{ac}-{side}",
                    asset_class=ac,
                    trade_side=side,
                    min_trade_value=Decimal("0.0000"),
                    max_trade_value=None,
                    fee_rate_bps=Decimal("10.0000") if ac != "CASH" else Decimal("0.0000"),  # 10 bps
                    fixed_fee=Decimal("5.0000") if ac != "CASH" else Decimal("0.0000"),       # $5 flat
                    minimum_fee=Decimal("5.0000") if ac != "CASH" else Decimal("0.0000"),
                    maximum_fee=Decimal("500.0000"),
                    currency="USD",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    is_active=True,
                )
            )
            f_counter += 1
    session.add_all(fee_schedules)
    session.commit()


@pytest.fixture
def db_session():
    """Fixture providing an isolated database session with standard environment."""
    session = _create_sqlite_session()
    yield session
    session.close()


# ==============================================================================
# 1. Overweight asset class generates SELL recommendations
# ==============================================================================

def test_overweight_asset_class_generates_sell(db_session):
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    # Instrument: AAPL (EQUITY), lot_size 1.0000
    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    bnd = Instrument(instrument_id="INS-BND", symbol="BND", instrument_name="Vanguard Bond", asset_class="DEBT", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add_all([aapl, bnd])

    # 100 shares AAPL @ $100 = $10,000 (80% of $12,500 total). Cash: $2,500 (20%).
    # Targets: EQUITY 40%, DEBT 40%, CASH 20%.
    # EQUITY is overweight by 40% ($5,000).
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=3, instrument_id="INS-BND", price=Decimal("50.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("2500.0000"), as_of_date=as_of),
        Holding(holding_id="H-AAPL", portfolio_id="PORT-REBAL-01", instrument_id="INS-AAPL", quantity=Decimal("100.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="EQUITY", target_weight=Decimal("40.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="DEBT", target_weight=Decimal("40.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=3, portfolio_id="PORT-REBAL-01", asset_class="CASH", target_weight=Decimal("20.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    result = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    sells = [t for t in result.proposed_trades if t.trade_side == "SELL"]
    assert len(sells) >= 1
    assert sells[0].instrument_id == "INS-AAPL"
    assert sells[0].trade_side == "SELL"
    # Target sell was $5,000 = 50 shares of AAPL
    assert sells[0].quantity == Decimal("50.0000")
    assert sells[0].trade_value == Decimal("5000.0000")


# ==============================================================================
# 2. Underweight asset class generates BUY recommendations
# ==============================================================================

def test_underweight_asset_class_generates_buy(db_session):
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    bnd = Instrument(instrument_id="INS-BND", symbol="BND", instrument_name="Bond", asset_class="DEBT", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(bnd)
    # Cash: $10,000 (100%). Target: DEBT 50%, CASH 50%.
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-BND", price=Decimal("50.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="DEBT", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="CASH", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    result = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    buys = [t for t in result.proposed_trades if t.trade_side == "BUY"]
    assert len(buys) == 1
    assert buys[0].instrument_id == "INS-BND"
    assert buys[0].trade_side == "BUY"
    assert buys[0].quantity > Decimal("0.0000")


# ==============================================================================
# 3. Sell quantity never exceeds the existing holding
# ==============================================================================

def test_sell_quantity_never_exceeds_existing_holding(db_session):
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    # Holding is 10 AAPL @ $100 = $1,000. Cash is $9,000. Total = $10,000.
    # Target: 0% Equity, 100% Cash.
    # Entire equity must be sold, but CANNOT sell more than 10 shares.
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("9000.0000"), as_of_date=as_of),
        Holding(holding_id="H-AAPL", portfolio_id="PORT-REBAL-01", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="EQUITY", target_weight=Decimal("0.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="CASH", target_weight=Decimal("100.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    result = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    sells = [t for t in result.proposed_trades if t.trade_side == "SELL"]
    assert len(sells) == 1
    assert sells[0].quantity == Decimal("10.0000")
    assert sells[0].quantity <= Decimal("10.0000")


# ==============================================================================
# 4. Sell quantities are integer multiples of Instrument.lot_size
# ==============================================================================

def test_sell_quantities_are_integer_multiples_of_lot_size(db_session):
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    # lot_size is 10.0000
    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("10.0000"), is_active=True)
    db_session.add(aapl)

    # 55 AAPL held @ $100 = $5,500. Cash $4,500. Total $10,000.
    # Target: Equity 30% ($3,000), Cash 70% ($7,000).
    # Ideal sell is $2,500 = 25 shares.
    # With lot_size 10.0000, valid sell must be 20 shares (2 lots), NOT 25!
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("4500.0000"), as_of_date=as_of),
        Holding(holding_id="H-AAPL", portfolio_id="PORT-REBAL-01", instrument_id="INS-AAPL", quantity=Decimal("55.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="EQUITY", target_weight=Decimal("30.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="CASH", target_weight=Decimal("70.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    result = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    sells = [t for t in result.proposed_trades if t.trade_side == "SELL"]
    assert len(sells) == 1
    assert sells[0].quantity == Decimal("20.0000")
    assert (sells[0].quantity % Decimal("10.0000")) == Decimal("0.0000")


# ==============================================================================
# 5. Pro-rata sell allocation across existing positions is deterministic
# ==============================================================================

def test_pro_rata_sell_allocation_is_deterministic(db_session):
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    # Two equity instruments: AAPL and MSFT
    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    msft = Instrument(instrument_id="INS-MSFT", symbol="MSFT", instrument_name="Microsoft", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add_all([aapl, msft])

    # AAPL held: 60 @ $100 = $6,000 (60% of Equity).
    # MSFT held: 40 @ $100 = $4,000 (40% of Equity).
    # Equity total: $10,000. Target: Equity 50% ($5,000), Cash 50% ($5,000).
    # Need to sell $5,000 total from Equity:
    # AAPL share: 60% of $5,000 = $3,000 (30 shares)
    # MSFT share: 40% of $5,000 = $2,000 (20 shares)
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=3, instrument_id="INS-MSFT", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("0.0000"), as_of_date=as_of),
        Holding(holding_id="H-AAPL", portfolio_id="PORT-REBAL-01", instrument_id="INS-AAPL", quantity=Decimal("60.0000"), as_of_date=as_of),
        Holding(holding_id="H-MSFT", portfolio_id="PORT-REBAL-01", instrument_id="INS-MSFT", quantity=Decimal("40.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="CASH", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    result = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    sells = {t.instrument_id: t for t in result.proposed_trades if t.trade_side == "SELL"}
    assert "INS-AAPL" in sells
    assert "INS-MSFT" in sells
    assert sells["INS-AAPL"].quantity == Decimal("30.0000")
    assert sells["INS-MSFT"].quantity == Decimal("20.0000")


# ==============================================================================
# 6. Existing eligible instruments are preferred for buys
# ==============================================================================

def test_existing_eligible_instruments_are_preferred_for_buys(db_session):
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    # Two debt instruments: BND (currently held) and TIP (unheld, but lower instrument_id INS-AAA-TIP)
    tip = Instrument(instrument_id="INS-000-TIP", symbol="TIP", instrument_name="TIPS", asset_class="DEBT", lot_size=Decimal("1.0000"), is_active=True)
    bnd = Instrument(instrument_id="INS-BND", symbol="BND", instrument_name="Bond", asset_class="DEBT", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add_all([tip, bnd])

    # Portfolio holds BND (10 shares @ $50 = $500). Cash = $4,500. Total = $5,000.
    # Target: DEBT 50% ($2,500), CASH 50% ($2,500).
    # Since BND is already held in the portfolio, BUY should select BND, NOT TIP!
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-000-TIP", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=3, instrument_id="INS-BND", price=Decimal("50.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("4500.0000"), as_of_date=as_of),
        Holding(holding_id="H-BND", portfolio_id="PORT-REBAL-01", instrument_id="INS-BND", quantity=Decimal("10.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="DEBT", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="CASH", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    result = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    buys = [t for t in result.proposed_trades if t.trade_side == "BUY"]
    assert len(buys) == 1
    assert buys[0].instrument_id == "INS-BND"


# ==============================================================================
# 7. Unheld underweight asset class selects lowest instrument_id
# ==============================================================================

def test_unheld_underweight_asset_class_selects_lowest_instrument_id(db_session):
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    # Two commodities instruments, neither is held
    gld = Instrument(instrument_id="INS-GLD", symbol="GLD", instrument_name="Gold", asset_class="COMMODITIES", lot_size=Decimal("1.0000"), is_active=True)
    slv = Instrument(instrument_id="INS-SLV", symbol="SLV", instrument_name="Silver", asset_class="COMMODITIES", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add_all([gld, slv])

    # Cash = $10,000. Target: COMMODITIES 20% ($2,000), CASH 80% ($8,000).
    # Lowest instrument_id is INS-GLD.
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-GLD", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=3, instrument_id="INS-SLV", price=Decimal("20.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="COMMODITIES", target_weight=Decimal("20.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="CASH", target_weight=Decimal("80.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    result = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    buys = [t for t in result.proposed_trades if t.trade_side == "BUY"]
    assert len(buys) == 1
    assert buys[0].instrument_id == "INS-GLD"


# ==============================================================================
# 8. Excluded instruments are never recommended for purchase
# ==============================================================================

def test_excluded_instruments_are_never_recommended_for_purchase(db_session):
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    # GLD has lower ID, but is EXCLUDED! SLV is eligible.
    gld = Instrument(instrument_id="INS-GLD", symbol="GLD", instrument_name="Gold", asset_class="COMMODITIES", lot_size=Decimal("1.0000"), is_active=True)
    slv = Instrument(instrument_id="INS-SLV", symbol="SLV", instrument_name="Silver", asset_class="COMMODITIES", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add_all([gld, slv])

    # Constraint excluding GLD
    excl_c = Constraint(
        constraint_id="CST-EXCL-GLD",
        constraint_name="Exclude Gold",
        constraint_type=ConstraintType.EXCLUDED_INSTRUMENT.value,
        scope_type=ScopeType.INSTRUMENT.value,
        scope_reference_id="INS-GLD",
        severity=ConstraintSeverity.HARD.value,
        effective_from=date(2026, 1, 1),
        effective_to=None,
        is_active=True,
    )
    db_session.add(excl_c)

    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-GLD", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=3, instrument_id="INS-SLV", price=Decimal("20.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="COMMODITIES", target_weight=Decimal("20.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="CASH", target_weight=Decimal("80.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    result = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    buys = [t for t in result.proposed_trades if t.trade_side == "BUY"]
    assert len(buys) == 1
    assert buys[0].instrument_id == "INS-SLV"
    assert buys[0].instrument_id != "INS-GLD"


# ==============================================================================
# 9. Buy quantities obey lot-size multiples
# ==============================================================================

def test_buy_quantities_obey_lot_size_multiples(db_session):
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    # lot_size is 25.0000
    bnd = Instrument(instrument_id="INS-BND", symbol="BND", instrument_name="Bond", asset_class="DEBT", lot_size=Decimal("25.0000"), is_active=True)
    db_session.add(bnd)

    # Cash = $10,000. Unit price = $40. Target DEBT = $3,500 (87.5 shares).
    # Multiples of 25: 75 shares ($3,000) or 100 shares ($4,000).
    # Since target is $3,500 and cash allows, integer lot sizing must produce multiple of 25.
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-BND", price=Decimal("40.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="DEBT", target_weight=Decimal("35.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="CASH", target_weight=Decimal("65.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    result = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    buys = [t for t in result.proposed_trades if t.trade_side == "BUY"]
    assert len(buys) == 1
    assert (buys[0].quantity % Decimal("25.0000")) == Decimal("0.0000")


# ==============================================================================
# 10. Buy sizing accounts for fees, not only trade notional
# ==============================================================================

def test_buy_sizing_accounts_for_fees_and_prevents_overdraft(db_session):
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    # AAPL price = $100. Cash = $1,005.
    # If we bought 10 shares ($1,000 notional), fee is $5 fixed + 10 bps ($1.00) = $6.00.
    # Total outlay would be $1,006 > $1,005 (overdraft!).
    # Sizing MUST scale down to 9 shares so notional + fee <= $1,005!
    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("1005.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="EQUITY", target_weight=Decimal("100.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    result = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    buys = [t for t in result.proposed_trades if t.trade_side == "BUY"]
    assert len(buys) == 1
    assert buys[0].trade_value + buys[0].fee_amount <= Decimal("1005.0000")
    assert result.remaining_cash >= Decimal("0.0000")


# ==============================================================================
# 11. Missing applicable fee schedule is explicitly reported as failure/block
# ==============================================================================

def test_missing_applicable_fee_schedule_blocks_trade(db_session):
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    # Deactivate the BUY fee schedule for EQUITY
    eq_buy_fee = db_session.query(FeeSchedule).filter_by(asset_class="EQUITY", trade_side="BUY").first()
    eq_buy_fee.is_active = False
    db_session.commit()

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("5000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="CASH", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    result = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    # Trade should not be silently generated with zero fee; must be BLOCKED
    assert not result.is_executable
    blocked_trades = [t for t in result.proposed_trades if t.status == "BLOCKED"]
    assert len(blocked_trades) == 1
    assert "fee schedule" in blocked_trades[0].diagnostic.lower()


# ==============================================================================
# 12. Total buy outlay never exceeds starting cash plus net sell proceeds
# ==============================================================================

def test_total_buy_outlay_never_exceeds_available_cash_flow(db_session):
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    bnd = Instrument(instrument_id="INS-BND", symbol="BND", instrument_name="Bond", asset_class="DEBT", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add_all([aapl, bnd])

    # AAPL: 50 @ $100 = $5,000. Cash = $100. Total = $5,100.
    # Target: DEBT 80% ($4,080), EQUITY 10% ($510), CASH 10% ($510).
    # Sells AAPL -> generates proceeds -> Buys BND with proceeds.
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=3, instrument_id="INS-BND", price=Decimal("50.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("100.0000"), as_of_date=as_of),
        Holding(holding_id="H-AAPL", portfolio_id="PORT-REBAL-01", instrument_id="INS-AAPL", quantity=Decimal("50.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="EQUITY", target_weight=Decimal("10.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="DEBT", target_weight=Decimal("80.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=3, portfolio_id="PORT-REBAL-01", asset_class="CASH", target_weight=Decimal("10.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    result = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    assert result.is_executable
    assert result.remaining_cash >= Decimal("0.0000")
    assert result.total_buy_notional + result.total_buy_fees <= result.starting_cash + result.total_sell_notional - result.total_sell_fees


# ==============================================================================
# 13. Cash is not sold as an ordinary instrument
# ==============================================================================

def test_cash_is_not_sold_as_ordinary_instrument(db_session):
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    bnd = Instrument(instrument_id="INS-BND", symbol="BND", instrument_name="Bond", asset_class="DEBT", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(bnd)

    # Cash = $10,000 (100%). Target: CASH 20%, DEBT 80%.
    # CASH is overweight by 80%, but no SELL trade for CASH-USD should ever be produced!
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-BND", price=Decimal("50.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="DEBT", target_weight=Decimal("80.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="CASH", target_weight=Decimal("20.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    result = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    cash_sells = [t for t in result.proposed_trades if t.trade_side == "SELL" and t.asset_class == "CASH"]
    assert len(cash_sells) == 0


# ==============================================================================
# 14. Identical inputs produce identical ordered recommendations
# ==============================================================================

def test_identical_inputs_produce_identical_ordered_recommendations(db_session):
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    bnd = Instrument(instrument_id="INS-BND", symbol="BND", instrument_name="Bond", asset_class="DEBT", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add_all([aapl, bnd])

    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=3, instrument_id="INS-BND", price=Decimal("50.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("5000.0000"), as_of_date=as_of),
        Holding(holding_id="H-AAPL", portfolio_id="PORT-REBAL-01", instrument_id="INS-AAPL", quantity=Decimal("50.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="EQUITY", target_weight=Decimal("20.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="DEBT", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=3, portfolio_id="PORT-REBAL-01", asset_class="CASH", target_weight=Decimal("30.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    run1 = service.generate_rebalance_trades("PORT-REBAL-01", as_of)
    run2 = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    assert len(run1.proposed_trades) == len(run2.proposed_trades)
    for t1, t2 in zip(run1.proposed_trades, run2.proposed_trades):
        assert t1.instrument_id == t2.instrument_id
        assert t1.trade_side == t2.trade_side
        assert t1.quantity == t2.quantity
        assert t1.trade_value == t2.trade_value
        assert t1.fee_amount == t2.fee_amount


# ==============================================================================
# 15. Lot-size rounding leaves explicit residual drift
# ==============================================================================

def test_lot_size_rounding_leaves_explicit_residual_drift(db_session):
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    # Large lot size: 50.0000 shares ($5,000 per lot)
    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("50.0000"), is_active=True)
    db_session.add(aapl)

    # Total = $10,000. Cash $10,000. Target: Equity 25% ($2,500).
    # Since 1 lot is $5,000, 0 lots are bought ($0).
    # Target cannot be matched due to lot indivisibility, leaving residual drift!
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("10000.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="EQUITY", target_weight=Decimal("25.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="CASH", target_weight=Decimal("75.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    result = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    assert "EQUITY" in result.residual_drifts
    # Equity remains under target
    assert result.residual_drifts["EQUITY"] < Decimal("0.0000")


# ==============================================================================
# 16. Missing prices or unknown price freshness are not silently safe
# ==============================================================================

def test_missing_prices_raise_error(db_session):
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    # AAPL held, but NO market price seeded!
    db_session.add_all([
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("5000.0000"), as_of_date=as_of),
        Holding(holding_id="H-AAPL", portfolio_id="PORT-REBAL-01", instrument_id="INS-AAPL", quantity=Decimal("10.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="EQUITY", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="CASH", target_weight=Decimal("50.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    with pytest.raises(MissingPriceError):
        service.generate_rebalance_trades("PORT-REBAL-01", as_of)


def test_stale_price_uncertainty_is_diagnosed(db_session):
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    # Price date is 5 days old (2026-01-10)
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=date(2026, 1, 10), source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("5000.0000"), as_of_date=as_of),
        Holding(holding_id="H-AAPL", portfolio_id="PORT-REBAL-01", instrument_id="INS-AAPL", quantity=Decimal("50.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="EQUITY", target_weight=Decimal("20.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="CASH", target_weight=Decimal("80.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    result = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    # Diagnostics must record the staleness/age notice
    assert any("5 day(s) old" in d for d in result.diagnostics)


# ==============================================================================
# Financial Safety Review Tests
# ==============================================================================

def test_blocked_sell_does_not_contribute_proceeds_or_enable_buys(db_session):
    """Verify a blocked SELL does not contribute proceeds to available cash to fund BUYs."""
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    # Deactivate the SELL fee schedule for EQUITY
    eq_sell_fee = db_session.query(FeeSchedule).filter_by(asset_class="EQUITY", trade_side="SELL").first()
    eq_sell_fee.is_active = False
    db_session.commit()

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    bnd = Instrument(instrument_id="INS-BND", symbol="BND", instrument_name="Bond", asset_class="DEBT", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add_all([aapl, bnd])

    # Portfolio: Starting Cash = $0.0000. AAPL = 50 @ $100 = $5,000 (100%).
    # Target: EQUITY 0%, DEBT 100%.
    # Sells AAPL -> but SELL fee schedule is missing, so SELL is BLOCKED!
    # Because SELL is blocked, its $5,000 proceeds CANNOT be used to buy BND!
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=as_of, source="TEST"),
        MarketPrice(id=3, instrument_id="INS-BND", price=Decimal("50.0000"), price_date=as_of, source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("0.0000"), as_of_date=as_of),
        Holding(holding_id="H-AAPL", portfolio_id="PORT-REBAL-01", instrument_id="INS-AAPL", quantity=Decimal("50.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="EQUITY", target_weight=Decimal("0.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="DEBT", target_weight=Decimal("100.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    result = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    assert not result.is_executable
    # Blocked SELL must not count towards executable sell notional
    assert result.total_sell_notional == Decimal("0.0000")
    # No executable BUY trades should be funded because real available cash was $0
    assert result.total_buy_notional == Decimal("0.0000")
    assert len([t for t in result.proposed_trades if t.trade_side == "BUY"]) == 0
    assert result.remaining_cash == Decimal("0.0000")


def test_historical_price_flags_requires_human_review(db_session):
    """Verify unknown price freshness (is_stale=None, price_age_days > 0) sets requires_human_review."""
    as_of = date(2026, 1, 15)
    _seed_standard_environment(db_session, as_of)

    aapl = Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple", asset_class="EQUITY", lot_size=Decimal("1.0000"), is_active=True)
    db_session.add(aapl)

    # 5 days old price
    db_session.add_all([
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("100.0000"), price_date=date(2026, 1, 10), source="TEST"),
        Holding(holding_id="H-CSH", portfolio_id="PORT-REBAL-01", instrument_id="INS-CASH-USD", quantity=Decimal("5000.0000"), as_of_date=as_of),
        Holding(holding_id="H-AAPL", portfolio_id="PORT-REBAL-01", instrument_id="INS-AAPL", quantity=Decimal("50.0000"), as_of_date=as_of),
        TargetAllocation(id=1, portfolio_id="PORT-REBAL-01", asset_class="EQUITY", target_weight=Decimal("20.0000"), effective_from=date(2026, 1, 1), effective_to=None),
        TargetAllocation(id=2, portfolio_id="PORT-REBAL-01", asset_class="CASH", target_weight=Decimal("80.0000"), effective_from=date(2026, 1, 1), effective_to=None),
    ])
    db_session.commit()

    service = RebalancingService(db_session)
    result = service.generate_rebalance_trades("PORT-REBAL-01", as_of)

    assert result.requires_human_review is True
    assert any("5 day(s) old" in d for d in result.diagnostics)


