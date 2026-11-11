"""Grounded explanation service explaining rebalancing proposals with validated policy citations."""

from datetime import date, datetime, timezone
import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.schemas.explanation import (
    ExplanationCitation,
    ExplanationRequest,
    ExplanationResponse,
    ExplanationStatus,
    TradeExplanationItem,
)
from app.schemas.policy_rag import PolicySearchResult
from app.services.explanation.citation_validator import CitationValidator
from app.services.explanation.prompt_templates import ExplanationPromptBuilder
from app.services.policy_rag.llm_client import (
    BaseLLMClient,
    LLMUnavailableError,
    LocalLLMClient,
)

logger = logging.getLogger(__name__)


class ExplanationService:
    """Service generating grounded, citation-validated explanations for rebalance proposals."""

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        prompt_builder: Optional[ExplanationPromptBuilder] = None,
        citation_validator: Optional[CitationValidator] = None,
    ) -> None:
        if llm_client is not None:
            self.llm_client = llm_client
        else:
            try:
                from app.core.config import get_settings
                settings = get_settings()
                base_url = getattr(settings, "LOCAL_LLM_URL", "http://localhost:11434") or "http://localhost:11434"
                model_name = getattr(settings, "LOCAL_LLM_MODEL", "llama3.2") or "llama3.2"
                timeout = float(getattr(settings, "LOCAL_LLM_TIMEOUT", 5.0) or 5.0)
                self.llm_client = LocalLLMClient(base_url=base_url, model_name=model_name, timeout_seconds=timeout)
            except Exception:
                import os
                base_url = os.environ.get("LOCAL_LLM_URL", "http://localhost:11434")
                model_name = os.environ.get("LOCAL_LLM_MODEL", "llama3.2")
                timeout = float(os.environ.get("LOCAL_LLM_TIMEOUT", "5.0"))
                self.llm_client = LocalLLMClient(base_url=base_url, model_name=model_name, timeout_seconds=timeout)
        self.prompt_builder = prompt_builder or ExplanationPromptBuilder()
        self.citation_validator = citation_validator or CitationValidator()

    def generate_explanation(self, request: ExplanationRequest) -> ExplanationResponse:
        """Generate structured explanation grounded in deterministic trade data and policy evidence."""
        warnings: List[str] = list(request.warnings)
        requires_human_review: bool = False

        # 1. Financial Safety Invariant Check
        if request.proposal.status == "REJECTED" or not request.proposal.is_executable:
            reason = request.proposal.review_reason or "Hard constraint violation"
            warnings.append(
                f"Proposal {request.proposal_id} is REJECTED ({reason}). Proposed trades are unexecutable."
            )
            requires_human_review = True

        # 2. Check for policy-family version conflicts
        family_versions: Dict[str, set] = {}
        for chunk in request.policy_evidence:
            fam = chunk.policy_family_id or f"DOC-{chunk.document_id}"
            family_versions.setdefault(fam, set()).add(chunk.document_version)

        for fam_id, versions in family_versions.items():
            if len(versions) > 1:
                conflict_msg = (
                    f"Policy family '{fam_id}' retrieved conflicting active versions {sorted(versions)} "
                    f"for as-of date {request.as_of_date.isoformat()}."
                )
                warnings.append(conflict_msg)
                return self._build_evidence_only_fallback(
                    request=request,
                    status=ExplanationStatus.CONFLICT_DETECTED,
                    summary=f"Conflicting policy versions detected for policy family '{fam_id}'. Manual review required.",
                    extra_warnings=warnings,
                    requires_human_review=True,
                )

        # 3. Check for missing policy evidence
        if not request.policy_evidence:
            warnings.append(
                f"No policy evidence found covering rebalancing mandate as of {request.as_of_date.isoformat()}."
            )
            return self._build_evidence_only_fallback(
                request=request,
                status=ExplanationStatus.INSUFFICIENT_EVIDENCE,
                summary="Proposal generated without active policy evidence. Compliance must be verified manually.",
                extra_warnings=warnings,
                requires_human_review=True,
            )

        # 4. Invoke LLM with bounded prompt
        prompt = self.prompt_builder.build_prompt(request)
        try:
            raw_answer = self.llm_client.generate_answer(prompt)
        except LLMUnavailableError as unavail_err:
            logger.warning("LLM daemon unavailable during explanation generation: %s", unavail_err)
            warnings.append(f"LLM unavailable: {unavail_err}")
            return self._build_evidence_only_fallback(
                request=request,
                status=ExplanationStatus.LLM_UNAVAILABLE,
                summary="Deterministic evidence-only summary (LLM unavailable).",
                extra_warnings=warnings,
                requires_human_review=True,
            )
        except Exception as gen_err:
            logger.exception("Error during LLM explanation generation: %s", gen_err)
            warnings.append(f"LLM generation failed: {gen_err}")
            return self._build_evidence_only_fallback(
                request=request,
                status=ExplanationStatus.VALIDATION_FAILED,
                summary="Deterministic evidence-only summary (LLM generation error).",
                extra_warnings=warnings,
                requires_human_review=True,
            )

        # 5. Parse and validate LLM structured response
        parsed_data = self._parse_json_response(raw_answer)
        if not parsed_data:
            warnings.append("LLM returned malformed non-JSON output: using deterministic fallback.")
            return self._build_evidence_only_fallback(
                request=request,
                status=ExplanationStatus.VALIDATION_FAILED,
                summary="Deterministic evidence-only summary (malformed LLM output).",
                extra_warnings=warnings,
                requires_human_review=True,
            )

        # 6. Extract fields and strictly ground trade explanations
        summary = str(parsed_data.get("summary", "Portfolio rebalancing proposal explanation.")).strip()
        rebalancing_reasons = [str(r).strip() for r in parsed_data.get("rebalancing_reasons", []) if str(r).strip()]
        allocation_observations = [str(o).strip() for o in parsed_data.get("allocation_observations", []) if str(o).strip()]
        policy_findings = [str(p).strip() for p in parsed_data.get("policy_findings", []) if str(p).strip()]

        raw_trade_map = {}
        for item in parsed_data.get("trade_explanations", []):
            if isinstance(item, dict) and "trade_id" in item:
                raw_trade_map[str(item["trade_id"])] = str(item.get("explanation", "")).strip()

        # Build trade explanations from deterministic trades
        trade_items: List[TradeExplanationItem] = []
        for t in request.proposal.trades:
            exp_text = raw_trade_map.get(
                t.trade_id,
                f"{t.trade_side} {t.quantity} shares of {t.symbol or t.instrument_id} at ${t.unit_price} to restore target allocation.",
            )
            trade_items.append(
                TradeExplanationItem(
                    trade_id=t.trade_id,
                    instrument_id=t.instrument_id,
                    symbol=t.symbol,
                    trade_side=t.trade_side,
                    quantity=t.quantity,
                    unit_price=t.unit_price,
                    trade_value=t.trade_value,
                    fee_amount=t.fee_amount,
                    status=t.status,
                    explanation=exp_text,
                )
            )

        # 7. Extract and validate citations across all text
        corpus_for_citations = " ".join(
            [summary] + rebalancing_reasons + policy_findings + [t.explanation for t in trade_items]
        )
        validated_citations, citation_warnings = self.citation_validator.extract_and_filter_citations(
            corpus_for_citations, request.policy_evidence
        )
        warnings.extend(citation_warnings)

        return ExplanationResponse(
            workflow_id=request.workflow_id,
            portfolio_id=request.portfolio_id,
            proposal_id=request.proposal_id,
            as_of_date=request.as_of_date,
            status=ExplanationStatus.GENERATED,
            summary=summary,
            rebalancing_reasons=rebalancing_reasons,
            trade_explanations=trade_items,
            allocation_observations=allocation_observations,
            policy_findings=policy_findings,
            citations=validated_citations,
            warnings=warnings,
            requires_human_review=requires_human_review or request.proposal.requires_human_review,
        )

    def _parse_json_response(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON object from LLM response text."""
        # Try direct parse
        try:
            return json.loads(text.strip())
        except Exception:
            pass

        # Try extracting markdown json codeblock or first outer {...}
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except Exception:
                pass

        match_bracket = re.search(r"(\{.*\})", text, re.DOTALL)
        if match_bracket:
            try:
                return json.loads(match_bracket.group(1).strip())
            except Exception:
                pass

        return None

    def _build_evidence_only_fallback(
        self,
        request: ExplanationRequest,
        status: ExplanationStatus,
        summary: str,
        extra_warnings: List[str],
        requires_human_review: bool = True,
    ) -> ExplanationResponse:
        """Construct a deterministic, evidence-only explanation without LLM synthesis."""
        trade_items: List[TradeExplanationItem] = []
        for t in request.proposal.trades:
            trade_items.append(
                TradeExplanationItem(
                    trade_id=t.trade_id,
                    instrument_id=t.instrument_id,
                    symbol=t.symbol,
                    trade_side=t.trade_side,
                    quantity=t.quantity,
                    unit_price=t.unit_price,
                    trade_value=t.trade_value,
                    fee_amount=t.fee_amount,
                    status=t.status,
                    explanation=(
                        f"Deterministic trade: {t.trade_side} {t.quantity} of {t.symbol or t.instrument_id} "
                        f"at ${t.unit_price} (Notional: ${t.trade_value}, Status: {t.status})."
                    ),
                )
            )

        citations: List[ExplanationCitation] = []
        for chunk in request.policy_evidence:
            citations.append(
                ExplanationCitation(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    policy_family_id=chunk.policy_family_id,
                    document_title=chunk.document_title,
                    version=chunk.document_version,
                    section_title=chunk.section_title,
                    excerpt=chunk.content[:200],
                )
            )

        reasons = [
            f"Pre-trade portfolio value: ${request.proposal.pre_trade_portfolio_value}; post-trade value: ${request.proposal.post_trade_portfolio_value}.",
            f"Total executable trades: {len(request.proposal.trades)}.",
        ]

        return ExplanationResponse(
            workflow_id=request.workflow_id,
            portfolio_id=request.portfolio_id,
            proposal_id=request.proposal_id,
            as_of_date=request.as_of_date,
            status=status,
            summary=summary,
            rebalancing_reasons=reasons,
            trade_explanations=trade_items,
            allocation_observations=[],
            policy_findings=[],
            citations=citations,
            warnings=extra_warnings,
            requires_human_review=requires_human_review,
        )
