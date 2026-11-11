# Portfolio Rebalancing Recommendation System

> **Policy-Constrained, Deterministic Rebalancing Engine with Grounded Semantic Policy Retrieval and Mandatory Human Governance.**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17+-blue.svg)](https://www.postgresql.org/)
[![Tests](https://img.shields.io/badge/Tests-507%20Passed-brightgreen.svg)]()

---

## 1. Project Overview & Problem Statement

Institutional wealth management and retail advisory platforms require continuous portfolio alignment against target asset-class allocations. However, automated rebalancing presents complex financial, legal, and operational risks:
- Uncontrolled trade execution can trigger severe capital gains tax penalties, excessive ticket fees, and cash deficits.
- Portfolios are governed by rigid legal mandates, ESG exclusion lists, and investment policy statements (IPS) that change over time and are written in natural language.
- Generative AI models are prone to hallucinating financial quantities, miscalculating fees, and fabricating compliance justifications.

### The Solution: Deterministic Core + Sandboxed AI
The **YottaFlex Portfolio Rebalancing System** enforces an inviolable separation of concerns:
1. **Mathematical Determinism:** All valuations, target drift calculations, lot-size rounding, tiered execution fee deductions, cash solvency verifications, and post-trade simulations are executed by mathematically pure Python algorithms.
2. **Grounded Compliance Policy RAG:** Investment mandates (PDF and Markdown) are chunked, embedded locally via FastEmbed ONNX (`BAAI/bge-small-en-v1.5`), and retrieved using compliance-filtered cosine similarity.
3. **Sandboxed LLM Explanations:** The LLM summarizes deterministic calculations and cites retrieved policy evidence. It is barred from computing trade quantities, modifying database records, or approving proposals.
4. **Mandatory Human Governance:** Algorithmic recommendations are staged as proposals. Human approval via verified reviewer identity is mandatory prior to any downstream trade execution. Real portfolio holdings are **never mutated**.

---

## 2. Key Objectives & Features

- **Portfolio Valuation & Drift Analytics:** Multi-asset class valuation (`EQUITY`, `FIXED_INCOME`, `CASH`, `COMMODITIES`) with historical price lookup, stale-price diagnostics, and corridor/threshold rebalancing trigger evaluations.
- **Deterministic Trade Generation:** Lot-size integer rounding, tiered broker fee schedules, minimum trade value thresholds, and cash overdraft protection.
- **In-Memory Post-Trade Simulation:** Simulates post-execution quantities, cash balances, and residual drift deltas prior to staging proposals.
- **Constraint Gatekeeper:** Evaluates `HARD` vs `SOFT` constraints. Proposals violating `HARD` constraints (e.g. `EXCLUDED_INSTRUMENT` or `MAX_POSITION_WEIGHT`) are automatically marked `REJECTED`.
- **Relational Vector Store:** Hybrid compliance-filtered semantic search preserving temporal validity (`effective_from <= as_of_date <= effective_to`) and active document status.
- **Agentic Workflow Orchestrator:** Idempotent state machine (`RECEIVED` -> `VALIDATING` -> `ANALYZING` -> `GENERATING_PROPOSAL` -> `RETRIEVING_POLICIES` -> `GENERATING_EXPLANATION` -> `PENDING_HUMAN_REVIEW`).
- **Fail-Closed Security & Governance:** Role-Based Access Control (`PORTFOLIO_MANAGER`, `COMPLIANCE_OFFICER`, `ADMIN`, `REVIEWER`), mandatory rejection justification, and immutable append-only audit event logging.

---

## 3. Technology Stack

- **Backend Framework:** FastAPI 0.110+, Starlette, Uvicorn (ASGI)
- **Database & ORM:** PostgreSQL 17+, SQLAlchemy 2.0+ (Declarative 2.0 mapping), Alembic-compatible baseline DDL
- **Vector Embeddings:** FastEmbed 0.5+ running quantized ONNX models (`BAAI/bge-small-en-v1.5`, 384 dimensions)
- **Local LLM Engine:** Ollama daemon (`llama3` or compatible local LLM) with automated deterministic fallback
- **Data Validation & Typing:** Pydantic 2.6+, Pydantic Settings
- **Testing & Verification:** Pytest 8.4+, HTTPX, AnyIO, SQLite (in-memory and WAL-mode file-backed testing)

---

## 4. Architecture Overview

The system is organized as a **Modular Monolith**:

```text
                                 +---------------------------------------------------+
                                 |              FastAPI Application                  |
                                 +---------------------------------------------------+
                                                           |
                                           +---------------+---------------+
                                           |                               |
                             +---------------------------+   +---------------------------+
                             |   Workflow Orchestration  |   |    Approval Governance    |
                             |      (WorkflowService)    |   |     (ApprovalService)     |
                             +---------------------------+   +---------------------------+
                                           |                               |
                 +-------------------------+-------------------------+     |
                 |                         |                         |     |
   +---------------------------+ +-------------------+ +-----------------+ |
   | PortfolioAnalyticsService | | RebalancingEngine | | PolicyRAGService| |
   +---------------------------+ +-------------------+ +-----------------+ |
                 |                         |                         |     |
                 +-------------------------+-------------------------+     |
                                           |                               |
                             +---------------------------+   +---------------------------+
                             | PostgreSQL Core Database  |   | Append-Only Audit Trail   |
                             |       (15 Tables)         |   |      (audit_events)       |
                             +---------------------------+   +---------------------------+
```

For complete High-Level and Low-Level architecture designs, see [`docs/architecture.md`](file:///e:/Yottaflex/portfolio-rebalancing-system/docs/architecture.md).

---

## 5. Complete Workflow Lifecycle

```text
[1. Request Initiated]
       |---> Validates portfolio existence & checks idempotency key
[2. Portfolio Valuation]
       |---> Evaluates holdings, market prices, and asset class weights
[3. Drift Analysis]
       |---> Compares current allocations to targets; evaluates rebalance corridors
[4. Proposal Generation]
       |---> Calculates lot-sized BUY/SELL trades, applies fee tiers, ensures cash solvency
[5. Gatekeeper & Simulation]
       |---> Evaluates HARD/SOFT constraints; generates post-trade simulated state
[6. Policy Retrieval]
       |---> FastEmbed vector similarity search retrieves governing mandates & ESG exclusions
[7. Grounded Explanation]
       |---> LLM formats summary and cites policy chunks; citations are verified
[8. Human Approval Gating]
       |---> Staged as PENDING_HUMAN_REVIEW; requires explicit authenticated approval
[9. Immutable Audit Event]
       |---> Every review decision is recorded to audit_events table with actor and timestamp
```

---

## 6. Project Directory Structure

```text
portfolio-rebalancing-system/
├── app/
│   ├── api/
│   │   ├── dependencies.py          # Authentication verifiers & RBAC dependencies
│   │   └── v1/
│   │       ├── analytics.py         # Valuation & drift REST endpoints
│   │       ├── approvals.py         # Human approval/rejection & audit endpoints
│   │       ├── policies.py          # Policy ingestion, search & Q&A endpoints
│   │       ├── rebalancing.py       # Standalone proposal generation endpoints
│   │       └── workflows.py         # Unified workflow orchestration endpoints
│   ├── core/
│   │   └── config.py                # Pydantic Settings & environment parsing
│   ├── database/
│   │   └── session.py               # Lazy SQLAlchemy engine & SessionLocal factory
│   ├── models/                      # 15 SQLAlchemy 2.0 ORM database entities
│   │   ├── audit_event.py
│   │   ├── constraint.py
│   │   ├── holding.py
│   │   ├── instrument.py
│   │   ├── policy_document.py
│   │   ├── portfolio.py
│   │   ├── rebalance_proposal.py
│   │   ├── trade.py
│   │   └── workflow_run.py
│   ├── schemas/                     # Strongly-typed Pydantic request/response models
│   └── services/                    # Core business logic services
│       ├── approval/                # ApprovalService & state validation
│       ├── audit/                   # AuditService & immutable logging
│       ├── explanation/             # Grounded prompt building & citation validation
│       ├── orchestration/           # Workflow engine, executor & state machine
│       ├── policy_rag/              # Document extraction, FastEmbed, & VectorStore
│       ├── portfolio_analytics_service.py
│       └── rebalancing_service.py
├── data/
│   ├── starter/                     # 10-portfolio starter synthetic dataset (CSV/JSON/SQL)
│   └── full/                        # 1,000-portfolio full synthetic dataset
├── docs/
│   ├── api-reference.md             # Complete REST API reference (13 endpoints)
│   ├── architecture.md              # Detailed HLD, LLD, diagrams & safety boundaries
│   ├── data-dictionary.md           # Schema definitions for all 15 relational tables
│   └── migrations/                  # Sequential PostgreSQL DDL (000–003)
├── policy_documents/                # Sample Markdown compliance mandates & ESG policies
├── synthetic_data/                  # Synthetic dataset generator & anomaly injector
├── tests/                           # 43 Pytest test suites (507 tests)
├── .env.example                     # Environment template
├── pytest.ini                       # Test runner configuration
└── requirements.txt                 # Project dependencies
```

---

## 7. Prerequisites & Installation

### Prerequisites
- Python 3.12 (compatible with 3.10+)
- PostgreSQL 17+ (or Docker for database containerization)
- Optional: Local Ollama daemon for natural language generation (offline fallback active if omitted)

### Virtual Environment Setup

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Dependency Installation
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 8. Environment Configuration

Copy the sample environment template:

```bash
# Windows
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

### Configuration Variables (`.env`)

| Variable | Default Value | Description |
|---|---|---|
| `APP_ENV` | `development` | Environment mode (`development`, `test`, `production`). In production, mock auth fails closed. |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@localhost:5432/portfolio_rebalancing` | SQLAlchemy connection string |
| `AUTH_PROVIDER` | `production` | Security provider (`production` fails closed; `mock` for local dev/testing) |
| `ENABLE_DEV_MOCK_AUTH` | `false` | Enable development mock reviewer tokens (`true` for local testing) |
| `LOCAL_LLM_URL` | `http://localhost:11434` | Ollama daemon URL |
| `LOCAL_LLM_MODEL` | `llama3.2` | Local LLM model tag |
| `LOCAL_LLM_TIMEOUT` | `5.0` | Ollama HTTP request timeout in seconds |
| `POLICY_DOCUMENTS_DIR` | `policy_documents` | Directory containing policy files |
| `EMBEDDING_MODEL_NAME` | `BAAI/bge-small-en-v1.5` | FastEmbed ONNX embedding model |
| `EMBEDDING_CACHE_DIR` | `None` | Optional custom cache directory for ONNX models |

> [!IMPORTANT]
> To test governance endpoints (`POST /api/v1/workflows`, `POST /api/v1/proposals/*/approve`) in local development, set `ENABLE_DEV_MOCK_AUTH=true` in `.env`.

---

## 9. Automated Database Setup, Migrations & Seeding

The application provides an automated, idempotent migration runner and database seeder:

```bash
# 1. Inspect without modifying (dry-run mode)
python scripts/seed_database.py --dry-run

# 2. Apply migrations (000 -> 003) and seed starter dataset
python scripts/seed_database.py

# 3. Apply migrations only without seeding data
python scripts/seed_database.py --skip-seed

# 4. Explicit database connection URI
python scripts/seed_database.py --database-url "postgresql+psycopg2://postgres:postgres@localhost:5432/portfolio_rebalancing"
```

### Safety Features
- **Deterministic Migration Order**: Strictly applies `000_create_core_tables.sql` -> `001_create_policy_rag_tables.sql` -> `002_add_policy_family_id.sql` -> `003_add_orchestration_and_audit_tables.sql`.
- **Pre-population Guard**: Detects existing data in core tables (`investor_profile`, `portfolio`, `instrument`) and safely stops without duplicating data (use `--force` to override).
- **Full Dataset Protection**: Blocks accidental loading of the 414 MB `data/full` dataset by default.
- **Pre-flight Connectivity Check**: Tests connection with `SELECT 1` before writing.

*(Manual fallback via `psql` is documented in [docs/deployment.md](docs/deployment.md).)*

---

## 10. Synthetic Dataset Generation & Validation

The system includes a reproducible synthetic financial dataset generator:

```bash
# Generate starter dataset (10 portfolios, 20 instruments)
python -m synthetic_data.dataset_builder --config starter

# Generate full benchmark dataset (1,000 portfolios, 5,000 instruments)
python -m synthetic_data.dataset_builder --config full
```

Generated datasets include ground-truth challenge anomalies (cash deficits, stale prices, constraint breaches) and are exported to `data/` in CSV, JSON, and relational SQL format.

---

## 11. Automated Policy Ingestion & Embeddings

Ingest and vectorize compliance policies into the database:

```bash
# 1. Dry-run metadata and extraction validation
python scripts/ingest_policies.py --dry-run

# 2. Automated batch ingestion (PDF, Markdown, TXT)
python scripts/ingest_policies.py

# 3. Offline execution with deterministic fake embeddings (testing without model download)
python scripts/ingest_policies.py --use-fake-embeddings
```

Features:
- Discovers `.pdf`, `.md`, and `.txt` files deterministically.
- Extracts metadata (`title`, `version`, `effective_from`, `policy_family_id`) from markdown headers and companion JSON.
- Idempotently skips already-ingested versions without duplicating chunks.
- Isolates document errors so invalid date bounds do not abort the entire batch.

---

## 12. Local Ollama LLM Setup (Optional)

The system connects to a local Ollama daemon for text explanation generation:

1. Install Ollama from [ollama.com](https://ollama.com).
2. Pull the default model:
   ```bash
   ollama pull llama3
   ```
3. Verify that the daemon is listening:
   ```bash
   curl http://localhost:11434/api/tags
   ```

*Note: If Ollama is offline or uninstalled, the system automatically falls back to deterministic evidence-only summaries and sets workflow status to `REQUIRES_ATTENTION`.*

---

## 13. Starting the Application

Launch the FastAPI application using Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive documentation is available at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **Health Check:** `http://localhost:8000/health`

For complete endpoint documentation and request/response payloads, see [`docs/api-reference.md`](file:///e:/Yottaflex/portfolio-rebalancing-system/docs/api-reference.md).

---

## 14. Running Tests

Run the complete test suite:

```bash
pytest
```

To run a fast, concise summary:
```bash
pytest -q
```

### Test Suite Summary
- **Total Tests:** 507 passed (0 skipped, 0 warnings)
- **Execution Time:** ~25-45 seconds
- **Pass Rate:** 100% across all unit, integration, security, and deployment test suites.

---

## 15. Security Considerations

1. **Untrusted Policy Documents:** Policy files are treated as untrusted text. Filesystem paths are sanitized against directory traversal attacks (`..`). File uploads are bounded by file size limits.
2. **Indirect Prompt Injection Defense:** Retrieved policy text is enclosed within strict data delimiters. The system prompt instructs the model to ignore instructions contained within retrieved policy text.
3. **Fail-Closed Authentication:** Reviewer identity cannot be spoofed via client HTTP headers. In production, unverified tokens return `401 Unauthorized`. Development mock tokens are disabled unless explicitly enabled, and fail immediately if `APP_ENV=production`.
4. **Append-Only Auditing:** Governance decisions are permanently recorded to `audit_events`. Deletion or modification of audit records is impossible through the application layer.

---

## 16. Known Limitations

1. **Execution Venue Integration:** The system generates and approves trade recommendations; it does not route orders to live brokers or exchanges.
2. **Holdings Mutation:** Real portfolio holdings are never mutated by approvals. Custodial updates must be ingested via authoritative external balance feeds.
3. **Cash Ledger:** Cash balances are represented via `Holding` records with `asset_class="CASH"` or calculated within portfolio market valuations; a double-entry cash accounting ledger is not implemented.
4. **PostgreSQL Multi-Process Concurrency:** Thread-level SQLite concurrency is verified with file-backed WAL mode and process locks; high-volume multi-process PostgreSQL stress testing has not yet been performed in live production clustering.
