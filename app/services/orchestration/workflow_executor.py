"""WorkflowExecutor coordinating Analytics, Rebalancing, and Policy RAG steps."""

from datetime import date
from decimal import Decimal
import logging
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.models.portfolio import Portfolio, PortfolioStatus
from app.models.rebalance_proposal import RebalanceProposal
from app.models.trade import Trade
from app.schemas.explanation import ExplanationRequest, ExplanationResponse
from app.schemas.orchestration import WorkflowExecutionError
from app.schemas.policy_rag import PolicySearchResult
from app.schemas.rebalancing import (
    PostTradeSimulationResult,
    RebalanceProposalResponse,
    SimulatedAllocation,
    TradeResponse,
)
from app.services.explanation.explanation_service import ExplanationService
from app.services.orchestration.workflow_context import WorkflowContext
from app.services.policy_rag.policy_rag_service import PolicyRAGService
from app.services.portfolio_analytics_service import (
    MissingPriceError,
    PortfolioAnalyticsService,
    PortfolioNotFoundError,
)
from app.services.rebalancing_service import RebalancingService

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """Coordinates deterministic execution of individual rebalancing workflow steps."""

    def __init__(
        self,
        session: Session,
        analytics_service: Optional[PortfolioAnalyticsService] = None,
        rebalancing_service: Optional[RebalancingService] = None,
        policy_rag_service: Optional[PolicyRAGService] = None,
        explanation_service: Optional[ExplanationService] = None,
    ) -> None:
        self.session = session
        self.analytics_service = analytics_service or PortfolioAnalyticsService(session)
        self.rebalancing_service = rebalancing_service or RebalancingService(session)
        self.policy_rag_service = policy_rag_service or PolicyRAGService(session=session)
        self.explanation_service = explanation_service or ExplanationService()

    def validate_portfolio(self, context: WorkflowContext) -> None:
        """Validate portfolio existence and active status."""
        portfolio = self.session.get(Portfolio, context.portfolio_id)
        if not portfolio:
            raise PortfolioNotFoundError(context.portfolio_id)
        if portfolio.status != PortfolioStatus.ACTIVE:
            raise WorkflowExecutionError(
                f"Portfolio '{context.portfolio_id}' is not ACTIVE (status: {portfolio.status})."
            )

    def execute_analytics(self, context: WorkflowContext) -> None:
        """Execute portfolio valuation and allocation drift calculation."""
        try:
            valuation = self.analytics_service.get_portfolio_valuation(
                portfolio_id=context.portfolio_id,
                as_of_date=context.as_of_date,
            )
            context.analytics_valuation = valuation

            drift = self.analytics_service.get_portfolio_drift(
                portfolio_id=context.portfolio_id,
                as_of_date=context.as_of_date,
            )
            context.analytics_drift = drift

            # Check if any price diagnostics require human review
            for pos in valuation.positions:
                if pos.price_age_days is not None and pos.price_age_days > 0:
                    context.requires_human_review = True
                    context.warnings.append(
                        f"Price for instrument {pos.instrument_id} is {pos.price_age_days} day(s) old."
                    )
        except (PortfolioNotFoundError, MissingPriceError) as e:
            raise e
        except Exception as e:
            logger.exception("Failed during analytics step for portfolio %s: %s", context.portfolio_id, e)
            raise WorkflowExecutionError(f"Analytics failure: {e}", error_code="ANALYTICS_FAILED") from e

    def execute_proposal(self, context: WorkflowContext) -> None:
        """Generate and persist deterministic rebalance proposal exactly once.

        If a proposal has already been created for this workflow run, it is reused.
        """
        if context.proposal_id and context.proposal_result:
            logger.info("Reusing existing proposal %s for workflow %s", context.proposal_id, context.workflow_id)
            return

        try:
            proposal_res = self.rebalancing_service.create_and_persist_proposal(
                portfolio_id=context.portfolio_id,
                as_of_date=context.as_of_date,
            )
            context.proposal_id = proposal_res.proposal_id
            context.proposal_result = proposal_res
            context.constraint_findings = proposal_res.constraint_findings

            for warning in proposal_res.warnings:
                if warning not in context.warnings:
                    context.warnings.append(warning)

            if proposal_res.requires_human_review:
                context.requires_human_review = True

        except Exception as e:
            logger.exception(
                "Failed during proposal generation step for portfolio %s: %s",
                context.portfolio_id,
                e,
            )
            raise WorkflowExecutionError(
                f"Proposal generation failure: {e}",
                error_code="PROPOSAL_GENERATION_FAILED",
            ) from e

    def execute_policy_retrieval(self, context: WorkflowContext) -> None:
        """Retrieve relevant active policy documents using PolicyRAGService."""
        query = (
            context.policy_query
            or f"Portfolio rebalancing and asset allocation compliance mandate for portfolio {context.portfolio_id}"
        )

        # Call search_policies with exact as_of_date
        results = self.policy_rag_service.search_policies(
            query=query,
            as_of_date=context.as_of_date,
            top_k=5,
        )
        context.policy_evidence = results

        # Invariant: Do not treat missing policy evidence as compliance
        if not results:
            context.warnings.append(
                f"No active policy documents found covering rebalancing mandate as of {context.as_of_date.isoformat()}."
            )
            context.requires_human_review = True
        else:
            # Check for policy-family version overlaps / conflicts
            families_seen: dict[str, set[str]] = {}
            for r in results:
                fam = r.policy_family_id or f"DOC-{r.document_id}"
                families_seen.setdefault(fam, set()).add(r.document_version)

            for fam_id, versions in families_seen.items():
                if len(versions) > 1:
                    conflict_msg = (
                        f"Policy family '{fam_id}' retrieved multiple distinct active versions {versions} "
                        f"for as-of date {context.as_of_date.isoformat()}."
                    )
                    context.warnings.append(conflict_msg)
                    context.requires_human_review = True

    def execute_explanation(self, context: WorkflowContext) -> None:
        """Generate grounded narrative explanation using ExplanationService."""
        if not context.proposal_result:
            return

        exp_req = ExplanationRequest(
            workflow_id=context.workflow_id,
            portfolio_id=context.portfolio_id,
            proposal_id=context.proposal_result.proposal_id,
            as_of_date=context.as_of_date,
            proposal=context.proposal_result,
            policy_evidence=context.policy_evidence,
            drifts=context.analytics_drift.drifts if context.analytics_drift else [],
            constraint_findings=context.constraint_findings,
            warnings=context.warnings,
        )
        exp_resp = self.explanation_service.generate_explanation(exp_req)
        context.explanation_result = exp_resp
        for w in exp_resp.warnings:
            if w not in context.warnings:
                context.warnings.append(w)
        if exp_resp.requires_human_review:
            context.requires_human_review = True

    def reconstruct_proposal_response(
        self,
        proposal_id: str,
        as_of_date: date,
        stored_result_payload: Optional[dict[str, Any]] = None,
    ) -> Optional[RebalanceProposalResponse]:
        """Reconstruct RebalanceProposalResponse from database if proposal already exists.

        Reconstructs exact simulation details from stored_result_payload when available,
        falling back gracefully for legacy records lacking a simulation snapshot.
        """
        db_proposal = self.session.get(RebalanceProposal, proposal_id)
        if not db_proposal:
            return None

        trades_db = (
            self.session.query(Trade)
            .filter_by(proposal_id=proposal_id)
            .order_by(Trade.trade_id)
            .all()
        )
        trades_response = [
            TradeResponse(
                trade_id=t.trade_id,
                proposal_id=t.proposal_id,
                instrument_id=t.instrument_id,
                symbol=t.instrument.symbol if t.instrument else None,
                instrument_name=t.instrument.instrument_name if t.instrument else None,
                asset_class=t.instrument.asset_class if t.instrument else "UNKNOWN",
                trade_side=t.trade_side,
                quantity=t.quantity,
                unit_price=t.unit_price,
                trade_value=t.trade_value,
                fee_amount=t.fee_amount,
                fee_schedule_id=t.fee_schedule_id,
                status=t.status,
                diagnostic=getattr(t, "diagnostic", None),
            )
            for t in trades_db
        ]

        # Reconstruct full deterministic simulation if snapshot exists in payload
        simulation = None
        if (
            stored_result_payload
            and isinstance(stored_result_payload, dict)
            and stored_result_payload.get("simulation")
        ):
            try:
                simulation = PostTradeSimulationResult.model_validate(
                    stored_result_payload["simulation"]
                )
            except Exception as e:
                logger.warning("Failed to deserialize simulation from stored_result_payload: %s", e)

        # Fallback minimal simulation for legacy records lacking stored simulation
        if not simulation:
            simulation = PostTradeSimulationResult(
                pre_trade_portfolio_value=db_proposal.pre_trade_portfolio_value or Decimal("0.0000"),
                post_trade_portfolio_value=db_proposal.post_trade_portfolio_value or Decimal("0.0000"),
                pre_trade_cash=Decimal("0.0000"),
                post_trade_cash=Decimal("0.0000"),
                total_executable_fees=sum((t.fee_amount for t in trades_response), Decimal("0.0000")),
                positions=[],
                asset_classes=[],
                residual_drifts={},
            )

        return RebalanceProposalResponse(
            proposal_id=db_proposal.proposal_id,
            portfolio_id=db_proposal.portfolio_id,
            as_of_date=as_of_date,
            status=db_proposal.status,
            review_decision=db_proposal.review_decision,
            review_reason=db_proposal.review_reason,
            pre_trade_portfolio_value=db_proposal.pre_trade_portfolio_value or Decimal("0.0000"),
            post_trade_portfolio_value=db_proposal.post_trade_portfolio_value or Decimal("0.0000"),
            created_at=db_proposal.created_at,
            trades=trades_response,
            simulation=simulation,
            constraint_findings=[],
            warnings=[],
            is_executable=(db_proposal.status != "REJECTED"),
            requires_human_review=(db_proposal.status == "PENDING_REVIEW"),
        )
