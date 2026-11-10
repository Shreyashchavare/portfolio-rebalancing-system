"""Tests for dataset configuration parameters and presets."""

from synthetic_data.dataset_config import FULL_CONFIG, STARTER_CONFIG, DatasetConfig


def test_starter_config_parameters_unchanged():
    """Verify STARTER_CONFIG retains exact baseline parameters."""
    assert STARTER_CONFIG.name == "starter"
    assert STARTER_CONFIG.investor_count == 5
    assert STARTER_CONFIG.portfolios_per_investor == 2
    assert STARTER_CONFIG.instrument_count == 20
    assert STARTER_CONFIG.trading_days == 30
    assert STARTER_CONFIG.min_holdings == 3
    assert STARTER_CONFIG.max_holdings == 8
    assert STARTER_CONFIG.proposals_per_portfolio == 1
    assert STARTER_CONFIG.trades_per_proposal == 2
    assert STARTER_CONFIG.seed == 20261022
    assert STARTER_CONFIG.dataset_reference_date == "2026-01-15"
    assert STARTER_CONFIG.reproducible_build_timestamp == "2026-01-15T00:00:00Z"


def test_full_config_parameters_match_challenge_requirements():
    """Verify FULL_CONFIG matches the full-scale challenge targets."""
    assert FULL_CONFIG.name == "full"
    assert FULL_CONFIG.investor_count == 500
    assert FULL_CONFIG.portfolios_per_investor == 2
    assert FULL_CONFIG.investor_count * FULL_CONFIG.portfolios_per_investor == 1000

    assert FULL_CONFIG.instrument_count == 5000
    assert FULL_CONFIG.trading_days == 250
    assert FULL_CONFIG.min_holdings == 4
    assert FULL_CONFIG.max_holdings == 4
    assert FULL_CONFIG.proposals_per_portfolio == 1
    assert FULL_CONFIG.trades_per_proposal == 2
    assert FULL_CONFIG.seed == 20261022
    assert FULL_CONFIG.dataset_reference_date == "2026-01-15"
    assert FULL_CONFIG.reproducible_build_timestamp == "2026-01-15T00:00:00Z"


def test_full_config_exact_holdings_math():
    """Verify that min_holdings == max_holdings == 4 guarantees 5,000 holdings across 1,000 portfolios."""
    portfolios_count = FULL_CONFIG.investor_count * FULL_CONFIG.portfolios_per_investor
    # Each portfolio gets 1 cash position + min_holdings non-cash positions
    holdings_per_portfolio = 1 + FULL_CONFIG.min_holdings
    assert holdings_per_portfolio == 5
    total_holdings = portfolios_count * holdings_per_portfolio
    assert total_holdings == 5000

