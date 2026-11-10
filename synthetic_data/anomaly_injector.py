"""Synthetic anomaly injector and ground-truth tracking for challenge evaluation."""

from copy import deepcopy
from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Optional, Sequence, Union

import numpy as np


class IssueType(str, Enum):
    """Supported portfolio rebalancing challenge issue types."""

    ALLOCATION_SUM_MISMATCH = "ALLOCATION_SUM_MISMATCH"
    EXCESS_SELL_QUANTITY = "EXCESS_SELL_QUANTITY"
    EXCLUDED_INSTRUMENT_RECOMMENDED = "EXCLUDED_INSTRUMENT_RECOMMENDED"
    MISSING_FEE = "MISSING_FEE"
    STALE_PRICE_USAGE = "STALE_PRICE_USAGE"


@dataclass(frozen=True)
class GroundTruthRecord:
    """Labelled ground-truth metadata kept completely separate from entity features."""

    record_id: str
    entity_type: str
    issue_type: str
    expected_decision: str
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)


def _copy_dataset_selectively(
    dataset: Mapping[str, list[dict[str, Any]]],
    mutate_tables: Sequence[str],
) -> dict[str, list[dict[str, Any]]]:
    """Create a shallow copy of the dataset mapping, deep-copying only specified mutable tables.

    Preserves references to read-only tables (such as market_price, holding, etc.)
    to avoid multi-gigabyte memory churn at full scale.
    """
    data = dict(dataset)
    for table in mutate_tables:
        if table in dataset:
            data[table] = deepcopy(dataset[table])
    return data


class AnomalyInjector:
    """Injects controlled, labelled challenge anomalies into baseline synthetic datasets with selective copying."""

    def __init__(self, seed: Union[int, np.random.Generator] = 20261022) -> None:
        if isinstance(seed, np.random.Generator):
            self.rng = seed
        else:
            self.rng = np.random.default_rng(seed)

    def _inject_allocation_sum_mismatch_in_place(
        self, data: dict[str, list[dict[str, Any]]]
    ) -> list[GroundTruthRecord]:
        ground_truth: list[GroundTruthRecord] = []
        allocs = data.get("target_allocation", [])
        if not allocs:
            return ground_truth

        target_alloc = allocs[0]
        original_weight = target_alloc["target_weight"]
        # Add 5.0000% to break 100% sum
        corrupted_weight = (original_weight + Decimal("5.0000")).quantize(Decimal("0.0001"))
        target_alloc["target_weight"] = corrupted_weight

        record_id = str(target_alloc.get("id", target_alloc.get("portfolio_id")))
        ground_truth.append(
            GroundTruthRecord(
                record_id=record_id,
                entity_type="target_allocation",
                issue_type=IssueType.ALLOCATION_SUM_MISMATCH.value,
                expected_decision="REJECT",
                explanation=f"Target allocations for portfolio {target_alloc['portfolio_id']} sum to {corrupted_weight + (Decimal('100.0000') - original_weight)}% instead of 100.0000%",
            )
        )
        return ground_truth

    def inject_allocation_sum_mismatch(
        self, dataset: Mapping[str, list[dict[str, Any]]]
    ) -> tuple[dict[str, list[dict[str, Any]]], list[GroundTruthRecord]]:
        """Inject anomaly 1: Portfolio allocation weights do not sum to 100%."""
        data = _copy_dataset_selectively(dataset, ["target_allocation"])
        gt = self._inject_allocation_sum_mismatch_in_place(data)
        return data, gt

    def _inject_excess_sell_quantity_in_place(
        self, data: dict[str, list[dict[str, Any]]]
    ) -> list[GroundTruthRecord]:
        ground_truth: list[GroundTruthRecord] = []
        trades = data.get("trade", [])
        holdings = data.get("holding", [])
        proposals = {p["proposal_id"]: p["portfolio_id"] for p in data.get("rebalance_proposal", [])}

        sell_trades = [t for t in trades if t["trade_side"] == "SELL"]
        if not sell_trades:
            return ground_truth

        target_trade = sell_trades[0]
        p_id = proposals.get(target_trade["proposal_id"])
        inst_id = target_trade["instrument_id"]

        current_holding = next(
            (h for h in holdings if h["portfolio_id"] == p_id and h["instrument_id"] == inst_id),
            None,
        )
        held_qty = current_holding["quantity"] if current_holding else Decimal("0.0000")

        excess_qty = (held_qty + Decimal("500.0000")).quantize(Decimal("0.0001"))
        target_trade["quantity"] = excess_qty
        target_trade["trade_value"] = (excess_qty * target_trade["unit_price"]).quantize(Decimal("0.0001"))

        ground_truth.append(
            GroundTruthRecord(
                record_id=target_trade["trade_id"],
                entity_type="trade",
                issue_type=IssueType.EXCESS_SELL_QUANTITY.value,
                expected_decision="REJECT",
                explanation=f"Trade {target_trade['trade_id']} proposes to sell {excess_qty} units but portfolio only holds {held_qty} units",
            )
        )
        return ground_truth

    def inject_excess_sell_quantity(
        self, dataset: Mapping[str, list[dict[str, Any]]]
    ) -> tuple[dict[str, list[dict[str, Any]]], list[GroundTruthRecord]]:
        """Inject anomaly 2: Trade SELL quantity exceeds available portfolio holding."""
        data = _copy_dataset_selectively(dataset, ["trade"])
        gt = self._inject_excess_sell_quantity_in_place(data)
        return data, gt

    def _inject_excluded_instrument_recommended_in_place(
        self, data: dict[str, list[dict[str, Any]]]
    ) -> list[GroundTruthRecord]:
        ground_truth: list[GroundTruthRecord] = []
        trades = data.get("trade", [])
        constraints = data.get("constraint", [])

        excl_constraints = [c for c in constraints if c["constraint_type"] == "EXCLUDED_INSTRUMENT"]
        if not excl_constraints or not trades:
            return ground_truth

        excl_inst_id = excl_constraints[0]["scope_reference_id"]

        buy_trades = [t for t in trades if t["trade_side"] == "BUY"]
        target_trade = buy_trades[0] if buy_trades else trades[0]
        target_trade["instrument_id"] = excl_inst_id
        target_trade["trade_side"] = "BUY"

        ground_truth.append(
            GroundTruthRecord(
                record_id=target_trade["trade_id"],
                entity_type="trade",
                issue_type=IssueType.EXCLUDED_INSTRUMENT_RECOMMENDED.value,
                expected_decision="REJECT",
                explanation=f"Trade {target_trade['trade_id']} recommends purchasing restricted instrument {excl_inst_id}",
            )
        )
        return ground_truth

    def inject_excluded_instrument_recommended(
        self, dataset: Mapping[str, list[dict[str, Any]]]
    ) -> tuple[dict[str, list[dict[str, Any]]], list[GroundTruthRecord]]:
        """Inject anomaly 3: Trade recommends an excluded instrument."""
        data = _copy_dataset_selectively(dataset, ["trade"])
        gt = self._inject_excluded_instrument_recommended_in_place(data)
        return data, gt

    def _inject_missing_fee_in_place(
        self, data: dict[str, list[dict[str, Any]]]
    ) -> list[GroundTruthRecord]:
        ground_truth: list[GroundTruthRecord] = []
        trades = [t for t in data.get("trade", []) if t.get("fee_amount", Decimal("0")) > Decimal("0")]
        if not trades:
            return ground_truth

        target_trade = trades[-1]
        target_trade["fee_amount"] = Decimal("0.0000")
        target_trade["fee_schedule_id"] = None

        ground_truth.append(
            GroundTruthRecord(
                record_id=target_trade["trade_id"],
                entity_type="trade",
                issue_type=IssueType.MISSING_FEE.value,
                expected_decision="REJECT",
                explanation=f"Trade {target_trade['trade_id']} omitted mandatory transaction fees for non-zero notional {target_trade['trade_value']}",
            )
        )
        return ground_truth

    def inject_missing_fee(
        self, dataset: Mapping[str, list[dict[str, Any]]]
    ) -> tuple[dict[str, list[dict[str, Any]]], list[GroundTruthRecord]]:
        """Inject anomaly 4: Required trading fee is omitted."""
        data = _copy_dataset_selectively(dataset, ["trade"])
        gt = self._inject_missing_fee_in_place(data)
        return data, gt

    def _inject_stale_price_usage_in_place(
        self, data: dict[str, list[dict[str, Any]]]
    ) -> list[GroundTruthRecord]:
        ground_truth: list[GroundTruthRecord] = []
        trades = data.get("trade", [])
        prices = data.get("market_price", [])
        if not trades or not prices:
            return ground_truth

        target_trade = trades[len(trades) // 2]
        inst_id = target_trade["instrument_id"]

        # Efficiently pick the oldest price for this instrument without building a full list
        stale_price_record = next((p for p in prices if p["instrument_id"] == inst_id), None)
        if stale_price_record is not None:
            stale_price = stale_price_record["price"]
        else:
            stale_price = (target_trade["unit_price"] * Decimal("0.75")).quantize(Decimal("0.0001"))

        target_trade["unit_price"] = stale_price
        target_trade["trade_value"] = (target_trade["quantity"] * stale_price).quantize(Decimal("0.0001"))

        ground_truth.append(
            GroundTruthRecord(
                record_id=target_trade["trade_id"],
                entity_type="trade",
                issue_type=IssueType.STALE_PRICE_USAGE.value,
                expected_decision="REJECT",
                explanation=f"Trade {target_trade['trade_id']} was valued using stale unit price {stale_price} instead of current market price",
            )
        )
        return ground_truth

    def inject_stale_price_usage(
        self, dataset: Mapping[str, list[dict[str, Any]]]
    ) -> tuple[dict[str, list[dict[str, Any]]], list[GroundTruthRecord]]:
        """Inject anomaly 5: Stale market price is used without a stale-price flag."""
        data = _copy_dataset_selectively(dataset, ["trade"])
        gt = self._inject_stale_price_usage_in_place(data)
        return data, gt

    def inject_all_anomalies(
        self, dataset: Mapping[str, list[dict[str, Any]]]
    ) -> tuple[dict[str, list[dict[str, Any]]], list[GroundTruthRecord]]:
        """Sequentially inject all 5 challenge anomalies using selective table copies.

        Deep-copies only mutated tables (target_allocation and trade) once.
        Read-only tables like market_price are preserved by reference.
        """
        data = _copy_dataset_selectively(dataset, ["target_allocation", "trade"])
        all_ground_truth: list[GroundTruthRecord] = []

        all_ground_truth.extend(self._inject_allocation_sum_mismatch_in_place(data))
        all_ground_truth.extend(self._inject_excess_sell_quantity_in_place(data))
        all_ground_truth.extend(self._inject_excluded_instrument_recommended_in_place(data))
        all_ground_truth.extend(self._inject_missing_fee_in_place(data))
        all_ground_truth.extend(self._inject_stale_price_usage_in_place(data))

        return data, all_ground_truth
