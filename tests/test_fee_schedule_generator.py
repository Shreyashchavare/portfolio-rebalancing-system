"""Tests for synthetic fee schedule generator."""

from datetime import date
from decimal import Decimal

from synthetic_data.generators.fee_schedule_generator import generate_fee_schedules
from synthetic_data.validators.schema_validator import SchemaValidator


def test_generate_fee_schedules_structure():
    fees = generate_fee_schedules()
    assert len(fees) > 0
    first = fees[0]
    expected_fields = {
        "fee_schedule_id",
        "asset_class",
        "trade_side",
        "min_trade_value",
        "max_trade_value",
        "fee_rate_bps",
        "fixed_fee",
        "minimum_fee",
        "maximum_fee",
        "currency",
        "effective_from",
        "effective_to",
        "is_active",
    }
    assert set(first.keys()) == expected_fields
    assert isinstance(first["min_trade_value"], Decimal)
    assert isinstance(first["fee_rate_bps"], Decimal)
    assert isinstance(first["fixed_fee"], Decimal)
    assert isinstance(first["minimum_fee"], Decimal)
    assert isinstance(first["effective_from"], date)
    assert isinstance(first["is_active"], bool)


def test_generate_fee_schedules_asset_classes_and_sides():
    fees = generate_fee_schedules()
    asset_classes = {f["asset_class"] for f in fees}
    sides = {f["trade_side"] for f in fees}

    expected_classes = {"EQUITY", "DEBT", "ETF", "GOLD", "CASH"}
    assert expected_classes.issubset(asset_classes)
    assert sides == {"BUY", "SELL"}


def test_generate_fee_schedules_non_overlapping_tiers():
    fees = generate_fee_schedules()
    from collections import defaultdict
    groups = defaultdict(list)
    for f in fees:
        groups[(f["asset_class"], f["trade_side"], f["effective_from"])].append(f)

    for (ac, side, eff_from), tier_list in groups.items():
        assert len(tier_list) >= 2, f"Should have multiple tiers for {ac} {side}"
        sorted_tiers = sorted(tier_list, key=lambda x: x["min_trade_value"])

        for i in range(len(sorted_tiers) - 1):
            curr_tier = sorted_tiers[i]
            next_tier = sorted_tiers[i + 1]
            assert curr_tier["max_trade_value"] is not None
            assert curr_tier["max_trade_value"] == next_tier["min_trade_value"], (
                f"Tiers overlap or gap in {ac} {side}: {curr_tier['max_trade_value']} != {next_tier['min_trade_value']}"
            )

        assert sorted_tiers[-1]["max_trade_value"] is None, f"Highest tier for {ac} {side} must be open-ended (None)"


def test_generate_fee_schedules_composite_uniqueness():
    fees = generate_fee_schedules()
    seen = set()
    for f in fees:
        key = (f["asset_class"], f["trade_side"], f["min_trade_value"], f["effective_from"])
        assert key not in seen, f"Duplicate tier key: {key}"
        seen.add(key)


def test_generate_fee_schedules_schema_validation():
    fees = generate_fee_schedules()
    validator = SchemaValidator()

    req_res = validator.validate_required_fields(
        fees,
        [
            "fee_schedule_id",
            "asset_class",
            "trade_side",
            "min_trade_value",
            "fee_rate_bps",
            "fixed_fee",
            "minimum_fee",
            "currency",
            "effective_from",
            "is_active",
        ],
        record_id_field="fee_schedule_id",
    )
    assert req_res.passed

    pk_res = validator.validate_primary_key_uniqueness(fees, "fee_schedule_id")
    assert pk_res.passed

    enum_res = validator.validate_enum_values(fees, "trade_side", ["BUY", "SELL"])
    assert enum_res.passed


def test_generate_fee_schedules_determinism():
    f1 = generate_fee_schedules()
    f2 = generate_fee_schedules()
    assert f1 == f2
