# Data Dictionary: Policy-Constrained Portfolio Rebalancing Recommendation System

This document provides the definitive data dictionary for the core database entities implemented in Phase 1. The SQLAlchemy declarative models defined in `app/models/` serve as the single source of truth.

---

## Entity Summary

| Table Name | Entity Class | Primary Key | Description |
|---|---|---|---|
| `investor_profile` | `InvestorProfile` | `investor_id` (VARCHAR(20)) | Investor risk profile and client metadata |
| `portfolio` | `Portfolio` | `portfolio_id` (VARCHAR(40)) | Investment portfolio belonging to an investor |
| `instrument` | `Instrument` | `instrument_id` (VARCHAR(20)) | Financial instrument master catalog |
| `holding` | `Holding` | `holding_id` (VARCHAR(100)) | Portfolio position snapshots as of a specific date |
| `market_price` | `MarketPrice` | `id` (BIGINT Identity) | EOD/snapshot market prices per instrument |
| `target_allocation` | `TargetAllocation` | `id` (BIGINT Identity) | Target asset class allocation percentages |
| `fee_schedule` | `FeeSchedule` | `fee_schedule_id` (VARCHAR(20)) | Tiered execution fee schedules |
| `constraint` | `Constraint` | `constraint_id` (VARCHAR(30)) | Policy and risk governance rules |
| `constraint_instrument` | `ConstraintInstrument` | `(constraint_id, instrument_id)` | Bridge table associating constraints with instruments |
| `rebalance_proposal` | `RebalanceProposal` | `proposal_id` (VARCHAR(30)) | Rebalancing recommendations and governance approvals |
| `trade` | `Trade` | `trade_id` (VARCHAR(40)) | Proposed or approved trades within a proposal |

---

## 1. InvestorProfile (`investor_profile`)

Stores individual client/investor identification, naming, and risk profile categories.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `investor_id` | String(20) | No | None | `INV-000001` format | ID | Primary Key | None | Primary key identifier |
| `name` | String | No | None | Non-empty string | Name | None | None | Required client name |
| `risk_category` | Enum / String | No | None | `LOW`, `MODERATE`, `HIGH` | Category | None | None | CHECK constraint: `risk_category IN ('LOW', 'MODERATE', 'HIGH')` |
| `created_at` | DateTime(timezone=True) | No | `func.now()` (UTC) | UTC Timestamp | Timestamp | None | None | Timezone-aware audit creation timestamp |

---

## 2. Portfolio (`portfolio`)

Represents an investment account/portfolio linked to an investor.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `portfolio_id` | String(40) | No | None | `PORT-<investor-id>-01` | ID | Primary Key | None | Primary key identifier |
| `investor_id` | String(20) | No | None | Valid `investor_profile.investor_id` | ID | None | `investor_profile.investor_id` | Required foreign key |
| `portfolio_name` | String | No | None | Non-empty string | Name | None | None | Required descriptive name |
| `base_currency` | String | No | None | ISO 4217 (e.g. `USD`, `EUR`) | Currency | None | None | Required 3-letter currency code |
| `status` | Enum / String | No | None | `ACTIVE`, `INACTIVE` | Status | None | None | CHECK constraint: `status IN ('ACTIVE', 'INACTIVE')` |
| `created_at` | DateTime(timezone=True) | No | `func.now()` (UTC) | UTC Timestamp | Timestamp | None | None | Timezone-aware audit creation timestamp |

---

## 3. Instrument (`instrument`)

Financial instrument master records specifying asset classification and trading units.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `instrument_id` | String(20) | No | None | `INS-000001` | ID | Primary Key | None | Primary key identifier |
| `symbol` | String(20) | No | None | e.g. `AAPL`, `MSFT`, `SPY` | Ticker | Unique | None | Non-nullable, unique ticker symbol |
| `instrument_name` | String | No | None | Non-empty string | Name | None | None | Full instrument name |
| `asset_class` | String | No | None | e.g. `EQUITY`, `FIXED_INCOME`, `CASH`, `COMMODITIES` | Asset Class | None | None | Asset classification identifier |
| `lot_size` | Numeric(18, 4) | No | None | `lot_size > 0` | Units | None | None | CHECK constraint: `lot_size > 0` |
| `is_active` | Boolean | No | `True` | `True`, `False` | Boolean | None | None | Active instrument status |

---

## 4. Holding (`holding`)

Historical and current position quantities held by a portfolio as of a specific date.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `holding_id` | String(100) | No | None | `HOLD-<portfolio-id>-<instrument-id>` | ID | Primary Key | None | Primary key identifier |
| `portfolio_id` | String(40) | No | None | Valid `portfolio.portfolio_id` | ID | Composite Unique | `portfolio.portfolio_id` | Required foreign key |
| `instrument_id` | String(20) | No | None | Valid `instrument.instrument_id` | ID | Composite Unique | `instrument.instrument_id` | Required foreign key |
| `quantity` | Numeric(18, 4) | No | None | `quantity >= 0` | Shares / Units | None | None | CHECK constraint: `quantity >= 0` |
| `as_of_date` | Date | No | None | Valid calendar date | Date | Composite Unique | None | Snapshot date. Unique `(portfolio_id, instrument_id, as_of_date)` |

---

## 5. MarketPrice (`market_price`)

End-of-day or snapshot market valuation for an instrument on a given date.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `id` | BigInteger | No | Identity | Autoincrement integer | Integer | Primary Key | None | Identity primary key (SQLite Integer variant) |
| `instrument_id` | String(20) | No | None | Valid `instrument.instrument_id` | ID | Composite Unique | `instrument.instrument_id` | Required foreign key |
| `price` | Numeric(18, 4) | No | None | `price > 0` | Currency / Unit | None | None | CHECK constraint: `price > 0` |
| `price_date` | Date | No | None | Valid calendar date | Date | Composite Unique | None | Price date. Unique `(instrument_id, price_date)` |
| `source` | String | No | None | e.g. `BLOOMBERG`, `REUTERS`, `SYNTHETIC` | Feed source | None | None | Origin market data provider identifier |

---

## 6. TargetAllocation (`target_allocation`)

Target asset-class percentage allocations governing portfolio rebalancing drift calculations.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `id` | BigInteger | No | Identity | Autoincrement integer | Integer | Primary Key | None | Identity primary key (SQLite Integer variant) |
| `portfolio_id` | String(40) | No | None | Valid `portfolio.portfolio_id` | ID | Composite Unique | `portfolio.portfolio_id` | Required foreign key |
| `asset_class` | String(50) | No | None | e.g. `EQUITY`, `FIXED_INCOME`, `CASH` | Asset Class | Composite Unique | None | Required asset class identifier |
| `target_weight` | Numeric(7, 4) | No | None | `[0.0000, 100.0000]` | Percentage (%) | None | None | CHECK constraint: `target_weight >= 0 AND target_weight <= 100` |
| `effective_from` | Date | No | None | Valid calendar date | Date | Composite Unique | None | Start date. Unique `(portfolio_id, asset_class, effective_from)` |
| `effective_to` | Date | Yes | None | `effective_to >= effective_from` or `NULL` | Date | None | None | CHECK constraint: `effective_to IS NULL OR effective_to >= effective_from` |

---

## 7. FeeSchedule (`fee_schedule`)

Tiered execution fee definitions based on notional trade value.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `fee_schedule_id` | String(20) | No | None | e.g. `FEE-USD-EQ-B1` | ID | Primary Key | None | Primary key identifier |
| `asset_class` | String(50) | No | None | e.g. `EQUITY`, `FIXED_INCOME` | Asset Class | Composite Unique | None | Target asset class identifier |
| `trade_side` | String(4) | No | None | `BUY`, `SELL` | Trade Side | Composite Unique | None | CHECK constraint: `trade_side IN ('BUY', 'SELL')` |
| `min_trade_value` | Numeric(18, 4) | No | None | `min_trade_value >= 0` | Currency notional | Composite Unique | None | Lower tier threshold inclusive. Unique `(asset_class, trade_side, min_trade_value, effective_from)` |
| `max_trade_value` | Numeric(18, 4) | Yes | None | `max_trade_value >= min_trade_value` | Currency notional | None | None | Upper tier threshold inclusive (`NULL` = unbounded ceiling) |
| `fee_rate_bps` | Numeric(10, 4) | No | None | `fee_rate_bps >= 0` | Basis points (bps) | None | None | CHECK constraint: non-negative bps |
| `fixed_fee` | Numeric(18, 4) | No | None | `fixed_fee >= 0` | Currency | None | None | Flat ticket fee charge |
| `minimum_fee` | Numeric(18, 4) | No | None | `minimum_fee >= 0` | Currency | None | None | Minimum fee floor |
| `maximum_fee` | Numeric(18, 4) | Yes | None | `maximum_fee >= minimum_fee` | Currency | None | None | Optional maximum fee ceiling cap |
| `currency` | String(3) | No | None | ISO 4217 (e.g. `USD`, `EUR`) | Currency | None | None | Schedule base currency |
| `effective_from` | Date | No | None | Valid calendar date | Date | Composite Unique | None | Tier effective start date |
| `effective_to` | Date | Yes | None | `effective_to >= effective_from` | Date | None | None | CHECK constraint: `effective_to IS NULL OR effective_to >= effective_from` |
| `is_active` | Boolean | No | `True` | `True`, `False` | Boolean | None | None | Operational status |

---

## 8. Constraint (`constraint`)

Policy and risk governance constraints regulating position sizing, trade sizes, and instrument exclusions.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `constraint_id` | String(30) | No | None | e.g. `CONST-POS-LIMIT-01` | ID | Primary Key | None | Primary key identifier |
| `constraint_name` | String(100) | No | None | Descriptive name | Text | None | None | Non-empty rule title |
| `constraint_type` | String(50) | No | None | `MAX_POSITION_WEIGHT`, `MIN_POSITION_WEIGHT`, `MIN_TRADE_VALUE`, `MAX_TRADE_VALUE`, `MIN_TRADE_QUANTITY`, `MAX_TRADE_QUANTITY`, `EXCLUDED_INSTRUMENT`, `LIQUIDITY_LIMIT` | Rule Type | None | None | CHECK constraint: supported constraint type |
| `scope_type` | String(20) | No | None | `PORTFOLIO`, `ASSET_CLASS`, `INSTRUMENT` | Scope | None | None | CHECK constraint: `scope_type IN ('PORTFOLIO', 'ASSET_CLASS', 'INSTRUMENT')` |
| `scope_reference_id` | String(50) | No | None | Polymorphic identifier | ID | None | None | Validated by helper; no direct DB FK |
| `severity` | String(10) | No | None | `HARD`, `SOFT` | Severity | None | None | CHECK constraint: `severity IN ('HARD', 'SOFT')` |
| `threshold_value` | Numeric(18, 4) | Yes | None | `threshold_value >= 0` | Value | None | None | CHECK constraint: `threshold_value IS NULL OR threshold_value >= 0` |
| `threshold_unit` | String(20) | Yes | None | `PERCENT`, `CURRENCY`, `QUANTITY` | Unit | None | None | Metric unit classification |
| `effective_from` | Date | No | None | Valid calendar date | Date | None | None | Rule activation start date |
| `effective_to` | Date | Yes | None | `effective_to >= effective_from` | Date | None | None | CHECK constraint: `effective_to IS NULL OR effective_to >= effective_from` |
| `is_active` | Boolean | No | `True` | `True`, `False` | Boolean | None | None | Operational status |
| `description` | Text | Yes | None | Free-form explanatory text | Text | None | None | Detailed governance rationale |

---

## 9. ConstraintInstrument (`constraint_instrument`) — Bridge Table

Many-to-many bridge table associating constraints with one or multiple instruments (e.g. `EXCLUDED_INSTRUMENT`).

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `constraint_id` | String(30) | No | None | Valid `constraint.constraint_id` | ID | Composite PK | `constraint.constraint_id` | Composite primary key component |
| `instrument_id` | String(20) | No | None | Valid `instrument.instrument_id` | ID | Composite PK | `instrument.instrument_id` | Composite primary key component |

- **Composite Primary Key**: `(constraint_id, instrument_id)` guarantees uniqueness and prevents duplicate assignments.
- **Audit Rule**: Cascade deletion is omitted to preserve audit integrity.

---

## 10. RebalanceProposal (`rebalance_proposal`)

Rebalancing run recommendation headers containing pre/post valuations and human review decisions.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `proposal_id` | String(30) | No | None | `RB-2026-000001` format | ID | Primary Key | None | Primary key identifier |
| `portfolio_id` | String(40) | No | None | Valid `portfolio.portfolio_id` | ID | None | `portfolio.portfolio_id` | Target portfolio foreign key |
| `status` | String(20) | No | None | `DRAFT`, `PENDING_REVIEW`, `APPROVED`, `REJECTED` | Status | None | None | CHECK constraint: `status IN ('DRAFT', 'PENDING_REVIEW', 'APPROVED', 'REJECTED')` |
| `review_decision` | String(20) | No | None | `PENDING`, `APPROVED`, `REJECTED` | Decision | None | None | CHECK constraint: `review_decision IN ('PENDING', 'APPROVED', 'REJECTED')` |
| `pre_trade_portfolio_value` | Numeric(18, 4) | Yes | None | `>= 0` or `NULL` | Currency | None | None | CHECK constraint: `pre_trade_portfolio_value IS NULL OR >= 0` |
| `post_trade_portfolio_value` | Numeric(18, 4) | Yes | None | `>= 0` or `NULL` | Currency | None | None | CHECK constraint: `post_trade_portfolio_value IS NULL OR >= 0` |
| `created_at` | DateTime(timezone=True) | No | `func.now()` (UTC) | UTC Timestamp | Timestamp | None | None | Creation timestamp |
| `reviewed_at` | DateTime(timezone=True) | Yes | None | UTC Timestamp | Timestamp | None | None | Timestamp of human reviewer decision |
| `review_reason` | Text | Yes | None | Free-form review notes | Text | None | None | Reviewer notes or rejection explanation |

---

## 11. Trade (`trade`)

Proposed rebalancing transactions generated under a specific `RebalanceProposal`.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `trade_id` | String(40) | No | None | Unique trade identifier | ID | Primary Key | None | Primary key identifier |
| `proposal_id` | String(30) | No | None | Valid `rebalance_proposal.proposal_id` | ID | None | `rebalance_proposal.proposal_id` | Parent proposal foreign key |
| `instrument_id` | String(20) | No | None | Valid `instrument.instrument_id` | ID | None | `instrument.instrument_id` | Traded instrument foreign key |
| `fee_schedule_id` | String(20) | Yes | None | Valid `fee_schedule.fee_schedule_id` | ID | None | `fee_schedule.fee_schedule_id` | Nullable foreign key (supports missing-fee anomalies) |
| `trade_side` | String(4) | No | None | `BUY`, `SELL` | Side | None | None | CHECK constraint: `trade_side IN ('BUY', 'SELL')` |
| `quantity` | Numeric(18, 4) | No | None | `quantity > 0` | Shares / Units | None | None | CHECK constraint: strictly positive |
| `unit_price` | Numeric(18, 4) | No | None | `unit_price > 0` | Price / Unit | None | None | CHECK constraint: strictly positive |
| `trade_value` | Numeric(18, 4) | No | None | `trade_value > 0` | Currency notional | None | None | CHECK constraint: strictly positive (`quantity * unit_price`) |
| `fee_amount` | Numeric(18, 4) | No | None | `fee_amount >= 0` | Currency | None | None | CHECK constraint: non-negative fee amount |
| `status` | String(20) | No | None | `PROPOSED`, `BLOCKED`, `APPROVED`, `REJECTED` | Status | None | None | CHECK constraint: `status IN ('PROPOSED', 'BLOCKED', 'APPROVED', 'REJECTED')` |
| `created_at` | DateTime(timezone=True) | No | `func.now()` (UTC) | UTC Timestamp | Timestamp | None | None | Creation timestamp |

---

## Schema Gaps & Architectural Assumptions

1. **Cash Accounting**: The current entity model does not define a separate `CashBalance` or `CashTransaction` table. Cash positions are either represented as `Holding` records with an instrument of `asset_class="CASH"` or tracked within `pre_trade_portfolio_value` / `post_trade_portfolio_value`.
2. **Polymorphic Scope Reference**: In `Constraint`, `scope_reference_id` stores strings referring to either `portfolio_id`, `instrument_id`, or generic asset-class strings. To avoid invalid relational foreign keys, application validation is provided via `validate_scope_reference()`.
3. **Fee Tiers In-Place**: Rather than introducing a normalized parent-child `FeeSchedule` -> `FeeTier` schema, fee tiers are modeled directly on individual `FeeSchedule` rows keyed by `(asset_class, trade_side, min_trade_value, effective_from)`.
4. **Missing Fee Schedule Anomaly Representation**: `Trade.fee_schedule_id` is nullable to allow the rebalancing engine to represent, flag, and block transactions where fee calculation rules are missing.
5. **Preservation of Audit History**: No cascading deletion rules are configured on financial transactions (`Holding`, `Trade`, `RebalanceProposal`, `ConstraintInstrument`) to preserve regulatory and immutable audit trails.

