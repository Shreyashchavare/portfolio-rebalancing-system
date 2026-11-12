# Phase 4 — Deterministic Rebalancing Engine

## Objective
Convert portfolio drift into deterministic BUY/SELL recommendations while reusing Phase 3 analytics and existing fee/constraint data.

## Trade generation contract
Return a structured recommendation result containing portfolio and as-of date, starting value and cash, proposed trades, instrument, side, quantity, price, notional, fee and fee-schedule reference, remaining cash, residual drift and diagnostics.

## SELL rules
- Generate sells from overweight asset classes.
- Never sell more than the current holding.
- Never sell cash as an ordinary instrument.
- Allocate sells deterministically across eligible positions.
- Round down to valid instrument lot-size multiples.
- Preserve residual drift instead of creating fractional-lot trades.

## BUY rules
- Generate buys for underweight asset classes.
- Prefer eligible instruments already held.
- If none exist, select deterministically from active, eligible, non-excluded instruments.
- Respect lot sizes and calculate fees before finalizing quantity.
- Never exceed available cash after accounting for sell proceeds and all fees.
- Never recommend excluded instruments.

## Fees and price freshness
- Use the applicable effective fee tier and existing fee calculation rules.
- Missing fee schedules must produce an explicit block/diagnostic, never a zero-fee assumption.
- Missing or unknown price freshness must be surfaced; `is_stale=None` is not fresh.
- Do not invent a stale-price threshold or trading calendar.

## Determinism
Identical input records and as-of date must produce identical ordered recommendations and residuals.
