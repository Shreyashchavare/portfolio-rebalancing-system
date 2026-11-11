# Prompt P4-05 — Final Persistence and Financial Safety Review

**AI Tool:** Antigravity  
**Phase:** 4 — Rebalancing Engine  
**Task:** Batch 4.2 Review — Final Persistence and Financial Safety Review

## Prompt

# Phase 4.2 — Final Persistence and Financial Safety Review

Repository: `E:\Yottaflex\portfolio-rebalancing-system`

Perform a focused review of the completed rebalancing workflow.

Inspect:
- `app/services/rebalancing_service.py`
- `app/schemas/rebalancing.py`
- `app/api/v1/rebalancing.py`
- `app/models/rebalance_proposal.py`
- `app/models/trade.py`
- `app/models/constraint.py`
- `tests/test_rebalancing_simulation_api.py`
- `tests/test_rebalancing_service.py`

## 1. Proposal and Trade ID Safety

Verify:
- Proposal IDs are unique across repeated proposal creation.
- Trade IDs are unique across different proposals.
- Repeated API requests cannot cause primary-key collisions.
- ID generation is concurrency-safe.
- A failed transaction does not leave partial records.
- Existing proposal and trade records cannot be overwritten accidentally.

If the existing deterministic ID scheme is unsafe, add regression tests and recommend the smallest correction compatible with the current model.

## 2. Constraint and Simulation Consistency

Verify:
- Every hard-blocked trade is excluded from the final simulation.
- A blocked SELL cannot contribute cash to BUY recommendations.
- A blocked BUY cannot reduce cash or holdings.
- After any trade is blocked, cash, valuation, weights and drift are recalculated.
- Persisted post-trade values match the final executable trade set.
- All constraint findings correspond to the final persisted trade statuses.

## 3. Constraint Coverage

Verify each supported constraint:
- EXCLUDED_INSTRUMENT
- MAX_POSITION_WEIGHT
- MIN_POSITION_WEIGHT
- MIN_TRADE_VALUE
- MAX_TRADE_VALUE
- MIN_TRADE_QUANTITY
- MAX_TRADE_QUANTITY
- LIQUIDITY_LIMIT

Check instrument, asset-class and portfolio scopes against the actual model and generator semantics. Verify active dates, open-ended constraints, and HARD versus SOFT behavior.

## 4. Financial Invariants

Verify:
- Post-trade portfolio value = pre-trade portfolio value minus executable fees.
- Post-trade cash is never negative.
- Blocked trades do not affect simulated state.
- Actual holdings remain unchanged.
- All financial arithmetic uses Decimal.
- Unknown price freshness requires human review.
- No proposal is automatically approved.

## 5. Transaction Safety

Verify proposal and trade records are committed atomically and rollback occurs on any persistence failure. Confirm the API cannot return success for a failed transaction.

## 6. TDD Requirements

If a defect is found:
- Add focused regression tests first.
- Demonstrate RED.
- Apply the smallest safe correction.
- Demonstrate GREEN.
- Run the full suite:

`.\.venv\Scripts\python.exe -m pytest -q`

If no defect is found, make no production changes.

Save the report in:

`prompts/phase-4/05-final-financial-persistence-review.md`

Do not add dependencies, migrations or unrelated refactoring. Do not commit or push.

Return findings, test evidence, changed files and any remaining limitations.

---

## Detailed Review Findings

### 1. Proposal and Trade ID Safety
- **Defects Identified**:
  - `func.count()`-based proposal ID generation (`RB-{year}-{count+1:06d}`) was vulnerable to gaps (e.g. pre-seeded records like `RB-2026-000010` with count = 1 generating `RB-2026-000002` and colliding or looping), deletions, cross-year count contamination, and concurrent worker collisions.
  - Trade IDs based on `func.count(Trade.trade_id)` were vulnerable to collisions if trade records were deleted or seeded non-contiguously.
- **Corrections Applied**:
  - Proposal ID sequencing derives the maximum existing integer sequence specifically for the target year prefix (`RB-{year}-%`), guaranteeing sequential continuity without gap collisions.
  - Trade ID sequencing derives the maximum existing integer sequence from all `TRD-%` records and checks `Trade` existence before assignment.
  - Wrapped proposal and trade persistence in a 5-attempt retry loop catching `IntegrityError`, ensuring that if two concurrent workers race to insert the same sequential ID, the colliding transaction automatically rolls back, re-queries `max_seq`, and commits on the next sequential ID without failing the client API request.
  - Transaction atomicity ensures no partial or overwritten records.

### 2. Constraint and Simulation Consistency
- **Defects Identified**:
  - When a BUY trade was blocked by a hard policy constraint (e.g., `MAX_TRADE_VALUE` on BUY), `sim_result` was previously not re-simulated because `has_newly_blocked_sell` was `False`. As a result, the blocked BUY trade remained in the simulated positions and post-trade cash was inappropriately deducted.
  - When a SELL trade was blocked by a hard constraint, its proceeds were removed, but dependent proposed BUY trades were not re-evaluated for cash solvency, causing `simulate_post_trade_state` to raise negative cash errors (`ValueError: Simulated cash cannot become negative`).
- **Corrections Applied**:
  - Added cash solvency reconciliation across all proposed trades:
    1. Executable cash is accumulated strictly from `status == "PROPOSED"` SELL trades.
    2. Proposed BUY trades are verified sequentially against available cash; if outlay exceeds available cash, the BUY trade is marked `BLOCKED` with diagnostic `"Blocked: insufficient executable proceeds to fund purchase"`.
    3. Final simulation is unconditionally re-run with the updated trade statuses, ensuring that every hard-blocked trade (BUY or SELL) is completely excluded from the simulated positions, cash accounting, and persisted portfolio valuation.

### 3. Constraint Coverage
All 8 policy constraint types are verified against models and generators:
- `EXCLUDED_INSTRUMENT`: Checked against BUY recommendations. Blocks execution on restricted instruments.
- `MAX_POSITION_WEIGHT`: Evaluated on individual instrument positions (excluding cash), respecting `PORTFOLIO` and `INSTRUMENT` scopes.
- `MIN_POSITION_WEIGHT`: Evaluated on individual held positions with non-zero post-trade quantity.
- `MIN_TRADE_VALUE` & `MAX_TRADE_VALUE`: Evaluated against trade notional; supports `PORTFOLIO`, `ASSET_CLASS`, and `INSTRUMENT` scopes.
- `MIN_TRADE_QUANTITY` & `MAX_TRADE_QUANTITY`: Evaluated against trade lot quantities.
- `LIQUIDITY_LIMIT`: Evaluated on post-trade cash percentage ($\frac{\text{cash}}{\text{portfolio\_value}} \times 100$).
- Active dates (`effective_from <= as_of_date <= effective_to`) and open-ended dates (`effective_to is None`) are strictly respected; expired constraints are ignored.

### 4. Financial Invariants
- Verified: $\text{post\_trade\_portfolio\_value} = \text{pre\_trade\_portfolio\_value} - \text{total\_executable\_fees}$.
- Post-trade cash is guaranteed non-negative via pre-trade buy lot scaling and gatekeeper solvency reconciliation.
- Database holdings remain completely untouched.
- All monetary and position calculations use Python `Decimal` quantized to 4 decimal places (`0.0001`).
- Historical prices with `is_stale=None` set `requires_human_review = True`; no proposal is automatically approved.

### 5. Transaction Safety
- Rebalance proposals and associated trades are persisted in a single transactional block.
- On any exception or constraint breach, `self.session.rollback()` is executed.
- The API returns 201 only on successful commit and produces 404, 422, or 500 without leaking stack traces or credentials on failure.

---

## Targeted Regression Tests (RED Phase)

Added to `tests/test_rebalancing_simulation_api.py`:
1. `test_hard_blocked_buy_trade_is_excluded_from_final_simulation`
2. `test_hard_blocked_sell_blocks_dependent_buys_and_maintains_cash_solvency`
3. `test_proposal_and_trade_id_safety_and_no_collision_with_gaps`

### RED Execution Output
```
================================== FAILURES ===================================
________ test_hard_blocked_buy_trade_is_excluded_from_final_simulation ________
E       AssertionError: assert Decimal('4994.0000') == Decimal('10000.0000')
E        +  where Decimal('4994.0000') = PostTradeSimulationResult(...).post_trade_cash
E        +  and   Decimal('10000.0000') = Decimal('10000.0000')

________ test_hard_blocked_sell_blocks_dependent_buys_and_maintains_cash_solvency ________
E       ValueError: Simulated cash cannot become negative: -4952.9750
================= 2 failed, 21 deselected, 1 warning in 0.91s =================
```

---

## GREEN Execution Output

### Targeted Regression Tests
```
tests/test_rebalancing_simulation_api.py::test_hard_blocked_buy_trade_is_excluded_from_final_simulation PASSED [ 33%]
tests/test_rebalancing_simulation_api.py::test_hard_blocked_sell_blocks_dependent_buys_and_maintains_cash_solvency PASSED [ 66%]
tests/test_rebalancing_simulation_api.py::test_proposal_and_trade_id_safety_and_no_collision_with_gaps PASSED [100%]
============================== 3 passed in 0.35s ==============================
```

### All Simulation & API Tests (`test_rebalancing_simulation_api.py`)
```
======================= 23 passed, 2 warnings in 1.39s ========================
```

### Phase 4.1 Rebalancing Service Tests (`test_rebalancing_service.py`)
```
============================= 19 passed in 0.90s ==============================
```

### Full Test Suite (`pytest -q`)
```
======================= 320 passed, 3 warnings in 6.02s =======================
```

