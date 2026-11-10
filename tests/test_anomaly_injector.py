"""Tests for synthetic anomaly injector and ground-truth tracking."""

from copy import deepcopy
from datetime import date
from decimal import Decimal

from synthetic_data.anomaly_injector import AnomalyInjector, GroundTruthRecord, IssueType
from synthetic_data.generators.constraint_generator import generate_constraints
from synthetic_data.generators.fee_schedule_generator import generate_fee_schedules
from synthetic_data.generators.holding_generator import generate_holdings
from synthetic_data.generators.instrument_generator import generate_instruments
from synthetic_data.generators.investor_generator import generate_investors
from synthetic_data.generators.market_price_generator import generate_market_prices
from synthetic_data.generators.portfolio_generator import generate_portfolios
from synthetic_data.generators.rebalance_proposal_generator import generate_rebalance_proposals
from synthetic_data.generators.target_allocation_generator import generate_target_allocations
from synthetic_data.generators.trade_generator import generate_trades


def _build_test_baseline():
    investors = generate_investors(count=5, seed=123)
    portfolios = generate_portfolios(investors, portfolios_per_investor=2, seed=123)
    instruments = generate_instruments(count=15, seed=123)
    market_prices = generate_market_prices(
        instruments, trading_days=15, start_date=date(2026, 1, 1), seed=123
    )
    target_allocations = generate_target_allocations(portfolios, investors, seed=123)
    holdings = generate_holdings(portfolios, instruments, as_of_date=date(2026, 1, 15), seed=123)
    fee_schedules = generate_fee_schedules()
    constraints, constraint_bridge = generate_constraints(portfolios, instruments, seed=123)
    proposals = generate_rebalance_proposals(portfolios, proposals_per_portfolio=1, seed=123)
    trades = generate_trades(
        proposals,
        holdings,
        instruments,
        market_prices,
        fee_schedules,
        constraints=constraints,
        seed=123,
    )

    return {
        "investor_profile": investors,
        "portfolio": portfolios,
        "instrument": instruments,
        "market_price": market_prices,
        "target_allocation": target_allocations,
        "holding": holdings,
        "fee_schedule": fee_schedules,
        "constraint": constraints,
        "constraint_instrument": constraint_bridge,
        "rebalance_proposal": proposals,
        "trade": trades,
    }


def test_injector_returns_ground_truth_and_anomalous_dataset():
    baseline = _build_test_baseline()
    injector = AnomalyInjector(seed=123)
    anomalous_data, ground_truth = injector.inject_all_anomalies(baseline)

    assert isinstance(ground_truth, list)
    assert len(ground_truth) >= 5
    for gt in ground_truth:
        assert isinstance(gt, GroundTruthRecord)
        assert gt.record_id
        assert gt.entity_type
        assert gt.issue_type in IssueType.__members__.values()
        assert gt.expected_decision in {"REJECT", "BLOCK"}
        assert len(gt.explanation) > 0


def test_baseline_dataset_remains_unmodified():
    baseline = _build_test_baseline()
    original_trades = deepcopy(baseline["trade"])
    original_allocations = deepcopy(baseline["target_allocation"])

    injector = AnomalyInjector(seed=123)
    anomalous_data, _ = injector.inject_all_anomalies(baseline)

    assert baseline["trade"] == original_trades
    assert baseline["target_allocation"] == original_allocations
    assert anomalous_data["trade"] != original_trades or anomalous_data["target_allocation"] != original_allocations


def test_selective_copying_and_memory_isolation():
    baseline = _build_test_baseline()
    injector = AnomalyInjector(seed=123)
    anomalous_data, _ = injector.inject_all_anomalies(baseline)

    # 1. Read-only tables must NOT be deep-copied (shared by reference)
    assert anomalous_data["market_price"] is baseline["market_price"], (
        "market_price was deep-copied, causing memory waste on large datasets"
    )
    assert anomalous_data["holding"] is baseline["holding"], (
        "holding was deep-copied unnecessarily"
    )
    assert anomalous_data["investor_profile"] is baseline["investor_profile"]
    assert anomalous_data["portfolio"] is baseline["portfolio"]
    assert anomalous_data["instrument"] is baseline["instrument"]
    assert anomalous_data["fee_schedule"] is baseline["fee_schedule"]
    assert anomalous_data["constraint"] is baseline["constraint"]

    # 2. Mutated tables MUST be independently copied
    assert anomalous_data["target_allocation"] is not baseline["target_allocation"], (
        "target_allocation must be an independent copy"
    )
    assert anomalous_data["trade"] is not baseline["trade"], (
        "trade must be an independent copy"
    )


def test_anomaly_allocation_sum_mismatch():
    baseline = _build_test_baseline()
    injector = AnomalyInjector(seed=123)
    anomalous_data, ground_truth = injector.inject_allocation_sum_mismatch(baseline)

    mismatch_gts = [gt for gt in ground_truth if gt.issue_type == IssueType.ALLOCATION_SUM_MISMATCH]
    assert len(mismatch_gts) >= 1

    # Check that market_price is preserved by reference in single anomaly calls
    assert anomalous_data["market_price"] is baseline["market_price"]
    assert anomalous_data["target_allocation"] is not baseline["target_allocation"]

    affected_record_id = mismatch_gts[0].record_id
    alloc = next(
        a for a in anomalous_data["target_allocation"]
        if str(a.get("id", a.get("portfolio_id"))) == affected_record_id or a["portfolio_id"] == affected_record_id
    )
    p_id = alloc["portfolio_id"]
    p_allocs = [a for a in anomalous_data["target_allocation"] if a["portfolio_id"] == p_id]
    total_weight = sum(a["target_weight"] for a in p_allocs)
    assert total_weight != Decimal("100.0000")


def test_anomaly_excess_sell_quantity():
    baseline = _build_test_baseline()
    injector = AnomalyInjector(seed=123)
    anomalous_data, ground_truth = injector.inject_excess_sell_quantity(baseline)

    excess_gts = [gt for gt in ground_truth if gt.issue_type == IssueType.EXCESS_SELL_QUANTITY]
    assert len(excess_gts) >= 1

    assert anomalous_data["market_price"] is baseline["market_price"]
    assert anomalous_data["trade"] is not baseline["trade"]

    trade_id = excess_gts[0].record_id
    trade = next(t for t in anomalous_data["trade"] if t["trade_id"] == trade_id)
    assert trade["trade_side"] == "SELL"

    prop = next(p for p in anomalous_data["rebalance_proposal"] if p["proposal_id"] == trade["proposal_id"])
    p_id = prop["portfolio_id"]
    holding = next(
        (h for h in anomalous_data["holding"] if h["portfolio_id"] == p_id and h["instrument_id"] == trade["instrument_id"]),
        None,
    )
    holding_qty = holding["quantity"] if holding else Decimal("0.0000")
    assert trade["quantity"] > holding_qty


def test_anomaly_excluded_instrument_recommended():
    baseline = _build_test_baseline()
    injector = AnomalyInjector(seed=123)
    anomalous_data, ground_truth = injector.inject_excluded_instrument_recommended(baseline)

    excl_gts = [gt for gt in ground_truth if gt.issue_type == IssueType.EXCLUDED_INSTRUMENT_RECOMMENDED]
    assert len(excl_gts) >= 1

    assert anomalous_data["market_price"] is baseline["market_price"]
    assert anomalous_data["trade"] is not baseline["trade"]

    trade_id = excl_gts[0].record_id
    trade = next(t for t in anomalous_data["trade"] if t["trade_id"] == trade_id)

    excluded_inst_ids = {
        c["scope_reference_id"] for c in anomalous_data["constraint"] if c["constraint_type"] == "EXCLUDED_INSTRUMENT"
    }
    assert trade["instrument_id"] in excluded_inst_ids


def test_anomaly_missing_fee():
    baseline = _build_test_baseline()
    injector = AnomalyInjector(seed=123)
    anomalous_data, ground_truth = injector.inject_missing_fee(baseline)

    fee_gts = [gt for gt in ground_truth if gt.issue_type == IssueType.MISSING_FEE]
    assert len(fee_gts) >= 1

    assert anomalous_data["market_price"] is baseline["market_price"]
    assert anomalous_data["trade"] is not baseline["trade"]

    trade_id = fee_gts[0].record_id
    trade = next(t for t in anomalous_data["trade"] if t["trade_id"] == trade_id)
    assert trade["fee_amount"] == Decimal("0.0000") or trade["fee_schedule_id"] is None


def test_anomaly_stale_price_usage():
    baseline = _build_test_baseline()
    injector = AnomalyInjector(seed=123)
    anomalous_data, ground_truth = injector.inject_stale_price_usage(baseline)

    stale_gts = [gt for gt in ground_truth if gt.issue_type == IssueType.STALE_PRICE_USAGE]
    assert len(stale_gts) >= 1

    assert anomalous_data["market_price"] is baseline["market_price"]
    assert anomalous_data["trade"] is not baseline["trade"]

    trade_id = stale_gts[0].record_id
    trade = next(t for t in anomalous_data["trade"] if t["trade_id"] == trade_id)
    assert trade["unit_price"] > Decimal("0")


def test_ground_truth_separation_from_entity_features():
    baseline = _build_test_baseline()
    injector = AnomalyInjector(seed=123)
    anomalous_data, ground_truth = injector.inject_all_anomalies(baseline)

    for entity_name, records in anomalous_data.items():
        for rec in records:
            assert "issue_type" not in rec
            assert "expected_decision" not in rec
            assert "ground_truth" not in rec
