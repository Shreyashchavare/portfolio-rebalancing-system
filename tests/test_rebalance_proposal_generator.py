"""Tests for synthetic rebalance proposal generator."""

from datetime import datetime
from decimal import Decimal

from synthetic_data.generators.investor_generator import generate_investors
from synthetic_data.generators.portfolio_generator import generate_portfolios
from synthetic_data.generators.rebalance_proposal_generator import generate_rebalance_proposals
from synthetic_data.validators.schema_validator import SchemaValidator


def _build_test_portfolios():
    investors = generate_investors(count=3, seed=123)
    return generate_portfolios(investors, portfolios_per_investor=2, seed=123)


def test_generate_proposals_structure():
    portfolios = _build_test_portfolios()
    proposals = generate_rebalance_proposals(portfolios, proposals_per_portfolio=1, seed=123)

    assert len(proposals) > 0
    first = proposals[0]
    expected_fields = {
        "proposal_id",
        "portfolio_id",
        "status",
        "review_decision",
        "pre_trade_portfolio_value",
        "post_trade_portfolio_value",
        "created_at",
        "reviewed_at",
        "review_reason",
    }
    assert set(first.keys()) == expected_fields
    assert isinstance(first["created_at"], datetime)
    if first["pre_trade_portfolio_value"] is not None:
        assert isinstance(first["pre_trade_portfolio_value"], Decimal)


def test_generate_proposals_id_format():
    portfolios = _build_test_portfolios()
    proposals = generate_rebalance_proposals(portfolios, proposals_per_portfolio=1, seed=123, year=2026)

    for p in proposals:
        assert p["proposal_id"].startswith("RB-2026-")


def test_generate_proposals_status_decision_coherence():
    portfolios = _build_test_portfolios()
    proposals = generate_rebalance_proposals(portfolios, proposals_per_portfolio=2, seed=123)

    for p in proposals:
        status = p["status"]
        decision = p["review_decision"]
        if status == "DRAFT":
            assert decision == "PENDING"
            assert p["reviewed_at"] is None
        elif status == "PENDING_REVIEW":
            assert decision == "PENDING"
            assert p["reviewed_at"] is None
        elif status == "APPROVED":
            assert decision == "APPROVED"
            assert p["reviewed_at"] is not None
            assert p["review_reason"] is not None
        elif status == "REJECTED":
            assert decision == "REJECTED"
            assert p["reviewed_at"] is not None
            assert p["review_reason"] is not None


def test_generate_proposals_determinism():
    portfolios = _build_test_portfolios()
    p1 = generate_rebalance_proposals(portfolios, seed=20261022)
    p2 = generate_rebalance_proposals(portfolios, seed=20261022)
    p3 = generate_rebalance_proposals(portfolios, seed=99999)

    assert p1 == p2
    assert p1 != p3


def test_generate_proposals_schema_validation():
    portfolios = _build_test_portfolios()
    proposals = generate_rebalance_proposals(portfolios, seed=123)

    validator = SchemaValidator()
    req_res = validator.validate_required_fields(
        proposals,
        ["proposal_id", "portfolio_id", "status", "review_decision", "created_at"],
        record_id_field="proposal_id",
    )
    assert req_res.passed

    pk_res = validator.validate_primary_key_uniqueness(proposals, "proposal_id")
    assert pk_res.passed

    status_res = validator.validate_enum_values(
        proposals, "status", ["DRAFT", "PENDING_REVIEW", "APPROVED", "REJECTED"]
    )
    assert status_res.passed

    dec_res = validator.validate_enum_values(
        proposals, "review_decision", ["PENDING", "APPROVED", "REJECTED"]
    )
    assert dec_res.passed
