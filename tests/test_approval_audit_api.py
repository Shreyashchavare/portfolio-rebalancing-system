"""Tests for Phase 6.3 Approval Governance, Audit Service & REST APIs.

Following strict Test-Driven Development (TDD), these tests define contracts and specifications
for human-in-the-loop approval, durable append-only audit events, secure authorization boundaries,
REST endpoints, and canonical idempotency payload comparison.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import os
import tempfile
from typing import Any, Optional
from unittest.mock import MagicMock, patch
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool, StaticPool

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
from app.models.workflow_run import WorkflowRun

# The following imports will fail or are under test for Phase 6.3
from app.models.audit_event import AuditEvent
from app.schemas.approval import (
    ApprovalDecisionResponse,
    ApproveProposalRequest,
    RejectProposalRequest,
    ReviewerContext,
)
from app.schemas.audit import AuditEventResponse, AuditListResponse
from app.schemas.orchestration import (
    IdempotencyConflictError,
    WorkflowRequest,
    WorkflowResponse,
    WorkflowStatus,
)
from app.services.approval.approval_service import (
    ApprovalService,
    InvalidProposalStateError,
    InvalidRejectionReasonError,
    ProposalNotFoundError,
    SafetyInterventionRequiredError,
)
from app.services.audit.audit_service import AuditService
from app.services.orchestration.workflow_service import WorkflowService
from app.api.dependencies import get_auth_verifier, get_current_reviewer


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


def _create_concurrency_file_sqlite_engine() -> tuple[Any, str]:
    """Create a temporary file-backed SQLite database engine for multi-threaded concurrency testing."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="yottaflex_concur_")
    os.close(fd)
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"timeout": 30.0, "check_same_thread": False},
        poolclass=NullPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine, path


def _seed_test_env(session: Session, as_of: date) -> tuple[str, str]:
    """Seed test investor, portfolio, instruments, holdings, fee schedule, and market prices."""
    investor = InvestorProfile(
        investor_id="INV-APP-01",
        name="Approval Test Investor",
        risk_category=RiskCategory.MODERATE,
    )
    session.add(investor)
    session.flush()

    portfolio = Portfolio(
        portfolio_id="PORT-APP-01",
        investor_id="INV-APP-01",
        portfolio_name="Approval Test Portfolio",
        base_currency="USD",
        status=PortfolioStatus.ACTIVE,
    )
    session.add(portfolio)
    session.flush()

    cash_inst = Instrument(
        instrument_id="INS-CASH-USD",
        symbol="USD",
        instrument_name="US Dollar",
        asset_class="CASH",
        lot_size=Decimal("1.0000"),
        is_active=True,
    )
    eq_inst = Instrument(
        instrument_id="INS-AAPL",
        symbol="AAPL",
        instrument_name="Apple Inc.",
        asset_class="EQUITY",
        lot_size=Decimal("1.0000"),
        is_active=True,
    )
    session.add_all([cash_inst, eq_inst])
    session.flush()

    p_cash = MarketPrice(
        id=101,
        instrument_id="INS-CASH-USD",
        price=Decimal("1.0000"),
        price_date=as_of,
        source="SYSTEM",
    )
    p_eq = MarketPrice(
        id=102,
        instrument_id="INS-AAPL",
        price=Decimal("150.0000"),
        price_date=as_of,
        source="SYSTEM",
    )
    session.add_all([p_cash, p_eq])

    h_cash = Holding(
        holding_id="HLD-APP-01",
        portfolio_id="PORT-APP-01",
        instrument_id="INS-CASH-USD",
        quantity=Decimal("10000.0000"),
        as_of_date=as_of,
    )
    h_eq = Holding(
        holding_id="HLD-APP-02",
        portfolio_id="PORT-APP-01",
        instrument_id="INS-AAPL",
        quantity=Decimal("20.0000"),
        as_of_date=as_of,
    )
    session.add_all([h_cash, h_eq])

    for ac in ["EQUITY", "CASH"]:
        for side in ["BUY", "SELL"]:
            session.add(
                FeeSchedule(
                    fee_schedule_id=f"FEE-APP-{ac}-{side}",
                    asset_class=ac,
                    trade_side=side,
                    min_trade_value=Decimal("0.0000"),
                    fee_rate_bps=Decimal("10.0000") if ac != "CASH" else Decimal("0.0000"),
                    fixed_fee=Decimal("1.0000") if ac != "CASH" else Decimal("0.0000"),
                    minimum_fee=Decimal("1.0000") if ac != "CASH" else Decimal("0.0000"),
                    maximum_fee=Decimal("100.0000"),
                    effective_from=date(2020, 1, 1),
                    currency="USD",
                    is_active=True,
                )
            )
    session.commit()
    return portfolio.portfolio_id, "INS-AAPL"


def _create_test_proposal(
    session: Session,
    portfolio_id: str,
    proposal_id: str = "PROP-APP-01",
    status: str = ProposalStatus.PENDING_REVIEW.value,
    decision: str = ReviewDecision.PENDING.value,
    reason: str = None,
    with_blocked_trade: bool = False,
) -> RebalanceProposal:
    """Create a test rebalance proposal with trades for approval/rejection testing."""
    prop = RebalanceProposal(
        proposal_id=proposal_id,
        portfolio_id=portfolio_id,
        status=status,
        review_decision=decision,
        pre_trade_portfolio_value=Decimal("13000.0000"),
        post_trade_portfolio_value=Decimal("13000.0000"),
        review_reason=reason,
    )
    session.add(prop)
    session.flush()

    trade1 = Trade(
        trade_id=f"TRD-{proposal_id}-01",
        proposal_id=proposal_id,
        instrument_id="INS-AAPL",
        trade_side="BUY",
        quantity=Decimal("10.0000"),
        unit_price=Decimal("150.0000"),
        trade_value=Decimal("1500.0000"),
        fee_amount=Decimal("2.5000"),
        status=TradeStatus.PROPOSED.value,
    )
    session.add(trade1)

    if with_blocked_trade:
        trade2 = Trade(
            trade_id=f"TRD-{proposal_id}-02",
            proposal_id=proposal_id,
            instrument_id="INS-AAPL",
            trade_side="SELL",
            quantity=Decimal("5.0000"),
            unit_price=Decimal("150.0000"),
            trade_value=Decimal("750.0000"),
            fee_amount=Decimal("1.7500"),
            status=TradeStatus.BLOCKED.value,
        )
        session.add(trade2)

    session.commit()
    return prop


class TestApprovalGovernance:
    """Tests for Batch A: Approval Governance."""

    def test_01_authorized_reviewer_approves_eligible_proposal(self):
        """1. Authorized reviewer approves an eligible proposal and child trades atomically."""
        session = _create_sqlite_session()
        port_id, inst_id = _seed_test_env(session, date(2026, 3, 31))
        prop = _create_test_proposal(session, port_id, proposal_id="PROP-01")

        service = ApprovalService(session)
        reviewer = ReviewerContext(reviewer_id="REV-ALICE", role="REVIEWER", email="alice@firm.com")

        result = service.approve_proposal(
            proposal_id="PROP-01",
            reviewer=reviewer,
            notes="Compliance verified, optimal rebalance allocation.",
        )

        assert result.proposal_id == "PROP-01"
        assert result.status == ProposalStatus.APPROVED.value
        assert result.review_decision == ReviewDecision.APPROVED.value
        assert result.reviewer_id == "REV-ALICE"
        assert result.reviewed_at is not None

        # Verify DB proposal entity
        refreshed_prop = session.query(RebalanceProposal).filter_by(proposal_id="PROP-01").one()
        assert refreshed_prop.status == ProposalStatus.APPROVED.value
        assert refreshed_prop.review_decision == ReviewDecision.APPROVED.value
        assert refreshed_prop.reviewed_at is not None

        # Verify trades were transitioned from PROPOSED to APPROVED
        trades = session.query(Trade).filter_by(proposal_id="PROP-01").all()
        assert len(trades) == 1
        assert trades[0].status == TradeStatus.APPROVED.value

        # Verify audit event was created atomically
        events = session.query(AuditEvent).filter_by(proposal_id="PROP-01").all()
        assert len(events) == 1
        assert events[0].action == "APPROVE"
        assert events[0].decision == "APPROVED"
        assert events[0].actor_id == "REV-ALICE"

    def test_02_authorized_reviewer_rejects_eligible_proposal_with_reason(self):
        """2. Authorized reviewer rejects an eligible proposal with mandatory reason."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        prop = _create_test_proposal(session, port_id, proposal_id="PROP-02")

        service = ApprovalService(session)
        reviewer = ReviewerContext(reviewer_id="REV-BOB", role="REVIEWER")

        result = service.reject_proposal(
            proposal_id="PROP-02",
            reviewer=reviewer,
            reason="Market volatility exceeds tactical threshold.",
        )

        assert result.proposal_id == "PROP-02"
        assert result.status == ProposalStatus.REJECTED.value
        assert result.review_decision == ReviewDecision.REJECTED.value
        assert result.review_reason == "Market volatility exceeds tactical threshold."
        assert result.reviewer_id == "REV-BOB"

        # Verify trades transitioned to REJECTED
        trades = session.query(Trade).filter_by(proposal_id="PROP-02").all()
        assert len(trades) == 1
        assert trades[0].status == TradeStatus.REJECTED.value

        # Verify audit event
        events = session.query(AuditEvent).filter_by(proposal_id="PROP-02").all()
        assert len(events) == 1
        assert events[0].action == "REJECT"
        assert events[0].decision == "REJECTED"
        assert events[0].reason == "Market volatility exceeds tactical threshold."

    def test_03_empty_rejection_reason_is_rejected(self):
        """3. Empty or whitespace-only rejection reason is rejected with InvalidRejectionReasonError."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(session, port_id, proposal_id="PROP-03")

        service = ApprovalService(session)
        reviewer = ReviewerContext(reviewer_id="REV-BOB", role="REVIEWER")

        with pytest.raises(InvalidRejectionReasonError, match="Rejection reason must not be empty"):
            service.reject_proposal(
                proposal_id="PROP-03",
                reviewer=reviewer,
                reason="   ",
            )

        with pytest.raises(InvalidRejectionReasonError):
            service.reject_proposal(
                proposal_id="PROP-03",
                reviewer=reviewer,
                reason="",
            )

    def test_07_rejected_proposal_cannot_be_approved(self):
        """7. A rejected proposal cannot be approved."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(
            session,
            port_id,
            proposal_id="PROP-07",
            status=ProposalStatus.REJECTED.value,
            decision=ReviewDecision.REJECTED.value,
            reason="Previously rejected",
        )

        service = ApprovalService(session)
        reviewer = ReviewerContext(reviewer_id="REV-ALICE", role="REVIEWER")

        with pytest.raises(InvalidProposalStateError, match="Cannot approve a rejected proposal"):
            service.approve_proposal("PROP-07", reviewer=reviewer)

    def test_08_hard_blocked_proposal_cannot_be_approved(self):
        """8. Hard-blocked or non-executable proposal cannot be approved."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(
            session,
            port_id,
            proposal_id="PROP-08",
            status=ProposalStatus.PENDING_REVIEW.value,
            decision=ReviewDecision.PENDING.value,
            reason="HARD violation: prohibited sector",
            with_blocked_trade=True,
        )

        service = ApprovalService(session)
        reviewer = ReviewerContext(reviewer_id="REV-ALICE", role="REVIEWER")

        with pytest.raises(InvalidProposalStateError, match="hard violations"):
            service.approve_proposal("PROP-08", reviewer=reviewer)

    def test_09_policy_or_explanation_failure_cannot_be_bypassed(self):
        """9. Explanation or policy failure requiring review cannot be bypassed by approval."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        prop = _create_test_proposal(session, port_id, proposal_id="PROP-09")

        # Create linked workflow run marked as REQUIRES_ATTENTION due to policy retrieval failure
        wf = WorkflowRun(
            id="WF-PROP-09",
            portfolio_id=port_id,
            proposal_id=prop.proposal_id,
            status=WorkflowStatus.REQUIRES_ATTENTION.value,
            request_key="KEY-09",
            error_code="POLICY_RETRIEVAL_FAILED",
            error_message="Embedding service unavailable",
        )
        session.add(wf)
        session.commit()

        service = ApprovalService(session)
        reviewer = ReviewerContext(reviewer_id="REV-ALICE", role="REVIEWER")

        with pytest.raises(SafetyInterventionRequiredError, match="safety intervention"):
            service.approve_proposal("PROP-09", reviewer=reviewer)

    def test_10_duplicate_identical_decision_is_safely_handled(self):
        """10. Duplicate identical decision is safely handled idempotently."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(session, port_id, proposal_id="PROP-10")

        service = ApprovalService(session)
        reviewer = ReviewerContext(reviewer_id="REV-ALICE", role="REVIEWER")

        res1 = service.approve_proposal("PROP-10", reviewer=reviewer, notes="First approval")
        assert res1.status == ProposalStatus.APPROVED.value

        # Second approval with same reviewer
        res2 = service.approve_proposal("PROP-10", reviewer=reviewer, notes="Duplicate approval")
        assert res2.status == ProposalStatus.APPROVED.value
        assert res2.proposal_id == res1.proposal_id

        # Exactly 1 approval audit event recorded
        events = session.query(AuditEvent).filter_by(proposal_id="PROP-10", action="APPROVE").all()
        assert len(events) == 1

    def test_11_conflicting_decisions_cannot_both_succeed(self):
        """11. An approved proposal cannot later be rejected without an explicit transition workflow."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(session, port_id, proposal_id="PROP-11")

        service = ApprovalService(session)
        reviewer = ReviewerContext(reviewer_id="REV-ALICE", role="REVIEWER")
        reviewer2 = ReviewerContext(reviewer_id="REV-BOB", role="REVIEWER")

        service.approve_proposal("PROP-11", reviewer=reviewer)

        # Attempt to reject an already approved proposal
        with pytest.raises(InvalidProposalStateError, match="Cannot reject an approved proposal"):
            service.reject_proposal("PROP-11", reviewer=reviewer2, reason="Change of mind")

    def test_concurrent_conflicting_decisions_cannot_both_succeed(self):
        """Concurrent contradictory decisions (approve vs reject) cannot both succeed."""
        engine, db_path = _create_concurrency_file_sqlite_engine()
        try:
            with Session(engine) as init_session:
                port_id, _ = _seed_test_env(init_session, date(2026, 3, 31))
                _create_test_proposal(init_session, port_id, proposal_id="PROP-CONCUR-CONFLICT")

            import concurrent.futures

            reviewer_a = ReviewerContext(reviewer_id="REV-ALICE", role="REVIEWER")
            reviewer_b = ReviewerContext(reviewer_id="REV-BOB", role="REVIEWER")

            session_a = Session(engine)
            session_b = Session(engine)

            service_a = ApprovalService(session_a)
            service_b = ApprovalService(session_b)

            results = []
            errors = []

            def do_approve():
                try:
                    res = service_a.approve_proposal("PROP-CONCUR-CONFLICT", reviewer=reviewer_a)
                    results.append(("APPROVE", res))
                except Exception as e:
                    errors.append(("APPROVE", e))

            def do_reject():
                try:
                    res = service_b.reject_proposal(
                        "PROP-CONCUR-CONFLICT", reviewer=reviewer_b, reason="Concurrent rejection"
                    )
                    results.append(("REJECT", res))
                except Exception as e:
                    errors.append(("REJECT", e))

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                f1 = executor.submit(do_approve)
                f2 = executor.submit(do_reject)
                concurrent.futures.wait([f1, f2])

            assert len(results) == 1, f"Expected exactly 1 successful decision, got {len(results)}"
            assert len(errors) == 1, f"Expected exactly 1 failed decision, got {len(errors)}"
            assert isinstance(errors[0][1], InvalidProposalStateError)

            session_a.close()
            session_b.close()
        finally:
            engine.dispose()
            try:
                os.remove(db_path)
            except OSError:
                pass

    def test_concurrent_identical_decisions_deterministic_idempotent(self):
        """Concurrent identical approval decisions both resolve safely to APPROVED."""
        engine, db_path = _create_concurrency_file_sqlite_engine()
        try:
            with Session(engine) as init_session:
                port_id, _ = _seed_test_env(init_session, date(2026, 3, 31))
                _create_test_proposal(init_session, port_id, proposal_id="PROP-CONCUR-IDEM")

            import concurrent.futures

            reviewer_a = ReviewerContext(reviewer_id="REV-ALICE", role="REVIEWER")
            reviewer_b = ReviewerContext(reviewer_id="REV-BOB", role="REVIEWER")

            session_a = Session(engine)
            session_b = Session(engine)

            service_a = ApprovalService(session_a)
            service_b = ApprovalService(session_b)

            results = []
            errors = []

            def do_approve_a():
                try:
                    res = service_a.approve_proposal("PROP-CONCUR-IDEM", reviewer=reviewer_a)
                    results.append(("A", res))
                except Exception as e:
                    errors.append(("A", e))

            def do_approve_b():
                try:
                    res = service_b.approve_proposal("PROP-CONCUR-IDEM", reviewer=reviewer_b)
                    results.append(("B", res))
                except Exception as e:
                    errors.append(("B", e))

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                f1 = executor.submit(do_approve_a)
                f2 = executor.submit(do_approve_b)
                concurrent.futures.wait([f1, f2])

            assert len(results) == 2, f"Expected both identical decisions to succeed, errors: {errors}"
            for _, res in results:
                assert res.status == ProposalStatus.APPROVED.value
                assert res.review_decision == ReviewDecision.APPROVED.value

            session_a.close()
            session_b.close()
        finally:
            engine.dispose()
            try:
                os.remove(db_path)
            except OSError:
                pass

    def test_12_decision_and_audit_event_persist_atomically(self):
        """12. Decision and audit event persist atomically; roll back on audit failure."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(session, port_id, proposal_id="PROP-12")

        service = ApprovalService(session)
        reviewer = ReviewerContext(reviewer_id="REV-ALICE", role="REVIEWER")

        # Mock audit service to raise an exception
        with patch.object(service.audit_service, "record_event", side_effect=RuntimeError("Audit disk full")):
            with pytest.raises(RuntimeError, match="Audit disk full"):
                service.approve_proposal("PROP-12", reviewer=reviewer)

        # Verify proposal remains PENDING_REVIEW due to rollback
        session.rollback()
        prop = session.query(RebalanceProposal).filter_by(proposal_id="PROP-12").one()
        assert prop.status == ProposalStatus.PENDING_REVIEW.value
        assert prop.review_decision == ReviewDecision.PENDING.value

    def test_16_no_trade_execution_or_holding_mutation_occurs(self):
        """16. Approval strictly does NOT execute trades or mutate holdings/portfolio."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(session, port_id, proposal_id="PROP-16")

        # Snapshot holdings before approval
        h_cash_before = session.query(Holding).filter_by(holding_id="HLD-APP-01").one().quantity
        h_eq_before = session.query(Holding).filter_by(holding_id="HLD-APP-02").one().quantity

        service = ApprovalService(session)
        reviewer = ReviewerContext(reviewer_id="REV-ALICE", role="REVIEWER")
        service.approve_proposal("PROP-16", reviewer=reviewer)

        # Verify holdings after approval are COMPLETELY UNCHANGED
        h_cash_after = session.query(Holding).filter_by(holding_id="HLD-APP-01").one().quantity
        h_eq_after = session.query(Holding).filter_by(holding_id="HLD-APP-02").one().quantity
        assert h_cash_before == h_cash_after
        assert h_eq_before == h_eq_after


class TestAuditService:
    """Tests for Batch B: Audit Service."""

    def test_14_audit_retrieval_is_read_only_and_properly_scoped(self):
        """14. Audit retrieval returns chronologically ordered events scoped by proposal or portfolio."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(session, port_id, proposal_id="PROP-A")
        _create_test_proposal(session, port_id, proposal_id="PROP-B")

        audit = AuditService(session)
        audit.record_event(
            event_type="PROPOSAL_REVIEWED",
            action="APPROVE",
            decision="APPROVED",
            actor_id="REV-01",
            entity_type="PROPOSAL",
            entity_id="PROP-A",
            portfolio_id=port_id,
            proposal_id="PROP-A",
            metadata={"note": "Approved by supervisor"},
        )
        audit.record_event(
            event_type="PROPOSAL_REVIEWED",
            action="REJECT",
            decision="REJECTED",
            actor_id="REV-02",
            entity_type="PROPOSAL",
            entity_id="PROP-B",
            portfolio_id=port_id,
            proposal_id="PROP-B",
            reason="Unbalanced liquidity",
        )
        session.commit()

        # Query proposal A
        events_a = audit.get_events_for_proposal("PROP-A")
        assert len(events_a) == 1
        assert events_a[0].action == "APPROVE"
        assert events_a[0].actor_id == "REV-01"

        # Query portfolio
        events_port = audit.get_events_for_portfolio(port_id)
        assert len(events_port) == 2

    def test_15_audit_events_are_append_only(self):
        """15. AuditService exposes no update or delete APIs."""
        session = _create_sqlite_session()
        audit = AuditService(session)
        assert not hasattr(audit, "update_event")
        assert not hasattr(audit, "delete_event")
        assert not hasattr(audit, "modify_event")


class TestApprovalAndAuditRESTAPI:
    """Tests for Batch C: REST APIs & Authorization Boundaries."""

    def test_04_unauthenticated_reviewer_is_denied_401(self):
        """4. Unauthenticated reviewer receives 401 Unauthorized."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(session, port_id, proposal_id="PROP-API-04")

        app.dependency_overrides[get_db] = lambda: session
        # Do not override get_current_reviewer, so it fails closed
        if get_current_reviewer in app.dependency_overrides:
            del app.dependency_overrides[get_current_reviewer]

        client = TestClient(app)
        res = client.post("/api/v1/proposals/PROP-API-04/approve", json={})
        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        app.dependency_overrides.clear()

    def test_arbitrary_bearer_token_returns_401(self):
        """2. Arbitrary unverified Bearer token returns 401 Unauthorized."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(session, port_id, proposal_id="PROP-API-ARBITRARY")

        app.dependency_overrides[get_db] = lambda: session
        if get_current_reviewer in app.dependency_overrides:
            del app.dependency_overrides[get_current_reviewer]

        client = TestClient(app)
        res = client.post(
            "/api/v1/proposals/PROP-API-ARBITRARY/approve",
            headers={"Authorization": "Bearer arbitrary-unverified-token"},
            json={},
        )
        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        app.dependency_overrides.clear()

    def test_arbitrary_x_reviewer_id_cannot_establish_identity_returns_401(self):
        """3. Arbitrary client-supplied X-Reviewer-Id header returns 401 Unauthorized."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(session, port_id, proposal_id="PROP-API-XID")

        app.dependency_overrides[get_db] = lambda: session
        if get_current_reviewer in app.dependency_overrides:
            del app.dependency_overrides[get_current_reviewer]

        client = TestClient(app)
        res = client.post(
            "/api/v1/proposals/PROP-API-XID/approve",
            headers={"X-Reviewer-Id": "REV-ATTACKER", "X-Reviewer-Role": "ADMIN"},
            json={},
        )
        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        app.dependency_overrides.clear()

    def test_dev_mock_auth_cannot_be_activated_in_production(self, monkeypatch):
        """7. Development mock auth is rejected with RuntimeError if attempted in production."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("ENABLE_DEV_MOCK_AUTH", "true")

        with pytest.raises(RuntimeError, match="cannot be activated in a production environment"):
            get_auth_verifier()

    def test_dev_mock_auth_works_in_development_when_explicitly_enabled(self, monkeypatch):
        """When explicitly enabled in development, verified mock token authenticates successfully."""
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("ENABLE_DEV_MOCK_AUTH", "true")

        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(session, port_id, proposal_id="PROP-API-DEV-AUTH")

        app.dependency_overrides[get_db] = lambda: session
        if get_current_reviewer in app.dependency_overrides:
            del app.dependency_overrides[get_current_reviewer]

        client = TestClient(app)
        # 1. Valid mock reviewer token succeeds
        res = client.post(
            "/api/v1/proposals/PROP-API-DEV-AUTH/approve",
            headers={"Authorization": "Bearer dev-reviewer-token"},
            json={"notes": "Approved via dev mock auth"},
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["reviewer_id"] == "REV-DEV-01"

        # 2. Unknown token still returns 401
        res_bad = client.post(
            "/api/v1/proposals/PROP-API-DEV-AUTH/approve",
            headers={"Authorization": "Bearer dev-unknown-token"},
            json={},
        )
        assert res_bad.status_code == status.HTTP_401_UNAUTHORIZED
        app.dependency_overrides.clear()

    def test_verified_principal_without_permission_receives_403_via_mock(self, monkeypatch):
        """6. Verified principal with VIEWER role receives 403 Forbidden via mock auth."""
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("ENABLE_DEV_MOCK_AUTH", "true")

        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(session, port_id, proposal_id="PROP-API-DEV-VIEWER")

        app.dependency_overrides[get_db] = lambda: session
        if get_current_reviewer in app.dependency_overrides:
            del app.dependency_overrides[get_current_reviewer]

        client = TestClient(app)
        res = client.post(
            "/api/v1/proposals/PROP-API-DEV-VIEWER/approve",
            headers={"Authorization": "Bearer dev-viewer-token"},
            json={},
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN
        app.dependency_overrides.clear()

    def test_05_unauthorized_reviewer_is_denied_403(self):
        """5. Unauthorized reviewer (e.g. read-only role) receives 403 Forbidden."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(session, port_id, proposal_id="PROP-API-05")

        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_reviewer] = lambda: ReviewerContext(
            reviewer_id="REV-GUEST", role="VIEWER"
        )

        client = TestClient(app)
        res = client.post("/api/v1/proposals/PROP-API-05/approve", json={})
        assert res.status_code == status.HTTP_403_FORBIDDEN
        app.dependency_overrides.clear()

    def test_06_client_supplied_reviewer_identity_cannot_impersonate(self):
        """6. Reviewer identity from request body is ignored; uses authenticated principal."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(session, port_id, proposal_id="PROP-API-06")

        app.dependency_overrides[get_db] = lambda: session
        # Authenticated principal is REV-REAL
        app.dependency_overrides[get_current_reviewer] = lambda: ReviewerContext(
            reviewer_id="REV-REAL", role="REVIEWER"
        )

        client = TestClient(app)
        # Attempt to spoof identity via body
        res = client.post(
            "/api/v1/proposals/PROP-API-06/approve",
            json={"reviewer_id": "REV-ATTACKER", "notes": "Approved"},
        )
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["reviewer_id"] == "REV-REAL"  # Trusted principal, not body!

        # Check in DB
        event = session.query(AuditEvent).filter_by(proposal_id="PROP-API-06").one()
        assert event.actor_id == "REV-REAL"
        app.dependency_overrides.clear()

    def test_api_approve_success_flow(self):
        """POST /api/v1/proposals/{id}/approve returns 200 OK and changes state."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(session, port_id, proposal_id="PROP-API-OK")

        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_reviewer] = lambda: ReviewerContext(
            reviewer_id="REV-MANAGER", role="REVIEWER"
        )

        client = TestClient(app)
        res = client.post("/api/v1/proposals/PROP-API-OK/approve", json={"notes": "All good"})
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["status"] == "APPROVED"
        assert data["review_decision"] == "APPROVED"
        assert data["reviewer_id"] == "REV-MANAGER"
        app.dependency_overrides.clear()

    def test_api_reject_requires_reason(self):
        """POST /api/v1/proposals/{id}/reject requires a non-empty reason (422)."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(session, port_id, proposal_id="PROP-API-REJ")

        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_reviewer] = lambda: ReviewerContext(
            reviewer_id="REV-MANAGER", role="REVIEWER"
        )

        client = TestClient(app)
        res = client.post("/api/v1/proposals/PROP-API-REJ/reject", json={"reason": "   "})
        assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        res2 = client.post(
            "/api/v1/proposals/PROP-API-REJ/reject",
            json={"reason": "Drift is within acceptable risk band."},
        )
        assert res2.status_code == status.HTTP_200_OK
        assert res2.json()["status"] == "REJECTED"
        app.dependency_overrides.clear()

    def test_api_get_proposal_audit_events(self):
        """GET /api/v1/proposals/{id}/audit returns audit event trail."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        _create_test_proposal(session, port_id, proposal_id="PROP-API-AUD")

        audit = AuditService(session)
        audit.record_event(
            event_type="PROPOSAL_REVIEWED",
            action="APPROVE",
            decision="APPROVED",
            actor_id="REV-AUDITOR",
            entity_type="PROPOSAL",
            entity_id="PROP-API-AUD",
            portfolio_id=port_id,
            proposal_id="PROP-API-AUD",
        )
        session.commit()

        app.dependency_overrides[get_db] = lambda: session
        client = TestClient(app)
        res = client.get("/api/v1/proposals/PROP-API-AUD/audit")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["action"] == "APPROVE"
        assert data["events"][0]["actor_id"] == "REV-AUDITOR"
        app.dependency_overrides.clear()

    def test_api_get_workflow_by_id(self):
        """GET /api/v1/workflows/{id} returns workflow run details."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))
        wf = WorkflowRun(
            id="WF-GET-01",
            portfolio_id=port_id,
            status=WorkflowStatus.PENDING_HUMAN_REVIEW.value,
            request_key="KEY-GET-01",
            request_payload={"portfolio_id": port_id, "request_key": "KEY-GET-01"},
            result_payload={"requires_human_review": True},
        )
        session.add(wf)
        session.commit()

        app.dependency_overrides[get_db] = lambda: session
        client = TestClient(app)
        res = client.get("/api/v1/workflows/WF-GET-01")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["workflow_id"] == "WF-GET-01"
        assert data["status"] == WorkflowStatus.PENDING_HUMAN_REVIEW.value
        app.dependency_overrides.clear()


class TestBatchDIdempotencyPayloadComparison:
    """Tests for Batch D: Canonical Idempotency Payload Comparison."""

    def test_17_same_key_identical_payload_returns_existing_result(self):
        """17. Same request key with identical full payload returns existing workflow result."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))

        # Target allocation
        session.add_all([
            TargetAllocation(
                portfolio_id=port_id,
                asset_class="CASH",
                target_weight=Decimal("20.0000"),
                effective_from=date(2020, 1, 1),
            ),
            TargetAllocation(
                portfolio_id=port_id,
                asset_class="EQUITY",
                target_weight=Decimal("80.0000"),
                effective_from=date(2020, 1, 1),
            ),
        ])
        session.commit()

        service = WorkflowService(session)
        req1 = WorkflowRequest(
            portfolio_id=port_id,
            as_of_date=date(2026, 3, 31),
            request_key="IDEM-TEST-KEY-01",
            policy_query="Standard mandate limits",
        )
        res1 = service.run_workflow(req1)

        # Same key, identical payload
        req2 = WorkflowRequest(
            portfolio_id=port_id,
            as_of_date=date(2026, 3, 31),
            request_key="IDEM-TEST-KEY-01",
            policy_query="Standard mandate limits",
        )
        res2 = service.run_workflow(req2)

        assert res1.workflow_id == res2.workflow_id
        assert res1.proposal_id == res2.proposal_id

    def test_18_changed_policy_query_raises_idempotency_conflict(self):
        """18. Reusing request key with different policy_query raises IdempotencyConflictError."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))

        session.add_all([
            TargetAllocation(
                portfolio_id=port_id,
                asset_class="CASH",
                target_weight=Decimal("20.0000"),
                effective_from=date(2020, 1, 1),
            ),
            TargetAllocation(
                portfolio_id=port_id,
                asset_class="EQUITY",
                target_weight=Decimal("80.0000"),
                effective_from=date(2020, 1, 1),
            ),
        ])
        session.commit()

        service = WorkflowService(session)
        req1 = WorkflowRequest(
            portfolio_id=port_id,
            as_of_date=date(2026, 3, 31),
            request_key="IDEM-CONFLICT-KEY",
            policy_query="Initial query",
        )
        service.run_workflow(req1)

        # Reusing same key with changed policy_query
        req2 = WorkflowRequest(
            portfolio_id=port_id,
            as_of_date=date(2026, 3, 31),
            request_key="IDEM-CONFLICT-KEY",
            policy_query="Altered policy query that affects behavior",
        )
        with pytest.raises(IdempotencyConflictError, match="policy_query"):
            service.run_workflow(req2)

    def test_19_changed_as_of_date_raises_idempotency_conflict(self):
        """19. Reusing request key with different as_of_date raises IdempotencyConflictError."""
        session = _create_sqlite_session()
        port_id, _ = _seed_test_env(session, date(2026, 3, 31))

        session.add_all([
            TargetAllocation(
                portfolio_id=port_id,
                asset_class="CASH",
                target_weight=Decimal("20.0000"),
                effective_from=date(2020, 1, 1),
            ),
            TargetAllocation(
                portfolio_id=port_id,
                asset_class="EQUITY",
                target_weight=Decimal("80.0000"),
                effective_from=date(2020, 1, 1),
            ),
        ])
        session.commit()

        service = WorkflowService(session)
        req1 = WorkflowRequest(
            portfolio_id=port_id,
            as_of_date=date(2026, 3, 31),
            request_key="IDEM-DATE-CONFLICT",
        )
        service.run_workflow(req1)

        # Reusing same key with changed date
        req2 = WorkflowRequest(
            portfolio_id=port_id,
            as_of_date=date(2026, 4, 1),
            request_key="IDEM-DATE-CONFLICT",
        )
        with pytest.raises(IdempotencyConflictError, match="as_of_date"):
            service.run_workflow(req2)
