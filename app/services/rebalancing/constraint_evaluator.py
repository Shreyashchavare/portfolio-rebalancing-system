"""Policy constraint evaluation for proposed trades and simulated post-trade states.

Evaluates active portfolio, asset-class, and instrument policy constraints against
proposed trades and simulated holdings, classifying findings as HARD violations or SOFT warnings.
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from app.models.constraint import Constraint
from app.schemas.rebalancing import (
    ConstraintFinding,
    PostTradeSimulationResult,
    ProposedTrade,
)


class ConstraintEvaluator:
    """Evaluates active policy constraints against proposed rebalancing trades and post-trade allocations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def evaluate_constraints(
        self,
        portfolio_id: str,
        as_of_date: date,
        proposed_trades: list[ProposedTrade],
        simulation: PostTradeSimulationResult,
    ) -> tuple[list[ConstraintFinding], list[str], list[str]]:
        """Evaluate active policy constraints effective on as_of_date against trades and simulated state.

        Returns:
            tuple of:
                - findings: list of all evaluated constraint findings (both satisfied and violated)
                - hard_violations: list of violation messages for HARD severity constraints
                - warnings: list of warning messages for non-HARD severity constraints
        """
        constraints = (
            self.session.query(Constraint)
            .filter(
                Constraint.is_active.is_(True),
                Constraint.effective_from <= as_of_date,
                (
                    Constraint.effective_to.is_(None)
                    | (Constraint.effective_to >= as_of_date)
                ),
            )
            .order_by(Constraint.constraint_id)
            .all()
        )

        findings: list[ConstraintFinding] = []
        hard_violations: list[str] = []
        warnings: list[str] = []

        for c in constraints:
            # Check applicability
            applies = False
            if c.scope_type == "PORTFOLIO" and c.scope_reference_id == portfolio_id:
                applies = True
            elif c.scope_type == "ASSET_CLASS":
                applies = True
            elif c.scope_type == "INSTRUMENT":
                applies = True

            if not applies:
                continue

            ctype = c.constraint_type
            is_violated = False
            affected_inst_id: Optional[str] = None
            msg = ""

            # 1. EXCLUDED_INSTRUMENT
            if ctype == "EXCLUDED_INSTRUMENT":
                excluded_ids = {c.scope_reference_id} if c.scope_reference_id else set()
                for inst in c.instruments:
                    excluded_ids.add(inst.instrument_id)

                for t in proposed_trades:
                    if t.trade_side == "BUY" and t.instrument_id in excluded_ids:
                        is_violated = True
                        affected_inst_id = t.instrument_id
                        msg = f"[{c.constraint_type}] Instrument {t.instrument_id} is on the restricted exclusion list (Constraint {c.constraint_id})"
                        break

            # 2. MAX_POSITION_WEIGHT
            elif ctype == "MAX_POSITION_WEIGHT":
                if c.threshold_value is not None:
                    if c.scope_type == "PORTFOLIO" and c.scope_reference_id == portfolio_id:
                        for p in simulation.positions:
                            if p.asset_class != "CASH" and p.post_trade_weight > c.threshold_value:
                                is_violated = True
                                affected_inst_id = p.instrument_id
                                msg = f"[{c.constraint_type}] Position {p.instrument_id} post-trade weight {p.post_trade_weight}% exceeds maximum weight limit of {c.threshold_value}% (Constraint {c.constraint_id})"
                                break
                    elif c.scope_type == "INSTRUMENT":
                        target_id = c.scope_reference_id
                        pos = next((p for p in simulation.positions if p.instrument_id == target_id), None)
                        if pos and pos.post_trade_weight > c.threshold_value:
                            is_violated = True
                            affected_inst_id = target_id
                            msg = f"[{c.constraint_type}] Position {target_id} post-trade weight {pos.post_trade_weight}% exceeds maximum weight limit of {c.threshold_value}% (Constraint {c.constraint_id})"

            # 3. MIN_POSITION_WEIGHT
            elif ctype == "MIN_POSITION_WEIGHT":
                if c.threshold_value is not None:
                    if c.scope_type == "PORTFOLIO" and c.scope_reference_id == portfolio_id:
                        for p in simulation.positions:
                            if p.asset_class != "CASH" and p.post_trade_quantity > Decimal("0.0000") and p.post_trade_weight < c.threshold_value:
                                is_violated = True
                                affected_inst_id = p.instrument_id
                                msg = f"[{c.constraint_type}] Position {p.instrument_id} post-trade weight {p.post_trade_weight}% is below minimum weight limit of {c.threshold_value}% (Constraint {c.constraint_id})"
                                break
                    elif c.scope_type == "INSTRUMENT":
                        target_id = c.scope_reference_id
                        pos = next((p for p in simulation.positions if p.instrument_id == target_id), None)
                        if pos and pos.post_trade_quantity > Decimal("0.0000") and pos.post_trade_weight < c.threshold_value:
                            is_violated = True
                            affected_inst_id = target_id
                            msg = f"[{c.constraint_type}] Position {target_id} post-trade weight {pos.post_trade_weight}% is below minimum weight limit of {c.threshold_value}% (Constraint {c.constraint_id})"

            # 4. MIN_TRADE_VALUE
            elif ctype == "MIN_TRADE_VALUE":
                if c.threshold_value is not None:
                    for t in proposed_trades:
                        match_trade = (
                            (c.scope_type == "PORTFOLIO" and c.scope_reference_id == portfolio_id)
                            or (c.scope_type == "ASSET_CLASS" and c.scope_reference_id == t.asset_class)
                            or (c.scope_type == "INSTRUMENT" and c.scope_reference_id == t.instrument_id)
                        )
                        if match_trade and t.trade_value < c.threshold_value:
                            is_violated = True
                            affected_inst_id = t.instrument_id
                            msg = f"[{c.constraint_type}] Trade on {t.instrument_id} value ${t.trade_value} is below minimum trade value threshold of ${c.threshold_value} (Constraint {c.constraint_id})"
                            break

            # 5. MAX_TRADE_VALUE
            elif ctype == "MAX_TRADE_VALUE":
                if c.threshold_value is not None:
                    for t in proposed_trades:
                        match_trade = (
                            (c.scope_type == "PORTFOLIO" and c.scope_reference_id == portfolio_id)
                            or (c.scope_type == "ASSET_CLASS" and c.scope_reference_id == t.asset_class)
                            or (c.scope_type == "INSTRUMENT" and c.scope_reference_id == t.instrument_id)
                        )
                        if match_trade and t.trade_value > c.threshold_value:
                            is_violated = True
                            affected_inst_id = t.instrument_id
                            msg = f"[{c.constraint_type}] Trade on {t.instrument_id} value ${t.trade_value} exceeds maximum trade value threshold of ${c.threshold_value} (Constraint {c.constraint_id})"
                            break

            # 6. MIN_TRADE_QUANTITY
            elif ctype == "MIN_TRADE_QUANTITY":
                if c.threshold_value is not None:
                    for t in proposed_trades:
                        match_trade = (
                            (c.scope_type == "PORTFOLIO" and c.scope_reference_id == portfolio_id)
                            or (c.scope_type == "INSTRUMENT" and c.scope_reference_id == t.instrument_id)
                        )
                        if match_trade and t.quantity < c.threshold_value:
                            is_violated = True
                            affected_inst_id = t.instrument_id
                            msg = f"[{c.constraint_type}] Trade on {t.instrument_id} quantity {t.quantity} is below minimum trade quantity of {c.threshold_value} (Constraint {c.constraint_id})"
                            break

            # 7. MAX_TRADE_QUANTITY
            elif ctype == "MAX_TRADE_QUANTITY":
                if c.threshold_value is not None:
                    for t in proposed_trades:
                        match_trade = (
                            (c.scope_type == "PORTFOLIO" and c.scope_reference_id == portfolio_id)
                            or (c.scope_type == "INSTRUMENT" and c.scope_reference_id == t.instrument_id)
                        )
                        if match_trade and t.quantity > c.threshold_value:
                            is_violated = True
                            affected_inst_id = t.instrument_id
                            msg = f"[{c.constraint_type}] Trade on {t.instrument_id} quantity {t.quantity} exceeds maximum trade quantity of {c.threshold_value} (Constraint {c.constraint_id})"
                            break

            # 8. LIQUIDITY_LIMIT
            elif ctype == "LIQUIDITY_LIMIT":
                if c.threshold_value is not None:
                    match_liq = (
                        (c.scope_type == "PORTFOLIO" and c.scope_reference_id == portfolio_id)
                        or (c.scope_type == "ASSET_CLASS" and c.scope_reference_id == "CASH")
                    )
                    if match_liq:
                        post_cash_pct = (
                            (simulation.post_trade_cash / simulation.post_trade_portfolio_value * Decimal("100.0000")).quantize(Decimal("0.0001"))
                            if simulation.post_trade_portfolio_value > Decimal("0.0000")
                            else Decimal("0.0000")
                        )
                        if post_cash_pct < c.threshold_value:
                            is_violated = True
                            msg = f"[{c.constraint_type}] Post-trade cash liquidity {post_cash_pct}% is below required liquidity limit of {c.threshold_value}% (Constraint {c.constraint_id})"

            if is_violated:
                if c.severity == "HARD":
                    hard_violations.append(msg)
                else:
                    warnings.append(msg)

            findings.append(
                ConstraintFinding(
                    constraint_id=c.constraint_id,
                    constraint_name=c.constraint_name,
                    constraint_type=c.constraint_type,
                    severity=c.severity,
                    scope_type=c.scope_type,
                    scope_reference_id=c.scope_reference_id,
                    threshold_value=c.threshold_value,
                    threshold_unit=c.threshold_unit,
                    is_violated=is_violated,
                    affected_instrument_id=affected_inst_id,
                    message=msg or "Within configured policy limit",
                )
            )

        return findings, hard_violations, warnings

