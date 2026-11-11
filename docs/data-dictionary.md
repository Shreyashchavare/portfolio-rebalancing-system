# Data Dictionary: Policy-Constrained Portfolio Rebalancing Recommendation System

This document provides the definitive data dictionary for all 15 database entities implemented across Phases 1 through 6. The SQLAlchemy declarative models defined in `app/models/` and the PostgreSQL baseline migrations (`docs/migrations/000_create_core_tables.sql` through `003_add_orchestration_and_audit_tables.sql`) serve as the single source of truth.

---

## Entity Summary

| # | Table Name | Entity Class | Primary Key | Description | Defined in Migration |
|---|---|---|---|---|---|
| 1 | `investor_profile` | `InvestorProfile` | `investor_id` (VARCHAR(20)) | Investor risk profile and client metadata | `000` |
| 2 | `portfolio` | `Portfolio` | `portfolio_id` (VARCHAR(40)) | Investment portfolio belonging to an investor | `000` |
| 3 | `instrument` | `Instrument` | `instrument_id` (VARCHAR(20)) | Financial instrument master catalog | `000` |
| 4 | `holding` | `Holding` | `holding_id` (VARCHAR(100)) | Portfolio position snapshots as of a specific date | `000` |
| 5 | `market_price` | `MarketPrice` | `id` (BIGINT Identity) | EOD/snapshot market prices per instrument | `000` |
| 6 | `target_allocation` | `TargetAllocation` | `id` (BIGINT Identity) | Target asset class allocation percentages | `000` |
| 7 | `fee_schedule` | `FeeSchedule` | `fee_schedule_id` (VARCHAR(20)) | Tiered execution fee schedules | `000` |
| 8 | `constraint` | `Constraint` | `constraint_id` (VARCHAR(30)) | Policy and risk governance rules | `000` |
| 9 | `constraint_instrument` | `ConstraintInstrument` | `(constraint_id, instrument_id)` | Bridge table associating constraints with instruments | `000` |
| 10 | `rebalance_proposal` | `RebalanceProposal` | `proposal_id` (VARCHAR(30)) | Rebalancing recommendations and governance approvals | `000` |
| 11 | `trade` | `Trade` | `trade_id` (VARCHAR(40)) | Proposed or approved trades within a proposal | `000` |
| 12 | `policy_documents` | `PolicyDocument` | `id` (VARCHAR(50)) | Ingested investment policy documents and versions | `001`, `002` |
| 13 | `policy_chunks` | `PolicyChunk` | `id` (VARCHAR(60)) | Heading-aware text chunks and embedding vectors | `001` |
| 14 | `workflow_runs` | `WorkflowRun` | `id` (VARCHAR(50)) | Idempotent orchestrated rebalance execution runs | `003` |
| 15 | `audit_events` | `AuditEvent` | `event_id` (VARCHAR(50)) | Immutable append-only governance and operational audit logs | `003` |

---

## 1. InvestorProfile (`investor_profile`)

Stores individual client/investor identification, naming, and risk profile categories.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `investor_id` | String(20) | No | None | `INV-000001` format | ID | Primary Key | None | Primary key identifier |
| `name` | String(255) | No | None | Non-empty string | Name | None | None | Required client name |
| `risk_category` | Enum / String(20) | No | None | `LOW`, `MODERATE`, `HIGH` | Category | None | None | CHECK constraint: `risk_category IN ('LOW', 'MODERATE', 'HIGH')` |
| `created_at` | DateTime(timezone=True) | No | `func.now()` (UTC) | UTC Timestamp | Timestamp | None | None | Timezone-aware audit creation timestamp |

- **Indexes**: `idx_investor_profile_risk_category` on `(risk_category)`.

---

## 2. Portfolio (`portfolio`)

Represents an investment account/portfolio linked to an investor.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `portfolio_id` | String(40) | No | None | `PORT-<investor-id>-01` | ID | Primary Key | None | Primary key identifier |
| `investor_id` | String(20) | No | None | Valid `investor_profile.investor_id` | ID | None | `investor_profile.investor_id` | Required foreign key |
| `portfolio_name` | String(255) | No | None | Non-empty string | Name | None | None | Required descriptive name |
| `base_currency` | String(10) | No | None | ISO 4217 (e.g. `USD`, `EUR`) | Currency | None | None | Required 3-letter currency code |
| `status` | Enum / String(20) | No | None | `ACTIVE`, `INACTIVE` | Status | None | None | CHECK constraint: `status IN ('ACTIVE', 'INACTIVE')` |
| `created_at` | DateTime(timezone=True) | No | `func.now()` (UTC) | UTC Timestamp | Timestamp | None | None | Timezone-aware audit creation timestamp |

- **Indexes**: `idx_portfolio_investor_id` on `(investor_id)`, `idx_portfolio_status` on `(status)`.

---

## 3. Instrument (`instrument`)

Financial instrument master records specifying asset classification and trading units.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `instrument_id` | String(20) | No | None | `INS-000001` | ID | Primary Key | None | Primary key identifier |
| `symbol` | String(20) | No | None | e.g. `AAPL`, `MSFT`, `SPY` | Ticker | Unique | None | Non-nullable, unique ticker symbol (`uq_instrument_symbol`) |
| `instrument_name` | String(255) | No | None | Non-empty string | Name | None | None | Full instrument name |
| `asset_class` | String(50) | No | None | `EQUITY`, `FIXED_INCOME`, `CASH`, `COMMODITIES` | Asset Class | None | None | Asset classification identifier |
| `lot_size` | Numeric(18, 4) | No | None | `lot_size > 0` | Units | None | None | CHECK constraint: `lot_size > 0` (`check_lot_size_positive`) |
| `is_active` | Boolean | No | `True` | `True`, `False` | Boolean | None | None | Active instrument status |

- **Indexes**: `idx_instrument_symbol` on `(symbol)`, `idx_instrument_asset_class` on `(asset_class)`, `idx_instrument_is_active` on `(is_active)`.

---

## 4. Holding (`holding`)

Historical and current position quantities held by a portfolio as of a specific date.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `holding_id` | String(100) | No | None | `HOLD-<portfolio-id>-<instrument-id>` | ID | Primary Key | None | Primary key identifier |
| `portfolio_id` | String(40) | No | None | Valid `portfolio.portfolio_id` | ID | Composite Unique | `portfolio.portfolio_id` | Required foreign key |
| `instrument_id` | String(20) | No | None | Valid `instrument.instrument_id` | ID | Composite Unique | `instrument.instrument_id` | Required foreign key |
| `quantity` | Numeric(18, 4) | No | None | `quantity >= 0` | Shares / Units | None | None | CHECK constraint: `quantity >= 0` (`check_holding_quantity_non_negative`) |
| `as_of_date` | Date | No | None | Valid calendar date | Date | Composite Unique | None | Snapshot date. Unique `(portfolio_id, instrument_id, as_of_date)` |

- **Indexes**: `idx_holding_portfolio_id` on `(portfolio_id)`, `idx_holding_instrument_id` on `(instrument_id)`, `idx_holding_as_of_date` on `(as_of_date)`.

---

## 5. MarketPrice (`market_price`)

End-of-day or snapshot market valuation for an instrument on a given date.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `id` | BigInteger | No | Identity | Autoincrement integer | Integer | Primary Key | None | Identity primary key (SQLite Integer variant) |
| `instrument_id` | String(20) | No | None | Valid `instrument.instrument_id` | ID | Composite Unique | `instrument.instrument_id` | Required foreign key |
| `price` | Numeric(18, 4) | No | None | `price > 0` | Currency / Unit | None | None | CHECK constraint: `price > 0` (`check_market_price_positive`) |
| `price_date` | Date | No | None | Valid calendar date | Date | Composite Unique | None | Price date. Unique `(instrument_id, price_date)` |
| `source` | String(100) | No | None | e.g. `BLOOMBERG`, `REUTERS`, `SYNTHETIC` | Feed source | None | None | Origin market data provider identifier |

- **Indexes**: `idx_market_price_instrument_id` on `(instrument_id)`, `idx_market_price_price_date` on `(price_date)`.

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

- **Indexes**: `idx_target_allocation_portfolio_id` on `(portfolio_id)`, `idx_target_allocation_asset_class` on `(asset_class)`.

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

- **Indexes**: `idx_fee_schedule_lookup` on `(asset_class, trade_side, is_active)`.

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

- **Indexes**: `idx_constraint_type` on `(constraint_type)`, `idx_constraint_scope` on `(scope_type, scope_reference_id)`, `idx_constraint_active_effective` on `(is_active, effective_from, effective_to)`.

---

## 9. ConstraintInstrument (`constraint_instrument`) — Bridge Table

Many-to-many bridge table associating constraints with one or multiple instruments (e.g. `EXCLUDED_INSTRUMENT`).

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `constraint_id` | String(30) | No | None | Valid `constraint.constraint_id` | ID | Composite PK | `constraint.constraint_id` | Composite primary key component |
| `instrument_id` | String(20) | No | None | Valid `instrument.instrument_id` | ID | Composite PK | `instrument.instrument_id` | Composite primary key component |

- **Composite Primary Key**: `(constraint_id, instrument_id)` guarantees uniqueness.
- **Indexes**: `idx_constraint_instrument_instrument_id` on `(instrument_id)`.

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

- **Indexes**: `idx_rebalance_proposal_portfolio_id` on `(portfolio_id)`, `idx_rebalance_proposal_status` on `(status)`, `idx_rebalance_proposal_created_at` on `(created_at)`.

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

- **Indexes**: `idx_trade_proposal_id` on `(proposal_id)`, `idx_trade_instrument_id` on `(instrument_id)`, `idx_trade_fee_schedule_id` on `(fee_schedule_id)`, `idx_trade_status` on `(status)`.

---

## 12. PolicyDocument (`policy_documents`)

Stores investment mandates, regulatory guidelines, and ESG exclusion policies ingested for retrieval-augmented generation.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `id` | String(50) | No | None | `DOC-ESG-001` format | ID | Primary Key | None | Primary key identifier |
| `policy_family_id` | String(50) | Yes | None | `FAM-ESG-EXCLUSION` format | Family ID | None | None | Stable policy family identifier across versions |
| `filename` | String(255) | No | None | e.g. `esg_policy_v1.md` | Name | None | None | Source document filename |
| `title` | String(255) | No | None | Descriptive title | Text | None | None | Policy document title |
| `document_type` | String(50) | No | `'INVESTMENT_POLICY'` | `INVESTMENT_POLICY`, `MANDATE`, `ESG_EXCLUSION`, `REGULATORY` | Type | None | None | CHECK constraint: `chk_policy_doc_type` |
| `version` | String(20) | No | `'1.0'` | Semver or major/minor | Version | None | None | Document version string |
| `effective_from` | Date | No | None | Valid calendar date | Date | None | None | Compliance start date |
| `effective_to` | Date | Yes | None | `effective_to >= effective_from` | Date | None | None | CHECK constraint: `chk_policy_effective_dates` |
| `status` | String(20) | No | `'ACTIVE'` | `ACTIVE`, `SUPERSEDED`, `DRAFT`, `ARCHIVED` | Status | None | None | CHECK constraint: `chk_policy_status` |
| `file_path` | String(500) | No | None | Safe internal path | Path | None | None | Application-validated path (no `..` traversal) |
| `sha256_checksum` | String(64) | No | None | 64-char hex string | Hash | None | None | SHA-256 content integrity hash |
| `uploaded_at` | DateTime(timezone=True) | No | `func.now()` (UTC) | UTC Timestamp | Timestamp | None | None | Ingestion timestamp |

- **Indexes**: `idx_policy_documents_family_id` on `(policy_family_id)`, `idx_policy_documents_status` on `(status)`, `idx_policy_documents_doc_type` on `(document_type)`, `idx_policy_documents_effective` on `(effective_from, effective_to)`, `idx_policy_documents_sha256` on `(sha256_checksum)`.

---

## 13. PolicyChunk (`policy_chunks`)

Embedded section chunks created from policy documents for compliance-aware semantic retrieval.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `id` | String(60) | No | None | `<doc-id>-chunk-<index>` | ID | Primary Key | None | Chunk primary key identifier |
| `document_id` | String(50) | No | None | Valid `policy_documents.id` | ID | None | `policy_documents.id` ON DELETE CASCADE | Parent policy document foreign key |
| `chunk_index` | Integer | No | None | `>= 0` | Index | None | None | CHECK constraint: `chunk_index >= 0` |
| `section_title` | String(255) | Yes | None | Heading text or `None` | Heading | None | None | Nearest enclosing markdown/document heading |
| `content` | Text | No | None | Non-empty chunk text | Text | None | None | Extracted text content |
| `token_count` | Integer | No | None | `token_count > 0` | Tokens | None | None | CHECK constraint: `token_count > 0` |
| `embedding_json` | Text | No | None | Serialized JSON array of floats | Vector | None | None | Quantized embedding representation |
| `embedding_model` | String(100) | No | None | e.g. `BAAI/bge-small-en-v1.5` | Model ID | None | None | Embedding model architecture identifier |
| `created_at` | DateTime(timezone=True) | No | `func.now()` (UTC) | UTC Timestamp | Timestamp | None | None | Creation timestamp |

- **Indexes**: `idx_policy_chunks_doc_id` on `(document_id)`, `idx_policy_chunks_model` on `(embedding_model)`.

---

## 14. WorkflowRun (`workflow_runs`)

Tracks orchestrated rebalancing workflow execution lifecycle, idempotency keys, and staged results.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `id` | String(50) | No | None | `WF-YYYYMMDD-<uuid>` | ID | Primary Key | None | Unique workflow execution identifier |
| `portfolio_id` | String(40) | No | None | Valid `portfolio.portfolio_id` | ID | Composite Unique | `portfolio.portfolio_id` | Target portfolio foreign key |
| `proposal_id` | String(30) | Yes | None | Valid `rebalance_proposal.proposal_id` | ID | None | `rebalance_proposal.proposal_id` | Staged proposal foreign key (set upon generation) |
| `status` | String(30) | No | None | Supported state enum | Status | None | None | CHECK constraint: `check_workflow_run_status_valid` |
| `request_key` | String(100) | No | None | Client-supplied idempotency key | Key | Composite Unique | None | Unique per portfolio (`uq_workflow_runs_portfolio_request_key`) |
| `request_payload` | JSON | Yes | None | Canonical request parameters | JSON | None | None | Serialized canonical request for conflict detection |
| `result_payload` | JSON | Yes | None | Staged workflow results | JSON | None | None | Serialized simulation snapshot and explanations |
| `error_code` | String(50) | Yes | None | e.g. `MISSING_PRICE_DATA` | Code | None | None | Diagnostic error classification code |
| `error_message` | Text | Yes | None | Detailed error string | Text | None | None | System or service exception detail |
| `started_at` | DateTime(timezone=True) | Yes | None | UTC Timestamp | Timestamp | None | None | Workflow execution initiation timestamp |
| `completed_at` | DateTime(timezone=True) | Yes | None | UTC Timestamp | Timestamp | None | None | Terminal state transition timestamp |
| `created_at` | DateTime(timezone=True) | No | `func.now()` (UTC) | UTC Timestamp | Timestamp | None | None | Database record creation timestamp |
| `updated_at` | DateTime(timezone=True) | No | `func.now()` (UTC) | UTC Timestamp | Timestamp | None | None | Record update timestamp |

- **Allowed Status Values**: `'RECEIVED'`, `'VALIDATING'`, `'ANALYZING'`, `'GENERATING_PROPOSAL'`, `'RETRIEVING_POLICIES'`, `'GENERATING_EXPLANATION'`, `'PENDING_HUMAN_REVIEW'`, `'APPROVED'`, `'REJECTED'`, `'COMPLETED'`, `'FAILED'`, `'REQUIRES_ATTENTION'`.
- **Indexes**: `idx_workflow_runs_portfolio_id` on `(portfolio_id)`, `idx_workflow_runs_proposal_id` on `(proposal_id)`, `idx_workflow_runs_status` on `(status)`, `idx_workflow_runs_request_key` on `(request_key)`.

---

## 15. AuditEvent (`audit_events`)

Append-only, immutable regulatory and operational audit log of all human decisions and significant workflow transitions.

| Field Name | Data Type | Nullable | Default | Allowed Values / Format | Units | Uniqueness | Foreign Key | Validation & Constraints |
|---|---|---|---|---|---|---|---|---|
| `event_id` | String(50) | No | None | `AUDIT-YYYYMMDD-<uuid>` | ID | Primary Key | None | Unique audit event identifier |
| `event_type` | String(50) | No | None | `PROPOSAL_APPROVAL`, `PROPOSAL_REJECTION`, etc. | Type | None | None | Governance event category |
| `action` | String(20) | No | None | `APPROVE`, `REJECT`, `INITIATE` | Action | None | None | Specific operation performed |
| `decision` | String(20) | Yes | None | `APPROVED`, `REJECTED`, `PENDING` | Decision | None | None | Reviewer decision outcome |
| `actor_id` | String(50) | No | None | Verified reviewer identifier | ID | None | None | Authenticated principal ID |
| `entity_type` | String(50) | No | None | `PROPOSAL`, `WORKFLOW`, `PORTFOLIO` | Entity | None | None | Target domain entity class |
| `entity_id` | String(50) | No | None | ID of target entity | ID | None | None | Target domain entity primary key |
| `portfolio_id` | String(40) | Yes | None | Valid `portfolio.portfolio_id` | ID | None | `portfolio.portfolio_id` | Associated portfolio foreign key |
| `proposal_id` | String(30) | Yes | None | Valid `rebalance_proposal.proposal_id` | ID | None | `rebalance_proposal.proposal_id` | Associated proposal foreign key |
| `workflow_id` | String(50) | Yes | None | Valid `workflow_runs.id` | ID | None | `workflow_runs.id` | Associated workflow run foreign key |
| `timestamp` | DateTime(timezone=True) | No | `func.now()` (UTC) | UTC Timestamp | Timestamp | None | None | Immutable event creation timestamp |
| `reason` | Text | Yes | None | Non-empty for rejection | Text | None | None | Reviewer rationale or justification |
| `metadata_json` | JSON | Yes | None | Arbitrary context metadata | JSON | None | None | Snapshot metadata (e.g. trade count, client IP) |

- **Indexes**: `idx_audit_events_event_type` on `(event_type)`, `idx_audit_events_action` on `(action)`, `idx_audit_events_actor_id` on `(actor_id)`, `idx_audit_events_entity` on `(entity_type, entity_id)`, `idx_audit_events_portfolio_id` on `(portfolio_id)`, `idx_audit_events_proposal_id` on `(proposal_id)`, `idx_audit_events_workflow_id` on `(workflow_id)`, `idx_audit_events_timestamp` on `(timestamp)`.

---

## Schema Invariants & Architectural Rules

1. **Strict Numeric Precision**:
   - All financial amounts, prices, fees, notional values, and quantities are stored as `NUMERIC(18, 4)`. Floating-point columns (`FLOAT`, `DOUBLE PRECISION`, `REAL`) are strictly prohibited in the core schema to prevent precision loss.
   - Percentage allocations and portfolio weights are stored as `NUMERIC(7, 4)`.
2. **Immutability of Audit Trails**:
   - The `audit_events` table is append-only. No `UPDATE` or `DELETE` endpoints are exposed.
   - Cascade delete is explicitly prohibited on financial entities (`holding`, `trade`, `rebalance_proposal`) to preserve regulatory history. The only table with `ON DELETE CASCADE` is `policy_chunks`, which automatically purges text chunks when a parent `policy_documents` record is deleted.
3. **Identifier Quoting**:
   - The `constraint` table name is an ANSI SQL and PostgreSQL reserved keyword. In all DDL and raw SQL queries, it MUST be quoted as `"constraint"`.
4. **Polymorphic Scope Reference**:
   - In `Constraint`, `scope_reference_id` stores strings referring to either `portfolio_id`, `instrument_id`, or generic asset-class strings. To maintain flexible rule engines without complex inheritance hierarchies, application validation is enforced via `validate_scope_reference()`.
5. **Deterministic Simulation Persistence**:
   - Complete post-trade simulation snapshots (`PostTradeSimulationResult`) are serialized to `workflow_runs.result_payload["simulation"]`. Idempotent retries reconstruct the simulation directly from stored JSON without re-running calculations or mutating database state.
