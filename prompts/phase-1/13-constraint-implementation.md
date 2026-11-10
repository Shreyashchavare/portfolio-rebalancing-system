# Prompt P1-13 — Constraint and ConstraintInstrument (TDD)

**AI Tool:** Antigravity  
**Phase:** 1 — Database Foundation  
**Task:** Implement Constraint and ConstraintInstrument entities using TDD

## Prompt

# Phase 1 — Batch 5: Constraint and ConstraintInstrument (TDD)

Existing models: InvestorProfile, Portfolio, Instrument, Holding, MarketPrice, TargetAllocation, FeeSchedule.
Existing test suite: 93 passing tests.

## Objective

Implement the Constraint entity and its many-to-many bridge table for instrument-specific constraints.

## 1. Constraint entity

Create `app/models/constraint.py` with:

- `constraint_id`: String(30), primary key.
- `constraint_name`: String(100), required.
- `constraint_type`: String(50), required. Examples: MAX_POSITION_WEIGHT, MIN_TRADE_VALUE, MIN_TRADE_QUANTITY, EXCLUDED_INSTRUMENT, LIQUIDITY_LIMIT.
- `scope_type`: String(20), required. Allowed: PORTFOLIO, ASSET_CLASS, INSTRUMENT.
- `scope_reference_id`: String(50), required. Stores the relevant portfolio ID, asset-class identifier, or instrument ID according to scope_type.
- `severity`: String(10), required. Allowed: HARD, SOFT.
- `threshold_value`: Numeric(18, 4), nullable. Use Decimal.
- `threshold_unit`: String(20), nullable. Examples: PERCENT, CURRENCY, QUANTITY.
- `effective_from`: Date, required.
- `effective_to`: Date, nullable.
- `is_active`: Boolean, required, default true.
- `description`: Text, nullable.

## 2. ConstraintInstrument bridge table

Create `app/models/constraint_instrument.py` or define a clearly named SQLAlchemy association table in the appropriate model module.

Columns:
- `constraint_id`: String(30), FK to `constraint.constraint_id`, primary key.
- `instrument_id`: String(20), FK to `instrument.instrument_id`, primary key.

Use a composite primary key to prevent duplicate associations.

The bridge table supports constraints applying to multiple specific instruments.

## 3. Database constraints

- Enforce allowed scope_type values.
- Enforce HARD and SOFT severity.
- Enforce valid effective date range: `effective_to IS NULL OR effective_to >= effective_from`.
- Validate that `threshold_value` is nonnegative when supplied.
- Add a CHECK constraint for supported constraint_type values.
- Enforce bridge-table foreign keys and composite primary key.

Important: scope_reference_id is polymorphic. Do not create a misleading ordinary foreign key for it. Validate its reference according to scope_type in application-level validation or a documented validation helper. Do not add unrelated tables.

## 4. Relationships

- Constraint has a many-to-many relationship with Instrument through ConstraintInstrument.
- Instrument should expose the reverse relationship if it can be added without changing existing schema behavior.
- Do not cascade-delete historical constraint records or instruments.

## 5. TDD execution

1. Create tests for both Constraint and ConstraintInstrument before implementation.
2. Cover:
   - Base inheritance and table names.
   - Primary keys and column types.
   - Enum/check constraints.
   - Effective date and threshold validation.
   - Metadata registration.
   - Bridge composite primary key.
   - Both bridge foreign keys.
   - Duplicate association rejection.
   - Many-to-many relationship loading.
   - SQLite insertion/retrieval with FK enforcement.
   - Scope-reference validation helper, if implemented.
3. Run new tests first and verify RED.
4. Implement both models and required exports.
5. Run focused tests and verify GREEN.
6. Run the complete test suite and verify GREEN.

## 6. Restrictions

- Do not modify existing entity schemas except the minimal Instrument relationship needed for many-to-many navigation.
- Do not implement Trade or RebalanceProposal.
- Do not add migrations, services, APIs, or dependencies.
- Use Decimal for numeric thresholds.
- Keep implementation minimal.
- Do not weaken existing tests.

## 7. Prompt record

Save this exact prompt as:
`prompts/phase-1/13-constraint-implementation.md`

Append a brief RED/GREEN execution record and document any schema assumptions.

## Final report

Report changed files, schema decisions, RED/GREEN results, total test count, warnings, and Git status.

Stop after this batch.

---

## Schema Assumptions & Decisions

1. **Polymorphic Scope References**: As required, `scope_reference_id` is a bare `String(50)` without an ordinary foreign key constraint to avoid misleading relational references across disparate entities (`portfolio`, `instrument`, or abstract asset class identifiers). Verification is provided via the documented `validate_scope_reference()` validation helper function.
2. **Supported Constraint Types**: Supported constraint types are enforced via database CHECK constraint (`check_constraint_type_valid`) and typed via `ConstraintType` enum: `MAX_POSITION_WEIGHT`, `MIN_POSITION_WEIGHT`, `MIN_TRADE_VALUE`, `MAX_TRADE_VALUE`, `MIN_TRADE_QUANTITY`, `MAX_TRADE_QUANTITY`, `EXCLUDED_INSTRUMENT`, and `LIQUIDITY_LIMIT`.
3. **Bridge Model**: Implemented as a declarative entity `ConstraintInstrument` in [`app/models/constraint_instrument.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/models/constraint_instrument.py) with composite primary key `(constraint_id, instrument_id)` and foreign keys referencing `constraint.constraint_id` and `instrument.instrument_id`.
4. **Many-to-Many Navigation**: `Constraint.instruments` navigates to `Instrument` via secondary table `constraint_instrument`, and `Instrument.constraints` exposes reverse navigation without mutating any column or table constraints on `instrument`.
5. **No Cascade Deletion**: Bridge table foreign keys and relationships omit cascade delete rules to preserve historical auditing integrity.

---

## Actual Results

### RED Phase
- Executed: `pytest tests/test_constraint.py -v`
- Result: 16 failed out of 16 tests due to missing `Constraint` and `ConstraintInstrument` models.
- All 93 pre-existing tests continued to pass (`pytest -k "not test_constraint" -v`).

### GREEN Phase
- Created [`app/models/constraint.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/models/constraint.py) implementing `Constraint`, `ScopeType`, `ConstraintSeverity`, `ConstraintType`, and `validate_scope_reference()`.
- Created [`app/models/constraint_instrument.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/models/constraint_instrument.py) implementing `ConstraintInstrument` bridge entity.
- Updated [`app/models/instrument.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/models/instrument.py) to declare `constraints` relationship.
- Exported all new entities and enums in [`app/models/__init__.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/models/__init__.py).
- Executed: `pytest -v`
- Result: 109 passed, 0 failed across all 10 test suites (93 existing + 16 new).

