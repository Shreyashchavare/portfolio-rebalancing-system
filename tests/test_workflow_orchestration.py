"""Tests for Phase 6.1 Workflow Orchestration Engine and Persistence.

Following strict TDD, these tests verify:
1. WorkflowRun persistence and database constraints.
2. Typed workflow state machine transitions and terminal state protection.
3. End-to-end orchestration across Analytics, Rebalancing, and Policy RAG services.
4. Exactly-once proposal generation and reuse.
5. Idempotency guarantees (same key same payload vs different payload).
6. Failure handling, partial-failure proposal preservation, and error recording.
7. Inviolable financial safety invariants (unmodified holdings, unbypassed constraints).
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from unittest.mock import MagicMock, patch
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import BaseAuthenticationVerifier, get_auth_verifier
from app.database.session import get_db
from app.main import app
from app.schemas.approval import ReviewerContext

from app.models.base import Base
from app.models.constraint import Constraint, ConstraintSeverity, ConstraintType, ScopeType
from app.models.fee_schedule import FeeSchedule
from app.models.holding import Holding
from app.models.instrument import Instrument
from app.models.investor_profile import InvestorProfile, RiskCategory
from app.models.market_price import MarketPrice
from app.models.policy_document import PolicyDocument, PolicyStatus
from app.models.portfolio import Portfolio, PortfolioStatus
from app.models.rebalance_proposal import ProposalStatus, RebalanceProposal, ReviewDecision
from app.models.target_allocation import TargetAllocation
from app.models.workflow_run import WorkflowRun
from app.schemas.orchestration import (
    IdempotencyConflictError,
    InvalidStateTransitionError,
    WorkflowExecutionError,
    WorkflowRequest,
    WorkflowResponse,
    WorkflowStatus,
)
from app.schemas.policy_rag import PolicySearchResult
from app.schemas.rebalancing import RebalanceProposalResponse
from app.services.orchestration.workflow_context import WorkflowContext
from app.services.orchestration.workflow_executor import WorkflowExecutor
from app.services.orchestration.workflow_service import WorkflowService
from app.services.orchestration.workflow_state import (
    ALLOWED_TRANSITIONS,
    is_terminal,
    validate_transition,
)
from app.services.policy_rag.policy_rag_service import PolicyRAGService
from app.services.portfolio_analytics_service import PortfolioAnalyticsService, PortfolioNotFoundError
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


def _seed_test_portfolio(session: Session, as_of: date) -> tuple[str, str]:
    """Seed test investor, portfolio, instruments, holdings, fee schedule, and prices."""
    investor = InvestorProfile(
        investor_id="INV-WF-01",
        name="Workflow Test Investor",
        risk_category=RiskCategory.MODERATE,
    )
    session.add(investor)
    session.flush()

    portfolio = Portfolio(
        portfolio_id="PORT-WF-01",
        investor_id="INV-WF-01",
        portfolio_name="Workflow Growth Portfolio",
        base_currency="USD",
        status=PortfolioStatus.ACTIVE,
    )
    session.add(portfolio)
    session.flush()

    # Instruments
    cash_inst = Instrument(
        instrument_id="INS-CASH-USD",
        symbol="USD",
        instrument_name="US Dollar Cash",
        asset_class="CASH",
        lot_size=Decimal("1.0000"),
        is_active=True,
    )
    eq_inst = Instrument(
        instrument_id="INS-AAPL",
        symbol="AAPL",
        instrument_name="Apple Inc",
        asset_class="EQUITY",
        lot_size=Decimal("1.0000"),
        is_active=True,
    )
    session.add_all([cash_inst, eq_inst])
    session.flush()

    # Standard flat fee schedule tiers across all asset classes
    classes = ["EQUITY", "DEBT", "COMMODITIES", "CASH"]
    for ac in classes:
        for side in ["BUY", "SELL"]:
            session.add(
                FeeSchedule(
                    fee_schedule_id=f"FEE-WF-{ac}-{side}",
                    asset_class=ac,
                    trade_side=side,
                    min_trade_value=Decimal("0.0000"),
                    max_trade_value=None,
                    fee_rate_bps=Decimal("10.0000") if ac != "CASH" else Decimal("0.0000"),
                    fixed_fee=Decimal("5.0000") if ac != "CASH" else Decimal("0.0000"),
                    minimum_fee=Decimal("5.0000") if ac != "CASH" else Decimal("0.0000"),
                    maximum_fee=Decimal("500.0000"),
                    currency="USD",
                    effective_from=date(2020, 1, 1),
                    effective_to=None,
                    is_active=True,
                )
            )

    # Prices
    p_cash = MarketPrice(
        id=101,
        instrument_id="INS-CASH-USD",
        price=Decimal("1.0000"),
        price_date=as_of,
        source="TEST",
    )
    p_eq = MarketPrice(
        id=102,
        instrument_id="INS-AAPL",
        price=Decimal("150.0000"),
        price_date=as_of,
        source="TEST",
    )
    session.add_all([p_cash, p_eq])

    # Target allocation
    t_cash = TargetAllocation(
        portfolio_id="PORT-WF-01",
        asset_class="CASH",
        target_weight=Decimal("20.0000"),
        effective_from=date(2020, 1, 1),
    )
    t_eq = TargetAllocation(
        portfolio_id="PORT-WF-01",
        asset_class="EQUITY",
        target_weight=Decimal("80.0000"),
        effective_from=date(2020, 1, 1),
    )
    session.add_all([t_cash, t_eq])

    # Holdings
    h_cash = Holding(
        holding_id="HLD-WF-CASH",
        portfolio_id="PORT-WF-01",
        instrument_id="INS-CASH-USD",
        quantity=Decimal("50000.0000"),
        as_of_date=as_of,
    )
    h_eq = Holding(
        holding_id="HLD-WF-AAPL",
        portfolio_id="PORT-WF-01",
        instrument_id="INS-AAPL",
        quantity=Decimal("100.0000"),
        as_of_date=as_of,
    )
    session.add_all([h_cash, h_eq])
    session.commit()

    return "PORT-WF-01", "INS-AAPL"


# ==============================================================================
# 1. State Machine & Transition Tests
# ==============================================================================


class TestWorkflowStateMachine:
    """Tests for typed workflow status, transition validator, and terminal protection."""

    def test_workflow_status_enum_values(self):
        """Verify all proposed states exist in WorkflowStatus."""
        expected_states = {
            "RECEIVED",
            "VALIDATING",
            "ANALYZING",
            "GENERATING_PROPOSAL",
            "RETRIEVING_POLICIES",
            "GENERATING_EXPLANATION",
            "PENDING_HUMAN_REVIEW",
            "APPROVED",
            "REJECTED",
            "COMPLETED",
            "FAILED",
            "REQUIRES_ATTENTION",
        }
        actual_states = {s.value for s in WorkflowStatus}
        assert expected_states == actual_states

    def test_valid_transitions_pipeline(self):
        """Verify standard forward progression through pipeline is permitted."""
        valid_chain = [
            (WorkflowStatus.RECEIVED, WorkflowStatus.VALIDATING),
            (WorkflowStatus.VALIDATING, WorkflowStatus.ANALYZING),
            (WorkflowStatus.ANALYZING, WorkflowStatus.GENERATING_PROPOSAL),
            (WorkflowStatus.GENERATING_PROPOSAL, WorkflowStatus.RETRIEVING_POLICIES),
            (WorkflowStatus.RETRIEVING_POLICIES, WorkflowStatus.PENDING_HUMAN_REVIEW),
            (WorkflowStatus.PENDING_HUMAN_REVIEW, WorkflowStatus.APPROVED),
            (WorkflowStatus.APPROVED, WorkflowStatus.COMPLETED),
        ]
        for src, dst in valid_chain:
            validate_transition(src, dst)

    def test_invalid_transitions_rejected(self):
        """Verify illegal skips or backwards steps raise InvalidStateTransitionError."""
        illegal_transitions = [
            (WorkflowStatus.RECEIVED, WorkflowStatus.APPROVED),
            (WorkflowStatus.ANALYZING, WorkflowStatus.COMPLETED),
            (WorkflowStatus.PENDING_HUMAN_REVIEW, WorkflowStatus.VALIDATING),
            (WorkflowStatus.GENERATING_PROPOSAL, WorkflowStatus.ANALYZING),
        ]
        for src, dst in illegal_transitions:
            with pytest.raises(InvalidStateTransitionError):
                validate_transition(src, dst)

    def test_terminal_state_protection(self):
        """Verify terminal states (COMPLETED, REJECTED, FAILED) cannot transition to any state."""
        terminal_states = [WorkflowStatus.COMPLETED, WorkflowStatus.REJECTED, WorkflowStatus.FAILED]
        for term in terminal_states:
            assert is_terminal(term) is True
            for dst in WorkflowStatus:
                with pytest.raises(InvalidStateTransitionError):
                    validate_transition(term, dst)

    def test_rejected_proposal_cannot_transition_to_approved(self):
        """Financial safety: a proposal that is REJECTED or has hard violations can NEVER transition workflow to APPROVED."""
        mock_proposal = MagicMock(spec=RebalanceProposalResponse)
        mock_proposal.status = "REJECTED"
        mock_proposal.review_decision = "REJECTED"
        mock_proposal.is_executable = False

        context = MagicMock()
        context.proposal_result = mock_proposal

        with pytest.raises(InvalidStateTransitionError) as exc_info:
            validate_transition(
                WorkflowStatus.PENDING_HUMAN_REVIEW,
                WorkflowStatus.APPROVED,
                context=context,
            )
        assert "REJECTED" in str(exc_info.value) or "hard violation" in str(exc_info.value)


# ==============================================================================
# 2. Workflow Persistence Model Tests
# ==============================================================================


class TestWorkflowPersistence:
    """Tests for WorkflowRun SQLAlchemy model, foreign keys, and idempotency constraints."""

    def test_workflow_run_table_and_persistence(self):
        """Verify WorkflowRun model creates table, persists fields, and loads correctly."""
        session = _create_sqlite_session()
        as_of = date(2025, 1, 15)
        portfolio_id, _ = _seed_test_portfolio(session, as_of)

        run = WorkflowRun(
            id="WF-20250115-0001",
            portfolio_id=portfolio_id,
            status=WorkflowStatus.RECEIVED.value,
            request_key="req-key-001",
            request_payload={"portfolio_id": portfolio_id, "as_of_date": "2025-01-15"},
            started_at=datetime.now(timezone.utc),
        )
        session.add(run)
        session.commit()

        loaded = session.get(WorkflowRun, "WF-20250115-0001")
        assert loaded is not None
        assert loaded.id == "WF-20250115-0001"
        assert loaded.portfolio_id == portfolio_id
        assert loaded.status == WorkflowStatus.RECEIVED.value
        assert loaded.request_payload == {"portfolio_id": portfolio_id, "as_of_date": "2025-01-15"}
        assert loaded.proposal_id is None
        assert loaded.error_code is None

    def test_idempotency_database_unique_constraint(self):
        """Verify database enforces uniqueness on (portfolio_id, request_key)."""
        session = _create_sqlite_session()
        as_of = date(2025, 1, 15)
        portfolio_id, _ = _seed_test_portfolio(session, as_of)

        run1 = WorkflowRun(
            id="WF-20250115-0001",
            portfolio_id=portfolio_id,
            status=WorkflowStatus.RECEIVED.value,
            request_key="dup-key-001",
            request_payload={"portfolio_id": portfolio_id},
        )
        session.add(run1)
        session.commit()

        run2 = WorkflowRun(
            id="WF-20250115-0002",
            portfolio_id=portfolio_id,
            status=WorkflowStatus.RECEIVED.value,
            request_key="dup-key-001",  # Same portfolio, same request_key
            request_payload={"portfolio_id": portfolio_id},
        )
        session.add(run2)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


# ==============================================================================
# 3. Service Orchestration & Integration Tests
# ==============================================================================


class TestWorkflowOrchestrationService:
    """Tests for WorkflowService orchestrating Analytics, Rebalancing, and Policy RAG."""

    def test_orchestration_executes_pipeline_end_to_end(self):
        """Verify successful workflow execution coordinates analytics, proposal creation, and policy search."""
        session = _create_sqlite_session()
        as_of = date(2025, 1, 15)
        portfolio_id, _ = _seed_test_portfolio(session, as_of)

        # Mock policy RAG returning active policy chunk
        mock_policy_rag = MagicMock(spec=PolicyRAGService)
        mock_policy_rag.search_policies.return_value = [
            PolicySearchResult(
                chunk_id="chk-001",
                document_id="doc-001",
                policy_family_id="FAM-EQUITY-01",
                document_title="Global Equity Policy",
                document_version="1.0",
                section_title="Target Bands",
                content="Equity target allocation must be maintained between 70% and 90%.",
                similarity_score=0.88,
                token_count=18,
            )
        ]

        service = WorkflowService(
            session=session,
            policy_rag_service=mock_policy_rag,
        )

        req = WorkflowRequest(
            portfolio_id=portfolio_id,
            as_of_date=as_of,
            request_key="wf-e2e-001",
        )

        resp = service.run_workflow(req)

        # Verification
        assert resp.portfolio_id == portfolio_id
        assert resp.as_of_date == as_of
        assert resp.proposal_id is not None
        assert resp.status == WorkflowStatus.PENDING_HUMAN_REVIEW.value
        assert resp.proposal is not None
        assert resp.proposal.proposal_id == resp.proposal_id
        assert len(resp.policy_evidence) == 1
        assert resp.policy_evidence[0].document_title == "Global Equity Policy"

        # Verify DB record
        run_record = session.get(WorkflowRun, resp.workflow_id)
        assert run_record is not None
        assert run_record.status == WorkflowStatus.PENDING_HUMAN_REVIEW.value
        assert run_record.proposal_id == resp.proposal_id
        assert run_record.completed_at is not None

        # Verify PolicyRAG was called with exact as_of date
        mock_policy_rag.search_policies.assert_called_once()
        _, kwargs = mock_policy_rag.search_policies.call_args
        assert kwargs["as_of_date"] == as_of

    def test_proposal_generation_invoked_exactly_once(self):
        """Verify proposal generation is called exactly once during workflow execution."""
        session = _create_sqlite_session()
        as_of = date(2025, 1, 15)
        portfolio_id, _ = _seed_test_portfolio(session, as_of)

        mock_policy_rag = MagicMock(spec=PolicyRAGService)
        mock_policy_rag.search_policies.return_value = []

        service = WorkflowService(session=session, policy_rag_service=mock_policy_rag)

        with patch.object(
            service.rebalancing_service,
            "create_and_persist_proposal",
            wraps=service.rebalancing_service.create_and_persist_proposal,
        ) as spy_create:
            req = WorkflowRequest(
                portfolio_id=portfolio_id,
                as_of_date=as_of,
                request_key="wf-once-001",
            )
            resp = service.run_workflow(req)
            assert spy_create.call_count == 1
            assert resp.proposal_id is not None

    def test_proposal_with_hard_violations_transitions_to_rejected(self):
        """Verify proposals with hard violations transition workflow to REJECTED."""
        session = _create_sqlite_session()
        as_of = date(2025, 1, 15)
        portfolio_id, eq_id = _seed_test_portfolio(session, as_of)

        # Add active hard constraint that violates portfolio (MAX_POSITION_WEIGHT 5% when equity is ~23%)
        hard_constraint = Constraint(
            constraint_id="CST-HARD-01",
            constraint_name="Max Position Weight 5%",
            constraint_type="MAX_POSITION_WEIGHT",
            scope_type="PORTFOLIO",
            scope_reference_id=portfolio_id,
            threshold_value=Decimal("5.0000"),
            severity="HARD",
            is_active=True,
            effective_from=date(2020, 1, 1),
        )
        session.add(hard_constraint)
        session.commit()

        mock_policy_rag = MagicMock(spec=PolicyRAGService)
        mock_policy_rag.search_policies.return_value = []

        service = WorkflowService(session=session, policy_rag_service=mock_policy_rag)
        req = WorkflowRequest(
            portfolio_id=portfolio_id,
            as_of_date=as_of,
            request_key="wf-rejected-001",
        )
        resp = service.run_workflow(req)

        assert resp.status == WorkflowStatus.REJECTED.value
        assert resp.proposal.status == "REJECTED"
        assert resp.proposal.review_decision == "REJECTED"


# ==============================================================================
# 4. Idempotency Tests
# ==============================================================================


class TestWorkflowIdempotency:
    """Tests for idempotent request deduplication and payload mismatch rejection."""

    def test_same_request_key_same_payload_returns_existing_run_without_duplicate(self):
        """Verify identical repeated request returns original workflow and does NOT create new proposal."""
        session = _create_sqlite_session()
        as_of = date(2025, 1, 15)
        portfolio_id, _ = _seed_test_portfolio(session, as_of)

        mock_policy_rag = MagicMock(spec=PolicyRAGService)
        mock_policy_rag.search_policies.return_value = []

        service = WorkflowService(session=session, policy_rag_service=mock_policy_rag)

        req1 = WorkflowRequest(
            portfolio_id=portfolio_id,
            as_of_date=as_of,
            request_key="idem-key-100",
        )
        resp1 = service.run_workflow(req1)

        proposal_count_initial = session.query(RebalanceProposal).count()
        workflow_count_initial = session.query(WorkflowRun).count()
        assert proposal_count_initial == 1
        assert workflow_count_initial == 1

        # Second request with SAME request_key and SAME payload
        req2 = WorkflowRequest(
            portfolio_id=portfolio_id,
            as_of_date=as_of,
            request_key="idem-key-100",
        )
        resp2 = service.run_workflow(req2)

        # Verification: same workflow_id, same proposal_id, no new DB rows
        assert resp2.workflow_id == resp1.workflow_id
        assert resp2.proposal_id == resp1.proposal_id
        assert session.query(RebalanceProposal).count() == proposal_count_initial
        assert session.query(WorkflowRun).count() == workflow_count_initial

    def test_same_request_key_different_payload_is_rejected(self):
        """Verify reusing request_key with altered payload raises IdempotencyConflictError."""
        session = _create_sqlite_session()
        as_of = date(2025, 1, 15)
        portfolio_id, _ = _seed_test_portfolio(session, as_of)

        mock_policy_rag = MagicMock(spec=PolicyRAGService)
        mock_policy_rag.search_policies.return_value = []

        service = WorkflowService(session=session, policy_rag_service=mock_policy_rag)

        req1 = WorkflowRequest(
            portfolio_id=portfolio_id,
            as_of_date=as_of,
            request_key="idem-key-conflict",
        )
        service.run_workflow(req1)

        # Altered as_of_date with same request_key
        req2 = WorkflowRequest(
            portfolio_id=portfolio_id,
            as_of_date=date(2025, 1, 20),  # Different date!
            request_key="idem-key-conflict",
        )
        with pytest.raises(IdempotencyConflictError) as exc_info:
            service.run_workflow(req2)

        assert "different request data" in str(exc_info.value).lower() or "conflict" in str(exc_info.value).lower()


# ==============================================================================
# 5. Failure Handling & Financial Safety Tests
# ==============================================================================


class TestWorkflowFailureHandling:
    """Tests for analytics failure, policy retrieval failure, and proposal preservation."""

    def test_analytics_failure_marks_workflow_failed(self):
        """Verify failure during analytics records safe failure without creating proposal."""
        session = _create_sqlite_session()
        as_of = date(2025, 1, 15)
        portfolio_id, _ = _seed_test_portfolio(session, as_of)

        # Remove market prices to trigger MissingPriceError in analytics
        session.query(MarketPrice).delete()
        session.commit()

        mock_policy_rag = MagicMock(spec=PolicyRAGService)
        service = WorkflowService(session=session, policy_rag_service=mock_policy_rag)

        req = WorkflowRequest(
            portfolio_id=portfolio_id,
            as_of_date=as_of,
            request_key="wf-fail-analytics",
        )

        with pytest.raises(WorkflowExecutionError):
            service.run_workflow(req)

        # Workflow run record must exist with status FAILED
        run_record = (
            session.query(WorkflowRun)
            .filter_by(portfolio_id=portfolio_id, request_key="wf-fail-analytics")
            .first()
        )
        assert run_record is not None
        assert run_record.status == WorkflowStatus.FAILED.value
        assert run_record.error_code is not None
        assert run_record.proposal_id is None
        assert session.query(RebalanceProposal).count() == 0

    def test_policy_retrieval_failure_preserves_persisted_proposal(self):
        """Verify failure in policy retrieval after proposal creation preserves proposal and sets REQUIRES_ATTENTION."""
        session = _create_sqlite_session()
        as_of = date(2025, 1, 15)
        portfolio_id, _ = _seed_test_portfolio(session, as_of)

        mock_policy_rag = MagicMock(spec=PolicyRAGService)
        mock_policy_rag.search_policies.side_effect = RuntimeError("Policy vector store timeout")

        service = WorkflowService(session=session, policy_rag_service=mock_policy_rag)

        req = WorkflowRequest(
            portfolio_id=portfolio_id,
            as_of_date=as_of,
            request_key="wf-fail-policy",
        )

        resp = service.run_workflow(req)

        # Critical assertions:
        # 1. Proposal was NOT rolled back or destroyed
        assert resp.proposal_id is not None
        persisted_proposal = session.get(RebalanceProposal, resp.proposal_id)
        assert persisted_proposal is not None

        # 2. Workflow status reflects attention / policy failure
        assert resp.status in (WorkflowStatus.REQUIRES_ATTENTION.value, WorkflowStatus.PENDING_HUMAN_REVIEW.value)
        assert resp.requires_human_review is True
        assert any("policy" in w.lower() for w in resp.warnings)

        # 3. DB run record preserves proposal_id
        run_record = session.get(WorkflowRun, resp.workflow_id)
        assert run_record.proposal_id == resp.proposal_id

    def test_financial_safety_holdings_are_never_mutated(self):
        """Verify holdings and portfolio state in the database are not altered by workflow execution."""
        session = _create_sqlite_session()
        as_of = date(2025, 1, 15)
        portfolio_id, _ = _seed_test_portfolio(session, as_of)

        initial_holdings = {
            h.holding_id: (h.instrument_id, h.quantity)
            for h in session.query(Holding).filter_by(portfolio_id=portfolio_id).all()
        }

        mock_policy_rag = MagicMock(spec=PolicyRAGService)
        mock_policy_rag.search_policies.return_value = []
        service = WorkflowService(session=session, policy_rag_service=mock_policy_rag)

        req = WorkflowRequest(
            portfolio_id=portfolio_id,
            as_of_date=as_of,
            request_key="wf-safety-holdings",
        )
        service.run_workflow(req)

        # Check holdings after workflow
        post_holdings = {
            h.holding_id: (h.instrument_id, h.quantity)
            for h in session.query(Holding).filter_by(portfolio_id=portfolio_id).all()
        }
        assert initial_holdings == post_holdings

    def test_missing_policy_evidence_does_not_fail_workflow_but_flags_human_review(self):
        """Invariant: Missing policy evidence is never treated as compliance, flags human review."""
        session = _create_sqlite_session()
        as_of = date(2025, 1, 15)
        portfolio_id, _ = _seed_test_portfolio(session, as_of)

        mock_policy_rag = MagicMock(spec=PolicyRAGService)
        # Return empty list (no matching policies found)
        mock_policy_rag.search_policies.return_value = []

        service = WorkflowService(session=session, policy_rag_service=mock_policy_rag)

        req = WorkflowRequest(
            portfolio_id=portfolio_id,
            as_of_date=as_of,
            request_key="wf-no-policy-evidence",
        )
        resp = service.run_workflow(req)

        assert resp.proposal_id is not None
        assert resp.requires_human_review is True
        assert any("no active policy" in w.lower() for w in resp.warnings)

    def test_proposal_generation_failure_marks_workflow_failed_without_proposal(self):
        """Verify unrecoverable proposal generation failure marks workflow FAILED with no proposal linked."""
        session = _create_sqlite_session()
        as_of = date(2025, 1, 15)
        portfolio_id, _ = _seed_test_portfolio(session, as_of)

        mock_policy_rag = MagicMock(spec=PolicyRAGService)
        service = WorkflowService(session=session, policy_rag_service=mock_policy_rag)

        # Force proposal generation failure
        with patch.object(
            service.rebalancing_service,
            "create_and_persist_proposal",
            side_effect=RuntimeError("Solver timeout"),
        ):
            req = WorkflowRequest(
                portfolio_id=portfolio_id,
                as_of_date=as_of,
                request_key="wf-fail-prop-gen",
            )
            with pytest.raises(WorkflowExecutionError):
                service.run_workflow(req)

        run_record = (
            session.query(WorkflowRun)
            .filter_by(portfolio_id=portfolio_id, request_key="wf-fail-prop-gen")
            .first()
        )
        assert run_record is not None
        assert run_record.status == WorkflowStatus.FAILED.value
        assert run_record.error_code == "PROPOSAL_GENERATION_FAILED"
        assert run_record.proposal_id is None

    def test_concurrent_integrity_error_during_initialization_recovers_gracefully(self):
        """Verify race condition IntegrityError on initialization fetches existing workflow safely."""
        session = _create_sqlite_session()
        as_of = date(2025, 1, 15)
        portfolio_id, _ = _seed_test_portfolio(session, as_of)

        mock_policy_rag = MagicMock(spec=PolicyRAGService)
        mock_policy_rag.search_policies.return_value = []
        service = WorkflowService(session=session, policy_rag_service=mock_policy_rag)

        # Pre-seed a workflow run with the same key
        existing = WorkflowRun(
            id="WF-CONCURRENT-001",
            portfolio_id=portfolio_id,
            status=WorkflowStatus.PENDING_HUMAN_REVIEW.value,
            request_key="concurrent-key-999",
            request_payload={"portfolio_id": portfolio_id, "as_of_date": as_of.isoformat()},
            started_at=datetime.now(timezone.utc),
        )
        session.add(existing)
        session.commit()

        req = WorkflowRequest(
            portfolio_id=portfolio_id,
            as_of_date=as_of,
            request_key="concurrent-key-999",
        )

        resp = service.run_workflow(req)
        assert resp.workflow_id == "WF-CONCURRENT-001"
        assert resp.status == WorkflowStatus.PENDING_HUMAN_REVIEW.value


# ==============================================================================
# 6. Workflow Initiation REST API Tests (Task 1)
# ==============================================================================


class MockWorkflowAuthVerifier(BaseAuthenticationVerifier):
    def __init__(self, token_map: dict[str, ReviewerContext]) -> None:
        self.token_map = token_map

    def verify_token(self, token: str) -> Optional[ReviewerContext]:
        return self.token_map.get(token)


class TestWorkflowInitiationRESTAPI:
    """Tests for POST /api/v1/workflows and its authenticated-principal boundary."""

    @pytest.fixture(autouse=True)
    def setup_client_and_db(self):
        self.session = _create_sqlite_session()
        self.as_of = date(2025, 1, 15)
        self.portfolio_id, _ = _seed_test_portfolio(self.session, self.as_of)

        app.dependency_overrides[get_db] = lambda: self.session
        self.mock_tokens = {
            "valid-pm-token": ReviewerContext(
                reviewer_id="REV-PM-01", role="PORTFOLIO_MANAGER", email="pm@firm.com"
            ),
            "viewer-token": ReviewerContext(
                reviewer_id="REV-VIEWER-01", role="VIEWER", email="viewer@firm.com"
            ),
        }
        app.dependency_overrides[get_auth_verifier] = lambda: MockWorkflowAuthVerifier(self.mock_tokens)
        self.client = TestClient(app)

        yield

        app.dependency_overrides.clear()
        self.session.close()

    def test_initiate_workflow_unauthenticated_returns_401(self):
        """Missing or malformed Authorization header returns 401."""
        resp = self.client.post(
            "/api/v1/workflows",
            json={
                "portfolio_id": self.portfolio_id,
                "request_key": "req-no-auth",
            },
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        assert "WWW-Authenticate" in resp.headers

    def test_initiate_workflow_invalid_token_returns_401(self):
        """Unrecognized Bearer token returns 401."""
        resp = self.client.post(
            "/api/v1/workflows",
            headers={"Authorization": "Bearer completely-bogus-token"},
            json={
                "portfolio_id": self.portfolio_id,
                "request_key": "req-bad-token",
            },
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_initiate_workflow_unauthorized_role_returns_403(self):
        """Verified principal without required role returns 403."""
        resp = self.client.post(
            "/api/v1/workflows",
            headers={"Authorization": "Bearer viewer-token"},
            json={
                "portfolio_id": self.portfolio_id,
                "request_key": "req-viewer",
            },
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_initiate_workflow_success_returns_200(self):
        """Authorized user successfully initiates workflow and receives typed WorkflowResponse."""
        resp = self.client.post(
            "/api/v1/workflows",
            headers={"Authorization": "Bearer valid-pm-token"},
            json={
                "portfolio_id": self.portfolio_id,
                "as_of_date": self.as_of.isoformat(),
                "request_key": "req-success-01",
            },
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["portfolio_id"] == self.portfolio_id
        assert data["workflow_id"].startswith("WF-")
        assert data["status"] in ("PENDING_HUMAN_REVIEW", "REQUIRES_ATTENTION")
        assert data["proposal_id"] is not None
        assert data["proposal"]["portfolio_id"] == self.portfolio_id

    def test_initiate_workflow_missing_portfolio_returns_404(self):
        """Non-existent portfolio returns 404."""
        resp = self.client.post(
            "/api/v1/workflows",
            headers={"Authorization": "Bearer valid-pm-token"},
            json={
                "portfolio_id": "PORT-NONEXISTENT",
                "as_of_date": self.as_of.isoformat(),
                "request_key": "req-missing-port",
            },
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in resp.json()["detail"].lower()

    def test_initiate_workflow_invalid_payload_returns_422(self):
        """Invalid request body missing required fields returns 422."""
        resp = self.client.post(
            "/api/v1/workflows",
            headers={"Authorization": "Bearer valid-pm-token"},
            json={
                "portfolio_id": self.portfolio_id,
                # Missing request_key
            },
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_initiate_workflow_idempotent_retry_returns_200_same_workflow(self):
        """Identical retry returns the existing workflow with status 200."""
        payload = {
            "portfolio_id": self.portfolio_id,
            "as_of_date": self.as_of.isoformat(),
            "request_key": "req-idem-api-01",
        }
        resp1 = self.client.post(
            "/api/v1/workflows",
            headers={"Authorization": "Bearer valid-pm-token"},
            json=payload,
        )
        assert resp1.status_code == status.HTTP_200_OK
        wf_id_1 = resp1.json()["workflow_id"]

        resp2 = self.client.post(
            "/api/v1/workflows",
            headers={"Authorization": "Bearer valid-pm-token"},
            json=payload,
        )
        assert resp2.status_code == status.HTTP_200_OK
        assert resp2.json()["workflow_id"] == wf_id_1

    def test_initiate_workflow_idempotency_conflict_returns_409(self):
        """Reusing request_key with changed parameters returns 409 conflict."""
        self.client.post(
            "/api/v1/workflows",
            headers={"Authorization": "Bearer valid-pm-token"},
            json={
                "portfolio_id": self.portfolio_id,
                "as_of_date": self.as_of.isoformat(),
                "request_key": "req-conflict-key",
                "policy_query": "Initial query",
            },
        )

        resp2 = self.client.post(
            "/api/v1/workflows",
            headers={"Authorization": "Bearer valid-pm-token"},
            json={
                "portfolio_id": self.portfolio_id,
                "as_of_date": self.as_of.isoformat(),
                "request_key": "req-conflict-key",
                "policy_query": "Changed different query",
            },
        )
        assert resp2.status_code == status.HTTP_409_CONFLICT
        assert "conflict" in resp2.json()["detail"].lower()

    def test_initiate_workflow_unexpected_internal_error_returns_500(self):
        """Unexpected internal execution error is safely masked with HTTP 500."""
        with patch.object(
            WorkflowService,
            "run_workflow",
            side_effect=RuntimeError("Secret database connection failure!"),
        ):
            resp = self.client.post(
                "/api/v1/workflows",
                headers={"Authorization": "Bearer valid-pm-token"},
                json={
                    "portfolio_id": self.portfolio_id,
                    "request_key": "req-crash-500",
                },
            )
            assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            # Verify internal secret is NOT leaked to client
            assert "Secret database connection failure" not in resp.json()["detail"]

    def test_get_workflow_by_id_preserved(self):
        """Existing GET /api/v1/workflows/{workflow_id} retrieves workflow correctly."""
        post_resp = self.client.post(
            "/api/v1/workflows",
            headers={"Authorization": "Bearer valid-pm-token"},
            json={
                "portfolio_id": self.portfolio_id,
                "as_of_date": self.as_of.isoformat(),
                "request_key": "req-get-wf-01",
            },
        )
        assert post_resp.status_code == status.HTTP_200_OK
        wf_id = post_resp.json()["workflow_id"]

        get_resp = self.client.get(f"/api/v1/workflows/{wf_id}")
        assert get_resp.status_code == status.HTTP_200_OK
        assert get_resp.json()["workflow_id"] == wf_id

    def test_run_workflow_missing_portfolio_raises_portfolio_not_found_error(self):
        """Direct service call with non-existent portfolio raises PortfolioNotFoundError directly."""
        service = WorkflowService(self.session)
        req = WorkflowRequest(
            portfolio_id="PORT-DOES-NOT-EXIST",
            as_of_date=self.as_of,
            request_key="direct-req-missing",
        )
        with pytest.raises(PortfolioNotFoundError) as exc_info:
            service.run_workflow(req)
        assert exc_info.value.portfolio_id == "PORT-DOES-NOT-EXIST"

    def test_no_workflow_or_proposal_left_behind_after_missing_portfolio_error(self):
        """Verify that when initialization fails due to nonexistent portfolio, no orphan records exist."""
        initial_wf_count = self.session.query(WorkflowRun).count()
        initial_prop_count = self.session.query(RebalanceProposal).count()

        resp = self.client.post(
            "/api/v1/workflows",
            headers={"Authorization": "Bearer valid-pm-token"},
            json={
                "portfolio_id": "PORT-NONEXISTENT-999",
                "as_of_date": self.as_of.isoformat(),
                "request_key": "req-missing-port-orphan-check",
            },
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert self.session.query(WorkflowRun).count() == initial_wf_count
        assert self.session.query(RebalanceProposal).count() == initial_prop_count


# ==============================================================================
# 7. Simulation Persistence and Reconstruction Tests (Task 4)
# ==============================================================================


class TestSimulationPersistenceAndReconstruction:
    """Tests for Task 4: Complete post-trade simulation persistence in result_payload and reconstruction."""

    def test_simulation_persisted_in_result_payload_and_reconstructed_accurately(self):
        """Verify full simulation snapshot is saved in result_payload and reconstructed accurately."""
        session = _create_sqlite_session()
        as_of = date(2025, 1, 15)
        portfolio_id, eq_id = _seed_test_portfolio(session, as_of)

        service = WorkflowService(session=session)
        req = WorkflowRequest(
            portfolio_id=portfolio_id,
            as_of_date=as_of,
            request_key="wf-sim-persist-01",
        )

        resp = service.run_workflow(req)
        assert resp.proposal is not None
        assert resp.proposal.simulation is not None

        orig_sim = resp.proposal.simulation
        assert orig_sim.pre_trade_portfolio_value > 0
        assert orig_sim.post_trade_portfolio_value > 0
        assert orig_sim.pre_trade_cash > 0
        assert len(orig_sim.positions) > 0
        assert len(orig_sim.asset_classes) > 0

        # Check raw DB workflow_run.result_payload
        run_record = session.get(WorkflowRun, resp.workflow_id)
        assert run_record.result_payload is not None
        assert "simulation" in run_record.result_payload
        sim_payload = run_record.result_payload["simulation"]
        assert sim_payload is not None
        assert Decimal(str(sim_payload["pre_trade_cash"])) == orig_sim.pre_trade_cash
        assert Decimal(str(sim_payload["post_trade_cash"])) == orig_sim.post_trade_cash
        assert len(sim_payload["positions"]) == len(orig_sim.positions)

        # 1. Test reconstruction via get_workflow()
        get_res = service.get_workflow(resp.workflow_id)
        assert get_res is not None
        assert get_res.proposal is not None
        reconstructed_sim = get_res.proposal.simulation
        assert reconstructed_sim is not None
        assert reconstructed_sim.pre_trade_cash == orig_sim.pre_trade_cash
        assert reconstructed_sim.post_trade_cash == orig_sim.post_trade_cash
        assert reconstructed_sim.pre_trade_portfolio_value == orig_sim.pre_trade_portfolio_value
        assert reconstructed_sim.post_trade_portfolio_value == orig_sim.post_trade_portfolio_value
        assert len(reconstructed_sim.positions) == len(orig_sim.positions)
        assert len(reconstructed_sim.asset_classes) == len(orig_sim.asset_classes)
        assert reconstructed_sim.residual_drifts == orig_sim.residual_drifts

        # 2. Test reconstruction via idempotent retry run_workflow()
        retry_res = service.run_workflow(req)
        assert retry_res.proposal is not None
        retry_sim = retry_res.proposal.simulation
        assert retry_sim is not None
        assert retry_sim.pre_trade_cash == orig_sim.pre_trade_cash
        assert retry_sim.post_trade_cash == orig_sim.post_trade_cash
        assert len(retry_sim.positions) == len(orig_sim.positions)

    def test_legacy_workflow_run_without_simulation_falls_back_gracefully(self):
        """Verify legacy record lacking simulation snapshot reconstructs fallback simulation safely."""
        session = _create_sqlite_session()
        as_of = date(2025, 1, 15)
        portfolio_id, _ = _seed_test_portfolio(session, as_of)

        service = WorkflowService(session=session)
        req = WorkflowRequest(
            portfolio_id=portfolio_id,
            as_of_date=as_of,
            request_key="wf-legacy-sim-01",
        )
        resp = service.run_workflow(req)

        # Simulate a legacy record by wiping 'simulation' from result_payload
        run_record = session.get(WorkflowRun, resp.workflow_id)
        modified_payload = dict(run_record.result_payload)
        modified_payload.pop("simulation", None)
        run_record.result_payload = modified_payload
        session.commit()

        # Retrieve workflow - must not crash
        get_res = service.get_workflow(resp.workflow_id)
        assert get_res is not None
        assert get_res.proposal is not None
        assert get_res.proposal.simulation is not None
        # Fallback simulation has 0 positions/classes but doesn't crash or invent fake data
        assert get_res.proposal.simulation.positions == []

