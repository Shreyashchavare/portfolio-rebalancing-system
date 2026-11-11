"""WorkflowService orchestrating portfolio rebalancing workflow lifecycle, idempotency, and persistence."""

from datetime import date, datetime, timezone
import logging
from typing import Any, Optional
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.portfolio import Portfolio
from app.models.workflow_run import WorkflowRun
from app.schemas.explanation import ExplanationResponse
from app.schemas.orchestration import (
    IdempotencyConflictError,
    WorkflowExecutionError,
    WorkflowRequest,
    WorkflowResponse,
    WorkflowStatus,
)
from app.services.explanation.explanation_service import ExplanationService
from app.services.orchestration.workflow_context import WorkflowContext
from app.services.orchestration.workflow_executor import WorkflowExecutor
from app.services.orchestration.workflow_state import validate_transition
from app.services.policy_rag.policy_rag_service import PolicyRAGService
from app.services.portfolio_analytics_service import (
    MissingPriceError,
    PortfolioAnalyticsService,
    PortfolioNotFoundError,
)
from app.services.rebalancing_service import RebalancingService

logger = logging.getLogger(__name__)


class WorkflowService:
    """Entry point for executing orchestrated portfolio rebalancing workflows."""

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
        self.executor = WorkflowExecutor(
            session=session,
            analytics_service=self.analytics_service,
            rebalancing_service=self.rebalancing_service,
            policy_rag_service=self.policy_rag_service,
            explanation_service=self.explanation_service,
        )

    def run_workflow(self, request: WorkflowRequest) -> WorkflowResponse:
        """Execute or resume an orchestrated rebalance workflow with idempotency protection.

        Coordinates:
        1. Request validation and idempotency check.
        2. Portfolio valuation and allocation drift analysis.
        3. Deterministic proposal generation and transaction commit.
        4. Compliance policy evidence retrieval.
        5. Final workflow status resolution and result persistence.
        """
        as_of = request.as_of_date or date.today()

        # 0. Portfolio existence validation
        portfolio = self.session.get(Portfolio, request.portfolio_id)
        if portfolio is None:
            raise PortfolioNotFoundError(request.portfolio_id)

        # 1. Idempotency Check
        existing_run = (
            self.session.query(WorkflowRun)
            .filter_by(
                portfolio_id=request.portfolio_id,
                request_key=request.request_key,
            )
            .first()
        )

        if existing_run:
            return self._handle_existing_run(existing_run, request, as_of)

        # 2. Initialize new WorkflowRun record
        workflow_id = f"WF-{as_of.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        workflow_run = WorkflowRun(
            id=workflow_id,
            portfolio_id=request.portfolio_id,
            status=WorkflowStatus.RECEIVED.value,
            request_key=request.request_key,
            request_payload=self.canonicalize_request_payload(request, as_of),
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(workflow_run)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            # If the portfolio was concurrently removed or missing, raise PortfolioNotFoundError
            if self.session.get(Portfolio, request.portfolio_id) is None:
                raise PortfolioNotFoundError(request.portfolio_id) from exc

            # Concurrent duplicate request race condition
            concurrent_run = (
                self.session.query(WorkflowRun)
                .filter_by(
                    portfolio_id=request.portfolio_id,
                    request_key=request.request_key,
                )
                .first()
            )
            if concurrent_run:
                return self._handle_existing_run(concurrent_run, request, as_of)
            raise WorkflowExecutionError("Database concurrency integrity conflict during workflow initialization.") from exc

        # 3. Construct Context
        context = WorkflowContext(
            workflow_id=workflow_run.id,
            portfolio_id=request.portfolio_id,
            as_of_date=as_of,
            request_key=request.request_key,
            policy_query=request.policy_query,
            proposal_id=workflow_run.proposal_id,
        )

        # 4. Pipeline Execution
        try:
            # Step A: VALIDATING
            self._transition(workflow_run, WorkflowStatus.VALIDATING, context)
            self.executor.validate_portfolio(context)

            # Step B: ANALYZING
            self._transition(workflow_run, WorkflowStatus.ANALYZING, context)
            self.executor.execute_analytics(context)

            # Step C: GENERATING_PROPOSAL
            self._transition(workflow_run, WorkflowStatus.GENERATING_PROPOSAL, context)
            self.executor.execute_proposal(context)
            # Immediately link persisted proposal_id to workflow_run
            workflow_run.proposal_id = context.proposal_id
            self.session.commit()

            # Step D: RETRIEVING_POLICIES
            self._transition(workflow_run, WorkflowStatus.RETRIEVING_POLICIES, context)
            policy_failed = False
            try:
                self.executor.execute_policy_retrieval(context)
            except Exception as policy_err:
                logger.warning(
                    "Policy retrieval failed for workflow %s: %s",
                    context.workflow_id,
                    policy_err,
                )
                policy_failed = True
                context.errors.append(f"Policy retrieval error: {str(policy_err)}")
                context.warnings.append(
                    f"Policy compliance verification could not be completed: {str(policy_err)}"
                )
                context.requires_human_review = True
                workflow_run.error_code = "POLICY_RETRIEVAL_FAILED"
                workflow_run.error_message = f"Policy retrieval failed: {str(policy_err)}"

            # Step E: GENERATING_EXPLANATION
            self._transition(workflow_run, WorkflowStatus.GENERATING_EXPLANATION, context)
            try:
                self.executor.execute_explanation(context)
            except Exception as exp_err:
                logger.warning(
                    "Explanation generation failed for workflow %s: %s",
                    context.workflow_id,
                    exp_err,
                )
                context.warnings.append(f"Explanation generation failed: {str(exp_err)}")
                context.requires_human_review = True

            # Step F: FINAL RESOLUTION
            if policy_failed:
                target_status = WorkflowStatus.REQUIRES_ATTENTION
            elif context.proposal_result and (
                context.proposal_result.status == "REJECTED"
                or context.proposal_result.review_decision == "REJECTED"
            ):
                target_status = WorkflowStatus.REJECTED
            else:
                target_status = WorkflowStatus.PENDING_HUMAN_REVIEW

            self._transition(workflow_run, target_status, context)
            workflow_run.completed_at = datetime.now(timezone.utc)
            exp_dict = None
            if context.explanation_result:
                exp_dict = context.explanation_result.model_dump(mode="json")

            sim_dict = None
            if context.proposal_result and context.proposal_result.simulation:
                sim_dict = context.proposal_result.simulation.model_dump(mode="json")

            workflow_run.result_payload = {
                "status": target_status.value,
                "proposal_id": context.proposal_id,
                "requires_human_review": context.requires_human_review,
                "warnings": context.warnings,
                "errors": context.errors,
                "policy_evidence_count": len(context.policy_evidence),
                "explanation": exp_dict,
                "simulation": sim_dict,
            }
            self.session.commit()

            return WorkflowResponse(
                workflow_id=workflow_run.id,
                portfolio_id=workflow_run.portfolio_id,
                as_of_date=as_of,
                status=workflow_run.status,
                request_key=workflow_run.request_key,
                proposal_id=context.proposal_id,
                proposal=context.proposal_result,
                explanation=context.explanation_result,
                policy_evidence=context.policy_evidence,
                warnings=context.warnings,
                errors=context.errors,
                requires_human_review=context.requires_human_review,
                error_code=workflow_run.error_code,
                error_message=workflow_run.error_message,
                started_at=workflow_run.started_at,
                completed_at=workflow_run.completed_at,
                created_at=workflow_run.created_at,
            )

        except (PortfolioNotFoundError, MissingPriceError) as client_err:
            self._fail_workflow(workflow_run, error_code="CLIENT_ERROR", error_message=str(client_err))
            raise WorkflowExecutionError(str(client_err)) from client_err
        except WorkflowExecutionError as exec_err:
            err_code = getattr(exec_err, "error_code", "EXECUTION_FAILED")
            self._fail_workflow(workflow_run, error_code=err_code, error_message=str(exec_err))
            raise
        except Exception as unexpected_err:
            logger.exception("Unexpected error in workflow %s: %s", workflow_run.id, unexpected_err)
            self._fail_workflow(workflow_run, error_code="UNEXPECTED_ERROR", error_message=str(unexpected_err))
            raise WorkflowExecutionError(f"Workflow execution failed: {unexpected_err}") from unexpected_err

    @staticmethod
    def canonicalize_request_payload(request: WorkflowRequest, as_of: date) -> dict[str, Any]:
        """Deterministically canonicalize all behavior-affecting request fields into JSON primitives."""
        return {
            "portfolio_id": str(request.portfolio_id).strip(),
            "as_of_date": as_of.isoformat(),
            "request_key": str(request.request_key).strip(),
            "policy_query": request.policy_query.strip() if request.policy_query and request.policy_query.strip() else None,
        }

    def _handle_existing_run(
        self,
        existing_run: WorkflowRun,
        request: WorkflowRequest,
        as_of: date,
    ) -> WorkflowResponse:
        """Handle idempotent lookup: return existing run or reject conflicting payload."""
        incoming_payload = self.canonicalize_request_payload(request, as_of)
        stored_payload = existing_run.request_payload

        # If older records lack stored payload or cannot be compared safely, fail closed
        if not stored_payload or not isinstance(stored_payload, dict):
            raise IdempotencyConflictError(
                f"Idempotency conflict: request_key '{request.request_key}' was previously used "
                "but stored request payload is missing or incomplete and cannot be safely verified."
            )

        # 1. Compare portfolio_id
        stored_portfolio = stored_payload.get("portfolio_id")
        if stored_portfolio is not None and str(stored_portfolio).strip() != incoming_payload["portfolio_id"]:
            raise IdempotencyConflictError(
                f"Idempotency conflict: request_key '{request.request_key}' was previously used "
                f"for portfolio '{stored_portfolio}' (attempted: '{incoming_payload['portfolio_id']}')."
            )

        # 2. Compare as_of_date
        recorded_date = stored_payload.get("as_of_date")
        incoming_date = incoming_payload["as_of_date"]
        if recorded_date != incoming_date:
            raise IdempotencyConflictError(
                f"Idempotency conflict: request_key '{request.request_key}' was previously used "
                f"with different request data (as_of_date: '{recorded_date}' vs '{incoming_date}')."
            )

        # 3. Compare policy_query
        stored_query = stored_payload.get("policy_query")
        if stored_query is not None:
            stored_query = str(stored_query).strip() if str(stored_query).strip() else None
        incoming_query = incoming_payload["policy_query"]
        if stored_query != incoming_query:
            raise IdempotencyConflictError(
                f"Idempotency conflict: request_key '{request.request_key}' was previously used "
                f"with different policy_query ('{stored_query}' vs '{incoming_query}')."
            )

        # Reconstruct proposal details if available
        proposal = None
        if existing_run.proposal_id:
            proposal = self.executor.reconstruct_proposal_response(
                existing_run.proposal_id, as_of, stored_result_payload=existing_run.result_payload
            )

        explanation = None
        if (
            existing_run.result_payload
            and isinstance(existing_run.result_payload, dict)
            and existing_run.result_payload.get("explanation")
        ):
            try:
                explanation = ExplanationResponse.model_validate(
                    existing_run.result_payload["explanation"]
                )
            except Exception as e:
                logger.warning("Failed to deserialize explanation from result_payload: %s", e)

        return WorkflowResponse(
            workflow_id=existing_run.id,
            portfolio_id=existing_run.portfolio_id,
            as_of_date=as_of,
            status=existing_run.status,
            request_key=existing_run.request_key,
            proposal_id=existing_run.proposal_id,
            proposal=proposal,
            explanation=explanation,
            policy_evidence=[],
            warnings=[],
            errors=[],
            requires_human_review=(existing_run.status == WorkflowStatus.PENDING_HUMAN_REVIEW.value),
            error_code=existing_run.error_code,
            error_message=existing_run.error_message,
            started_at=existing_run.started_at,
            completed_at=existing_run.completed_at,
            created_at=existing_run.created_at,
        )

    def _transition(
        self,
        workflow_run: WorkflowRun,
        target_status: WorkflowStatus,
        context: WorkflowContext,
    ) -> None:
        """Validate and apply a state transition on the workflow run record."""
        current_status = WorkflowStatus(workflow_run.status)
        validate_transition(current_status, target_status, context=context)
        workflow_run.status = target_status.value
        self.session.commit()

    def _fail_workflow(
        self,
        workflow_run: WorkflowRun,
        error_code: str,
        error_message: str,
    ) -> None:
        """Mark workflow run as FAILED and persist sanitized diagnostics."""
        try:
            workflow_run.status = WorkflowStatus.FAILED.value
            workflow_run.error_code = error_code
            workflow_run.error_message = error_message
            workflow_run.completed_at = datetime.now(timezone.utc)
            self.session.commit()
        except Exception as e:
            logger.exception("Failed to persist failed status for workflow %s: %s", workflow_run.id, e)
            self.session.rollback()

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowResponse]:
        """Retrieve workflow execution details and reconstructed proposal/explanation."""
        run = self.session.query(WorkflowRun).filter_by(id=workflow_id).first()
        if not run:
            return None

        as_of = date.today()
        req_payload = run.request_payload or {}
        if req_payload.get("as_of_date"):
            try:
                as_of = date.fromisoformat(req_payload["as_of_date"])
            except Exception:
                pass

        proposal = None
        if run.proposal_id:
            proposal = self.executor.reconstruct_proposal_response(
                run.proposal_id, as_of, stored_result_payload=run.result_payload
            )

        explanation = None
        if (
            run.result_payload
            and isinstance(run.result_payload, dict)
            and run.result_payload.get("explanation")
        ):
            try:
                explanation = ExplanationResponse.model_validate(run.result_payload["explanation"])
            except Exception as e:
                logger.warning("Failed to deserialize explanation from result_payload: %s", e)

        return WorkflowResponse(
            workflow_id=run.id,
            portfolio_id=run.portfolio_id,
            as_of_date=as_of,
            status=run.status,
            request_key=run.request_key,
            proposal_id=run.proposal_id,
            proposal=proposal,
            explanation=explanation,
            policy_evidence=[],
            warnings=[],
            errors=[],
            requires_human_review=(run.status == WorkflowStatus.PENDING_HUMAN_REVIEW.value),
            error_code=run.error_code,
            error_message=run.error_message,
            started_at=run.started_at,
            completed_at=run.completed_at,
            created_at=run.created_at,
        )
