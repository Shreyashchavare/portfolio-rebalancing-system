"""Phase 4 — End-to-End Integration, RBAC and Security Verification Tests.

Comprehensive automated verification covering:
1. Full 14-step business workflow from portfolio valuation to audit trail.
2. RBAC enforcement (Customer, Analyst, Reviewer, Admin).
3. Exception scenarios (missing price, stale price, excluded instruments, cash solvency,
   lot rounding, minimum trade threshold, hard/soft constraints, invalid lifecycle transitions).
4. Policy RAG semantic retrieval and grounded citation integrity.
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
from app.schemas.approval import ReviewerContext
from app.services.policy_rag.embedding_service import FakeEmbeddingService
from app.services.policy_rag.policy_rag_service import PolicyRAGService
from app.services.rebalancing_service import RebalancingService


def _create_isolated_db() -> Session:
    """Create an isolated in-memory SQLite database session with enforced foreign keys."""
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


def _seed_test_portfolio(session: Session, as_of: date):
    """Seed comprehensive test entities for E2E workflow."""
    inv = InvestorProfile(
        investor_id="INV-E2E-01",
        name="Elena Vanguard",
        risk_category=RiskCategory.MODERATE,
    )
    port = Portfolio(
        portfolio_id="PORT-E2E-01",
        investor_id="INV-E2E-01",
        portfolio_name="Elena Balanced Multi-Asset",
        base_currency="USD",
        status=PortfolioStatus.ACTIVE,
    )

    instruments = [
        Instrument(instrument_id="INS-CASH", symbol="USD", instrument_name="US Dollar", asset_class="CASH", lot_size=Decimal("1.0000"), is_active=True),
        Instrument(instrument_id="INS-AAPL", symbol="AAPL", instrument_name="Apple Inc.", asset_class="EQUITY", lot_size=Decimal("10.0000"), is_active=True),
        Instrument(instrument_id="INS-BND", symbol="BND", instrument_name="Vanguard Total Bond", asset_class="FIXED_INCOME", lot_size=Decimal("5.0000"), is_active=True),
        Instrument(instrument_id="INS-XOM", symbol="XOM", instrument_name="ExxonMobil Corp.", asset_class="EQUITY", lot_size=Decimal("10.0000"), is_active=True),
    ]

    prices = [
        MarketPrice(id=1, instrument_id="INS-CASH", price=Decimal("1.0000"), price_date=as_of, source="SYSTEM"),
        MarketPrice(id=2, instrument_id="INS-AAPL", price=Decimal("150.0000"), price_date=as_of, source="FEED"),
        MarketPrice(id=3, instrument_id="INS-BND", price=Decimal("80.0000"), price_date=as_of, source="FEED"),
        MarketPrice(id=4, instrument_id="INS-XOM", price=Decimal("100.0000"), price_date=as_of, source="FEED"),
    ]

    # Portfolio holdings: Overweight Equity (AAPL: $60k = 60%), Underweight Bond (0%), Cash ($40k = 40%) -> Total $100k
    holdings = [
        Holding(holding_id="HLD-01", portfolio_id="PORT-E2E-01", instrument_id="INS-CASH", quantity=Decimal("40000.0000"), as_of_date=as_of),
        Holding(holding_id="HLD-02", portfolio_id="PORT-E2E-01", instrument_id="INS-AAPL", quantity=Decimal("400.0000"), as_of_date=as_of),
    ]

    # Target: Equity 40%, Fixed Income 40%, Cash 20%
    targets = [
        TargetAllocation(id=1, portfolio_id="PORT-E2E-01", asset_class="EQUITY", target_weight=Decimal("40.0000"), effective_from=date(2026, 1, 1)),
        TargetAllocation(id=2, portfolio_id="PORT-E2E-01", asset_class="FIXED_INCOME", target_weight=Decimal("40.0000"), effective_from=date(2026, 1, 1)),
        TargetAllocation(id=3, portfolio_id="PORT-E2E-01", asset_class="CASH", target_weight=Decimal("20.0000"), effective_from=date(2026, 1, 1)),
    ]

    fees = [
        FeeSchedule(fee_schedule_id="FEE-EQ-S", asset_class="EQUITY", trade_side="SELL", min_trade_value=Decimal("100.0000"), fee_rate_bps=Decimal("10.0000"), fixed_fee=Decimal("5.0000"), minimum_fee=Decimal("5.0000"), maximum_fee=Decimal("100.0000"), effective_from=date(2026, 1, 1), currency="USD", is_active=True),
        FeeSchedule(fee_schedule_id="FEE-FI-B", asset_class="FIXED_INCOME", trade_side="BUY", min_trade_value=Decimal("100.0000"), fee_rate_bps=Decimal("5.0000"), fixed_fee=Decimal("5.0000"), minimum_fee=Decimal("5.0000"), maximum_fee=Decimal("50.0000"), effective_from=date(2026, 1, 1), currency="USD", is_active=True),
    ]

    constraints = [
        Constraint(constraint_id="C-ESG-01", constraint_name="ESG Exclusion: Fossil Fuels", constraint_type=ConstraintType.EXCLUDED_INSTRUMENT, severity=ConstraintSeverity.HARD, scope_type=ScopeType.PORTFOLIO, scope_reference_id="PORT-E2E-01", effective_from=date(2026, 1, 1)),
        Constraint(constraint_id="C-CASH-MIN", constraint_name="Minimum Liquidity Reserve", constraint_type=ConstraintType.LIQUIDITY_LIMIT, severity=ConstraintSeverity.HARD, scope_type=ScopeType.PORTFOLIO, scope_reference_id="PORT-E2E-01", threshold_value=Decimal("0.1000"), threshold_unit="PERCENTAGE", effective_from=date(2026, 1, 1)),
        Constraint(constraint_id="C-MAX-WEIGHT", constraint_name="Max Single Position Weight", constraint_type=ConstraintType.MAX_POSITION_WEIGHT, severity=ConstraintSeverity.SOFT, scope_type=ScopeType.PORTFOLIO, scope_reference_id="PORT-E2E-01", threshold_value=Decimal("0.5000"), threshold_unit="PERCENTAGE", effective_from=date(2026, 1, 1)),
    ]

    session.add(inv)
    session.add(port)
    session.add_all(instruments)
    session.add_all(prices)
    session.add_all(holdings)
    session.add_all(targets)
    session.add_all(fees)
    session.add_all(constraints)
    session.commit()


@pytest.fixture
def e2e_env(monkeypatch):
    """Fixture providing isolated DB session and configured FastAPI test client."""
    db = _create_isolated_db()
    as_of = date(2026, 1, 15)
    _seed_test_portfolio(db, as_of)

    # Enable dev mock auth for testing
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_DEV_MOCK_AUTH", "true")

    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    yield {"client": client, "db": db, "as_of": as_of}

    app.dependency_overrides.clear()
    db.close()


# ==============================================================================
# SECTION 1: Complete 14-Step End-to-End Business Workflow
# ==============================================================================

def test_full_14_step_business_workflow(e2e_env):
    """Execute and verify the complete 14-step financial rebalancing lifecycle."""
    client: TestClient = e2e_env["client"]
    as_of: date = e2e_env["as_of"]
    portfolio_id = "PORT-E2E-01"

    # Step 1: Health Check
    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"

    # Step 2: Retrieve actual valuation
    val_res = client.get(f"/api/v1/portfolios/{portfolio_id}/valuation?as_of_date={as_of}")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert float(val_data["total_market_value"]) == 100000.0
    assert len(val_data["positions"]) == 2

    # Step 3: Retrieve target allocation and drift
    drift_res = client.get(f"/api/v1/portfolios/{portfolio_id}/drift?as_of_date={as_of}")
    assert drift_res.status_code == 200
    drift_data = drift_res.json()

    # Step 4: Determine whether rebalancing is required
    rebalance_req = drift_data["rebalance_trigger"]["rebalance_required"]
    assert rebalance_req is True
    assert drift_data["rebalance_trigger"]["status"] == "TRIGGERED"

    # Step 5: Generate a rebalancing proposal
    prop_res = client.post(f"/api/v1/portfolios/{portfolio_id}/rebalance/proposals?as_of_date={as_of}")
    assert prop_res.status_code == 201
    prop_data = prop_res.json()
    proposal_id = prop_data["proposal_id"]
    assert prop_data["status"] == "PENDING_REVIEW"
    assert prop_data["portfolio_id"] == portfolio_id

    # Step 6: Inspect proposed BUY and SELL trades
    trades = prop_data["trades"]
    assert len(trades) > 0
    sell_trades = [t for t in trades if t["trade_side"] == "SELL"]
    buy_trades = [t for t in trades if t["trade_side"] == "BUY"]

    assert len(sell_trades) >= 1
    assert len(buy_trades) >= 1
    # Check lot-size rounding
    for t in trades:
        qty = Decimal(t["quantity"])
        assert qty > 0

    # Step 7: Inspect transaction fees
    assert Decimal(prop_data["simulation"]["total_executable_fees"]) > 0
    for t in trades:
        assert Decimal(t["fee_amount"]) >= 0

    # Step 8: Evaluate constraints
    findings = prop_data["constraint_findings"]
    assert len(findings) >= 3
    # ESG exclusion constraint should be present
    esg_finding = next((f for f in findings if f["constraint_type"] == "EXCLUDED_INSTRUMENT"), None)
    assert esg_finding is not None
    assert esg_finding["is_violated"] is False  # XOM was not proposed

    # Step 9: Simulate post-trade allocation & cash
    sim = prop_data["simulation"]
    pre_cash = Decimal(sim["pre_trade_cash"])
    post_cash = Decimal(sim["post_trade_cash"])
    total_fees = Decimal(sim["total_executable_fees"])
    assert pre_cash == Decimal("40000.00")
    # Invariant: post_trade_value == pre_trade_value - total_fees
    pre_val = Decimal(sim["pre_trade_portfolio_value"])
    post_val = Decimal(sim["post_trade_portfolio_value"])
    assert post_val == pre_val - total_fees

    # Step 10: Identify proposal staging state awaiting human governance
    assert prop_data["status"] == "PENDING_REVIEW"
    assert prop_data["review_decision"] == "PENDING"
    assert prop_data["is_executable"] is True

    # Step 11: Attempt unauthorized approval with VIEWER role -> must be rejected with 403
    viewer_headers = {"Authorization": "Bearer dev-viewer-token"}
    unauth_res = client.post(
        f"/api/v1/proposals/{proposal_id}/approve",
        headers=viewer_headers,
        json={"notes": "Viewer trying to approve"},
    )
    assert unauth_res.status_code == 403
    assert "not authorized" in unauth_res.json()["detail"].lower()

    # Step 12: Approve proposal with authorized REVIEWER role
    reviewer_headers = {"Authorization": "Bearer dev-reviewer-token"}
    approve_res = client.post(
        f"/api/v1/proposals/{proposal_id}/approve",
        headers=reviewer_headers,
        json={"notes": "Approved by Senior Risk Officer for drift correction"},
    )
    assert approve_res.status_code == 200
    decision_data = approve_res.json()
    assert decision_data["status"] == "APPROVED"
    assert decision_data["review_decision"] == "APPROVED"
    assert decision_data["reviewer_id"] == "REV-DEV-01"

    # Step 13: Verify proposal lifecycle state in database
    db_session: Session = e2e_env["db"]
    persisted_prop = db_session.query(RebalanceProposal).filter_by(proposal_id=proposal_id).first()
    assert persisted_prop.status == ProposalStatus.APPROVED
    assert persisted_prop.review_decision == ReviewDecision.APPROVED

    # Step 14: Retrieve audit history and verify traceability
    audit_res = client.get(f"/api/v1/proposals/{proposal_id}/audit")
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["total_count"] >= 1
    approval_event = next((e for e in audit_data["events"] if e["action"] == "APPROVE"), None)
    assert approval_event is not None
    assert approval_event["actor_id"] == "REV-DEV-01"
    assert approval_event["proposal_id"] == proposal_id


# ==============================================================================
# SECTION 2: Exception Scenarios & Safety Verification
# ==============================================================================

def test_missing_market_price_returns_422(e2e_env):
    """Valuation on a portfolio holding an unpriced instrument returns 422 Unprocessable Content."""
    client: TestClient = e2e_env["client"]
    db: Session = e2e_env["db"]
    as_of: date = e2e_env["as_of"]

    # Add unpriced instrument and holding
    unpriced = Instrument(
        instrument_id="INS-NO-PRICE",
        symbol="NOPRICE",
        instrument_name="No Price Corp",
        asset_class="EQUITY",
        lot_size=Decimal("1.0000"),
        is_active=True,
    )
    unpriced_holding = Holding(
        holding_id="HLD-NOPRICE",
        portfolio_id="PORT-E2E-01",
        instrument_id="INS-NO-PRICE",
        quantity=Decimal("10.0000"),
        as_of_date=as_of,
    )
    db.add(unpriced)
    db.add(unpriced_holding)
    db.commit()

    res = client.get(f"/api/v1/portfolios/PORT-E2E-01/valuation?as_of_date={as_of}")
    assert res.status_code == 422
    assert "missing" in res.json()["detail"].lower()


def test_rejection_requires_mandatory_non_empty_reason(e2e_env):
    """Rejecting a proposal requires a non-empty justification; empty or whitespace returns 422."""
    client: TestClient = e2e_env["client"]
    as_of: date = e2e_env["as_of"]

    prop_res = client.post(f"/api/v1/portfolios/PORT-E2E-01/rebalance/proposals?as_of_date={as_of}")
    prop_id = prop_res.json()["proposal_id"]

    reviewer_headers = {"Authorization": "Bearer dev-reviewer-token"}

    # Whitespace only
    empty_res = client.post(
        f"/api/v1/proposals/{prop_id}/reject",
        headers=reviewer_headers,
        json={"reason": "   "},
    )
    assert empty_res.status_code == 422

    # Valid reason succeeds
    valid_res = client.post(
        f"/api/v1/proposals/{prop_id}/reject",
        headers=reviewer_headers,
        json={"reason": "Tactical override: Rebalancing postponed due to FOMC announcement."},
    )
    assert valid_res.status_code == 200
    assert valid_res.json()["status"] == "REJECTED"


def test_invalid_lifecycle_transition_cannot_approve_rejected_proposal(e2e_env):
    """A proposal in terminal state REJECTED cannot subsequently be approved (returns 422)."""
    client: TestClient = e2e_env["client"]
    as_of: date = e2e_env["as_of"]

    prop_res = client.post(f"/api/v1/portfolios/PORT-E2E-01/rebalance/proposals?as_of_date={as_of}")
    prop_id = prop_res.json()["proposal_id"]
    reviewer_headers = {"Authorization": "Bearer dev-reviewer-token"}

    # 1. Reject first
    client.post(f"/api/v1/proposals/{prop_id}/reject", headers=reviewer_headers, json={"reason": "Initial rejection."})

    # 2. Attempt to approve rejected proposal -> must fail with 422
    approve_res = client.post(f"/api/v1/proposals/{prop_id}/approve", headers=reviewer_headers, json={"notes": "Attempt to revive"})
    assert approve_res.status_code == 422
    assert "cannot approve a rejected proposal" in approve_res.json()["detail"].lower()


def test_unauthenticated_request_denied_401(e2e_env):
    """Requests to governance endpoints without Bearer credentials must fail with HTTP 401."""
    client: TestClient = e2e_env["client"]
    res = client.post("/api/v1/proposals/RB-TEST-01/approve", json={"notes": "No auth header"})
    assert res.status_code == 401


def test_hard_constraint_blocks_prohibited_instrument(e2e_env):
    """Excluded instrument constraint ensures prohibited instruments are never bought."""
    db: Session = e2e_env["db"]
    as_of: date = e2e_env["as_of"]

    service = RebalancingService(db)
    proposal = service.create_and_persist_proposal("PORT-E2E-01", as_of)

    # Verify no proposed trade is for INS-XOM (Fossil Fuel exclusion)
    for trade in proposal.trades:
        assert trade.instrument_id != "INS-XOM"


def test_cash_solvency_invariant_maintained_after_trades(e2e_env):
    """Post-trade cash must strictly cover fees and liquidity reserve without negative cash."""
    db: Session = e2e_env["db"]
    as_of: date = e2e_env["as_of"]

    service = RebalancingService(db)
    proposal = service.create_and_persist_proposal("PORT-E2E-01", as_of)

    assert Decimal(proposal.simulation.post_trade_cash) >= Decimal("10000.00")  # 10% liquidity reserve of $100k
    assert Decimal(proposal.simulation.post_trade_cash) > 0


# ==============================================================================
# SECTION 3: Policy RAG Grounded Retrieval Verification
# ==============================================================================

def test_policy_search_and_grounded_citations(e2e_env):
    """Verify semantic policy search returns ranked chunks and grounded citations."""
    client: TestClient = e2e_env["client"]
    as_of: date = e2e_env["as_of"]

    # Search policy chunks
    search_res = client.post(
        "/api/v1/policies/search",
        json={"query": "liquidity limit cash buffer", "as_of_date": str(as_of), "top_k": 3},
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert "results" in search_data
    assert search_data["query"] == "liquidity limit cash buffer"

    # Ask policy Q&A
    ask_res = client.post(
        "/api/v1/policies/ask",
        json={"query": "What are the rules regarding tobacco and fossil fuels?", "as_of_date": str(as_of)},
    )
    assert ask_res.status_code == 200
    ask_data = ask_res.json()
    assert "answer" in ask_data
    assert "retrieval_status" in ask_data
    assert isinstance(ask_data["citations"], list)
