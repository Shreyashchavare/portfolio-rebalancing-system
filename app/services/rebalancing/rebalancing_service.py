"""Deterministic Rebalancing Proposal Orchestrator and Lifecycle Service.

Coordinates trade recommendation generation, post-trade simulation, policy constraint
gatekeeping, cash-solvency reconciliation, and atomic transactional database persistence.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.instrument import Instrument
from app.models.market_price import MarketPrice
from app.models.portfolio import Portfolio
from app.models.rebalance_proposal import (
    ProposalStatus,
    RebalanceProposal,
    ReviewDecision,
)
from app.models.trade import Trade
from app.schemas.rebalancing import (
    ConstraintFinding,
    PostTradeSimulationResult,
    ProposedTrade,
    RebalanceProposalResponse,
    RebalanceRecommendationResult,
    TradeResponse,
)
from app.services.portfolio_analytics_service import (
    PortfolioAnalyticsService,
    PortfolioNotFoundError,
)
from app.services.rebalancing.constraint_evaluator import ConstraintEvaluator
from app.services.rebalancing.trade_generator import TradeGenerator
from app.services.rebalancing.trade_simulator import TradeSimulator


class ConstraintViolationError(ValueError):
    """Raised when a hard policy constraint is violated during proposal processing."""

    pass


class RebalancingService:
    """Production service for deterministic rebalancing recommendation generation, simulation, and persistence."""

    def __init__(
        self,
        session: Session,
        analytics_service: Optional[PortfolioAnalyticsService] = None,
        trade_generator: Optional[TradeGenerator] = None,
        trade_simulator: Optional[TradeSimulator] = None,
        constraint_evaluator: Optional[ConstraintEvaluator] = None,
    ) -> None:
        self.session = session
        self.analytics_service = analytics_service or PortfolioAnalyticsService(session)
        self.trade_generator = trade_generator or TradeGenerator(session, self.analytics_service)
        self.trade_simulator = trade_simulator or TradeSimulator(session, self.analytics_service)
        self.constraint_evaluator = constraint_evaluator or ConstraintEvaluator(session)

    def _get_active_fee_tiers(self, as_of_date: date) -> list[dict]:
        """Fetch active fee schedule records effective as of date and convert to tier dicts."""
        return self.trade_generator._get_active_fee_tiers(as_of_date)

    def _get_active_excluded_instruments(self, as_of_date: date) -> set[str]:
        """Retrieve set of instrument IDs actively excluded on as_of_date."""
        return self.trade_generator._get_active_excluded_instruments(as_of_date)

    def _get_latest_price_record(self, instrument_id: str, as_of_date: date) -> MarketPrice:
        """Resolve latest market price record on or before as_of_date or raise MissingPriceError."""
        return self.trade_generator._get_latest_price_record(instrument_id, as_of_date)

    def _get_latest_price(self, instrument_id: str, as_of_date: date) -> Decimal:
        """Resolve latest market price on or before as_of_date or raise MissingPriceError."""
        return self.trade_generator._get_latest_price(instrument_id, as_of_date)

    def generate_rebalance_trades(
        self, portfolio_id: str, as_of_date: date
    ) -> RebalanceRecommendationResult:
        """Generate deterministic, lot-sized BUY and SELL trade recommendations."""
        return self.trade_generator.generate_rebalance_trades(portfolio_id, as_of_date)

    def simulate_post_trade_state(
        self,
        portfolio_id: str,
        as_of_date: date,
        proposed_trades: list[ProposedTrade],
    ) -> PostTradeSimulationResult:
        """Execute deterministic, in-memory simulation of proposed trades on portfolio holdings."""
        return self.trade_simulator.simulate_post_trade_state(portfolio_id, as_of_date, proposed_trades)

    def evaluate_constraints(
        self,
        portfolio_id: str,
        as_of_date: date,
        proposed_trades: list[ProposedTrade],
        simulation: PostTradeSimulationResult,
    ) -> tuple[list[ConstraintFinding], list[str], list[str]]:
        """Evaluate active policy constraints effective on as_of_date against trades and simulated state."""
        return self.constraint_evaluator.evaluate_constraints(
            portfolio_id, as_of_date, proposed_trades, simulation
        )

    def create_and_persist_proposal(
        self, portfolio_id: str, as_of_date: date
    ) -> RebalanceProposalResponse:
        """Generate, simulate, validate constraints, and transactionally persist a RebalanceProposal with Trades."""
        portfolio = self.session.get(Portfolio, portfolio_id)
        if not portfolio:
            raise PortfolioNotFoundError(portfolio_id)

        # 1. Generate initial recommendations
        rebal_res = self.generate_rebalance_trades(portfolio_id, as_of_date)

        # 2. Run initial simulation
        sim_result = self.simulate_post_trade_state(portfolio_id, as_of_date, rebal_res.proposed_trades)

        # 3. Evaluate constraints
        findings, hard_violations, warnings = self.evaluate_constraints(
            portfolio_id, as_of_date, rebal_res.proposed_trades, sim_result
        )

        is_executable = True
        review_reason: Optional[str] = None

        if hard_violations:
            is_executable = False
            proposal_status = ProposalStatus.REJECTED
            review_decision = ReviewDecision.REJECTED
            review_reason = "; ".join(hard_violations)

            # Block affected trades
            violated_inst_ids = {
                f.affected_instrument_id
                for f in findings
                if f.is_violated and f.severity == "HARD" and f.affected_instrument_id
            }
            for t in rebal_res.proposed_trades:
                if t.instrument_id in violated_inst_ids:
                    t.status = "BLOCKED"
                    t.diagnostic = "Blocked by hard policy constraint violation"
        else:
            # Check if any trades were blocked during generation (e.g. missing fee schedule)
            blocked_trades = [t for t in rebal_res.proposed_trades if t.status == "BLOCKED"]
            if blocked_trades:
                is_executable = False
                proposal_status = ProposalStatus.REJECTED
                review_decision = ReviewDecision.REJECTED
                review_reason = "Proposal contains unexecutable blocked trades: missing fee schedules or invalid market conditions"
            else:
                proposal_status = ProposalStatus.PENDING_REVIEW
                review_decision = ReviewDecision.PENDING
                review_reason = None

        # Reconcile cash solvency and dependent BUY trades
        # If any SELL trade is BLOCKED, its proceeds are $0 and cannot fund BUYs
        avail_cash = rebal_res.starting_cash
        for t in rebal_res.proposed_trades:
            if t.trade_side == "SELL" and t.status == "PROPOSED":
                avail_cash += t.trade_value - t.fee_amount

        for t in rebal_res.proposed_trades:
            if t.trade_side == "BUY" and t.status == "PROPOSED":
                outlay = t.trade_value + t.fee_amount
                if outlay > avail_cash:
                    t.status = "BLOCKED"
                    t.diagnostic = "Blocked: insufficient executable proceeds to fund purchase"
                else:
                    avail_cash -= outlay

        # Re-run simulation so blocked trades (BUY and SELL) are completely excluded from final post-trade state
        sim_result = self.simulate_post_trade_state(portfolio_id, as_of_date, rebal_res.proposed_trades)

        # 4. Transactional persistence with collision retry
        now_dt = datetime.now(timezone.utc)
        year_prefix = f"RB-{as_of_date.year}-"

        for attempt in range(5):
            try:
                # Query existing proposal IDs matching year_prefix to find max numeric suffix
                existing_prop_ids = [
                    p[0]
                    for p in self.session.query(RebalanceProposal.proposal_id)
                    .filter(RebalanceProposal.proposal_id.like(f"{year_prefix}%"))
                    .all()
                ]
                max_p_seq = 0
                for pid in existing_prop_ids:
                    suffix = pid[len(year_prefix):]
                    if suffix.isdigit():
                        max_p_seq = max(max_p_seq, int(suffix))

                proposal_id = f"{year_prefix}{max_p_seq + 1:06d}"
                while self.session.get(RebalanceProposal, proposal_id) is not None:
                    max_p_seq += 1
                    proposal_id = f"{year_prefix}{max_p_seq + 1:06d}"

                db_proposal = RebalanceProposal(
                    proposal_id=proposal_id,
                    portfolio_id=portfolio_id,
                    status=proposal_status.value if hasattr(proposal_status, "value") else str(proposal_status),
                    review_decision=review_decision.value if hasattr(review_decision, "value") else str(review_decision),
                    pre_trade_portfolio_value=sim_result.pre_trade_portfolio_value,
                    post_trade_portfolio_value=sim_result.post_trade_portfolio_value,
                    created_at=now_dt,
                    reviewed_at=now_dt if proposal_status == ProposalStatus.REJECTED else None,
                    review_reason=review_reason,
                )
                self.session.add(db_proposal)
                self.session.flush()

                # Derive max numeric sequence for Trade.trade_id to prevent collision with gaps
                existing_trade_ids = [
                    t[0]
                    for t in self.session.query(Trade.trade_id)
                    .filter(Trade.trade_id.like("TRD-%"))
                    .all()
                ]
                max_t_seq = 0
                for tid in existing_trade_ids:
                    suffix = tid[4:]
                    if suffix.isdigit():
                        max_t_seq = max(max_t_seq, int(suffix))

                persisted_trade_responses: list[TradeResponse] = []

                for i, pt in enumerate(rebal_res.proposed_trades):
                    t_idx = max_t_seq + i + 1
                    trade_id = f"TRD-{t_idx:06d}"
                    while self.session.get(Trade, trade_id) is not None:
                        max_t_seq += 1
                        trade_id = f"TRD-{max_t_seq + i + 1:06d}"

                    db_trade = Trade(
                        trade_id=trade_id,
                        proposal_id=proposal_id,
                        instrument_id=pt.instrument_id,
                        fee_schedule_id=pt.fee_schedule_id,
                        trade_side=pt.trade_side,
                        quantity=pt.quantity,
                        unit_price=pt.unit_price,
                        trade_value=pt.trade_value,
                        fee_amount=pt.fee_amount,
                        status=pt.status,
                        created_at=now_dt,
                    )
                    self.session.add(db_trade)
                    persisted_trade_responses.append(
                        TradeResponse(
                            trade_id=trade_id,
                            proposal_id=proposal_id,
                            instrument_id=pt.instrument_id,
                            symbol=pt.symbol,
                            instrument_name=pt.instrument_name,
                            asset_class=pt.asset_class,
                            trade_side=pt.trade_side,
                            quantity=pt.quantity,
                            unit_price=pt.unit_price,
                            trade_value=pt.trade_value,
                            fee_amount=pt.fee_amount,
                            fee_schedule_id=pt.fee_schedule_id,
                            status=pt.status,
                            diagnostic=pt.diagnostic,
                        )
                    )

                self.session.commit()
                break
            except IntegrityError:
                self.session.rollback()
                if attempt == 4:
                    raise
            except Exception:
                self.session.rollback()
                raise

        return RebalanceProposalResponse(
            proposal_id=proposal_id,
            portfolio_id=portfolio_id,
            as_of_date=as_of_date,
            status=proposal_status.value if hasattr(proposal_status, "value") else str(proposal_status),
            review_decision=review_decision.value if hasattr(review_decision, "value") else str(review_decision),
            review_reason=review_reason,
            pre_trade_portfolio_value=sim_result.pre_trade_portfolio_value,
            post_trade_portfolio_value=sim_result.post_trade_portfolio_value,
            created_at=now_dt,
            trades=persisted_trade_responses,
            simulation=sim_result,
            constraint_findings=findings,
            warnings=warnings,
            is_executable=is_executable,
            requires_human_review=rebal_res.requires_human_review,
        )

    def get_proposal_by_id(self, proposal_id: str) -> Optional[RebalanceProposalResponse]:
        """Retrieve an existing persisted proposal with actual trades, simulation, and gatekeeper findings."""
        proposal = self.session.get(RebalanceProposal, proposal_id)
        if not proposal:
            return None

        trades = (
            self.session.query(Trade)
            .filter(Trade.proposal_id == proposal_id)
            .order_by(Trade.trade_id)
            .all()
        )
        trade_responses: list[TradeResponse] = []
        for t in trades:
            inst = self.session.get(Instrument, t.instrument_id)
            trade_responses.append(
                TradeResponse(
                    trade_id=t.trade_id,
                    proposal_id=t.proposal_id,
                    instrument_id=t.instrument_id,
                    symbol=inst.symbol if inst else t.instrument_id,
                    instrument_name=inst.instrument_name if inst else None,
                    asset_class=inst.asset_class if inst else "UNKNOWN",
                    trade_side=t.trade_side,
                    quantity=t.quantity,
                    unit_price=t.unit_price,
                    trade_value=t.trade_value,
                    fee_amount=t.fee_amount,
                    fee_schedule_id=t.fee_schedule_id,
                    status=t.status,
                    diagnostic=None,
                )
            )

        as_of_d = proposal.created_at.date() if proposal.created_at else date(2026, 1, 15)
        proposed_trades_for_sim = [
            ProposedTrade(
                instrument_id=tr.instrument_id,
                symbol=tr.symbol,
                instrument_name=tr.instrument_name,
                asset_class=tr.asset_class,
                trade_side=tr.trade_side,
                quantity=tr.quantity,
                unit_price=tr.unit_price,
                trade_value=tr.trade_value,
                fee_amount=tr.fee_amount,
                fee_schedule_id=tr.fee_schedule_id,
                status=tr.status,
            )
            for tr in trade_responses
        ]

        try:
            sim_result = self.simulate_post_trade_state(
                proposal.portfolio_id, as_of_d, proposed_trades_for_sim
            )
            findings, _, warnings = self.evaluate_constraints(
                proposal.portfolio_id, as_of_d, proposed_trades_for_sim, sim_result
            )
        except Exception:
            sim_result = PostTradeSimulationResult(
                pre_trade_portfolio_value=proposal.pre_trade_portfolio_value or Decimal("0"),
                post_trade_portfolio_value=proposal.post_trade_portfolio_value or Decimal("0"),
                pre_trade_cash=Decimal("0"),
                post_trade_cash=Decimal("0"),
                total_executable_fees=sum((t.fee_amount for t in trade_responses), Decimal("0")),
                positions=[],
                asset_classes=[],
                residual_drifts={},
            )
            findings, warnings = [], []

        return RebalanceProposalResponse(
            proposal_id=proposal.proposal_id,
            portfolio_id=proposal.portfolio_id,
            as_of_date=as_of_d,
            status=proposal.status,
            review_decision=proposal.review_decision,
            review_reason=proposal.review_reason,
            pre_trade_portfolio_value=proposal.pre_trade_portfolio_value or sim_result.pre_trade_portfolio_value,
            post_trade_portfolio_value=proposal.post_trade_portfolio_value or sim_result.post_trade_portfolio_value,
            created_at=proposal.created_at,
            trades=trade_responses,
            simulation=sim_result,
            constraint_findings=findings,
            warnings=warnings,
            is_executable=(proposal.status != "REJECTED"),
            requires_human_review=(proposal.status == "PENDING_REVIEW"),
        )

    def list_proposals(
        self, portfolio_id: Optional[str] = None, status: Optional[str] = None
    ) -> list[RebalanceProposalResponse]:
        """List persisted proposals matching optional filters."""
        query = self.session.query(RebalanceProposal)
        if portfolio_id:
            query = query.filter(RebalanceProposal.portfolio_id == portfolio_id)
        if status:
            query = query.filter(RebalanceProposal.status == status)
        proposals = query.order_by(RebalanceProposal.created_at.desc()).all()
        results: list[RebalanceProposalResponse] = []
        for p in proposals:
            item = self.get_proposal_by_id(p.proposal_id)
            if item:
                results.append(item)
        return results


