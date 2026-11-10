"""Deterministic identifier generation utilities for synthetic portfolio data."""


def generate_investor_id(index: int) -> str:
    """Generate a deterministic, zero-padded investor identifier.

    Format: INV-000001
    """
    if not isinstance(index, int) or index < 1:
        raise ValueError(f"index must be an integer >= 1, got {index}")
    return f"INV-{index:06d}"


def generate_portfolio_id(investor_id: str, index: int = 1) -> str:
    """Generate a deterministic portfolio identifier scoped to an investor.

    Format: PORT-<investor-id>-01
    """
    if not isinstance(investor_id, str) or not investor_id.strip():
        raise ValueError(f"investor_id must be a non-empty string, got {investor_id!r}")
    if not isinstance(index, int) or index < 1:
        raise ValueError(f"index must be an integer >= 1, got {index}")
    return f"PORT-{investor_id.strip()}-{index:02d}"


def generate_instrument_id(index: int) -> str:
    """Generate a deterministic, zero-padded financial instrument identifier.

    Format: INS-000001
    """
    if not isinstance(index, int) or index < 1:
        raise ValueError(f"index must be an integer >= 1, got {index}")
    return f"INS-{index:06d}"


def generate_holding_id(portfolio_id: str, instrument_id: str) -> str:
    """Generate a deterministic holding identifier composed of portfolio and instrument IDs.

    Format: HOLD-<portfolio-id>-<instrument-id>
    """
    if not isinstance(portfolio_id, str) or not portfolio_id.strip():
        raise ValueError(f"portfolio_id must be a non-empty string, got {portfolio_id!r}")
    if not isinstance(instrument_id, str) or not instrument_id.strip():
        raise ValueError(f"instrument_id must be a non-empty string, got {instrument_id!r}")
    return f"HOLD-{portfolio_id.strip()}-{instrument_id.strip()}"


def generate_proposal_id(index: int, year: int = 2026) -> str:
    """Generate a deterministic rebalance proposal identifier.

    Format: RB-2026-000001
    """
    if not isinstance(index, int) or index < 1:
        raise ValueError(f"index must be an integer >= 1, got {index}")
    if not isinstance(year, int) or year < 1900:
        raise ValueError(f"year must be a valid four-digit integer, got {year}")
    return f"RB-{year}-{index:06d}"


def generate_trade_id(index: int) -> str:
    """Generate a deterministic trade identifier.

    Format: TRD-000001
    """
    if not isinstance(index, int) or index < 1:
        raise ValueError(f"index must be an integer >= 1, got {index}")
    return f"TRD-{index:06d}"


def generate_constraint_id(index: int) -> str:
    """Generate a deterministic constraint identifier.

    Format: CST-000001
    """
    if not isinstance(index, int) or index < 1:
        raise ValueError(f"index must be an integer >= 1, got {index}")
    return f"CST-{index:06d}"


def generate_fee_schedule_id(asset_class: str, trade_side: str, tier: int) -> str:
    """Generate a deterministic fee schedule identifier.

    Format: FEE-<AC>-<SIDE>-01
    """
    ac_code = asset_class[:3].upper()
    side_code = trade_side[:1].upper()
    return f"FEE-{ac_code}-{side_code}-{tier:02d}"
