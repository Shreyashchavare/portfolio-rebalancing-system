# Technical Reviewer Demo Guide

This guide provides step-by-step instructions for evaluating the **Portfolio Rebalancing Recommendation System** using the automated demonstration script and the FastAPI REST interface.

---

## 1. Prerequisites and Environment Setup

### System Requirements
- **Python**: 3.12+ (tested on Python 3.12.10)
- **Database**: PostgreSQL 15+ (recommended) or SQLite (supported for local evaluation)
- **Local LLM (Optional)**: Ollama serving `llama3:latest` on `http://localhost:11434` (graceful fallback provided if offline)

### Virtual Environment Setup
```powershell
# Activate the existing project virtual environment
.\.venv\Scripts\Activate.ps1

# Verify installed dependencies
python -m pip check
```

### Configuration (`.env`)
Copy the provided `.env.example` to `.env` or set environment variables:
```bash
# SQLite local demo configuration
DATABASE_URL=sqlite:///demo_rebalancing.db
APP_ENV=development
ALLOW_DEV_MOCK_AUTH=true
USE_FAKE_EMBEDDINGS=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:latest
```

---

## 2. Automated Demonstration Walkthrough

The fastest and safest way to evaluate the entire system is through the automated walkthrough script [`scripts/demo_walkthrough.py`](file:///E:/Yottaflex/portfolio-rebalancing-system/scripts/demo_walkthrough.py).

### Quick Execution
```powershell
# Run the complete 9-stage walkthrough
python scripts/demo_walkthrough.py --database-url sqlite:///demo_rebalancing.db
```

### What the Walkthrough Demonstrates

| Stage | Capability | Description |
|---|---|---|
| **Stage 1** | **Database & Migrations** | Validates connectivity, inspects `migration_history`, and applies transactional DDL (000–003) if unapplied. |
| **Stage 2** | **Synthetic Dataset** | Verifies entity tables (`investor_profile`, `portfolio`, `holding`, `market_price`, `fee_schedule`, `constraint`). |
| **Stage 3** | **Policy RAG Ingestion & Search** | Parses markdown policies, chunks, embeds, and executes compliance semantic search with similarity ranking. |
| **Stage 4** | **Portfolio Valuation** | Resolves holdings and historical market prices, computing market values and position age. |
| **Stage 5** | **Drift Analysis** | Compares current asset weights to target allocations, calculating percentage drift, dollar drift, and trigger flags. |
| **Stage 6 & 7** | **Proposal, Simulation & Gatekeeper** | Generates proposed buy/sell trades, calculates tiered fees, runs isolated post-trade simulation, and evaluates hard/soft constraints. |
| **Stage 8** | **Grounded Explanation & Citations** | Synthesizes compliance reasoning supported by exact chunk citations (falls back to evidence excerpts if Ollama is offline). |
| **Stage 9** | **Human Review & Audit Governance** | Demonstrates reviewer decision-making, role enforcement, and queries the append-only `audit_events` trail. |

> [!NOTE]
> The automated walkthrough is completely non-destructive: it does not reset existing databases, does not modify real client assets, and guarantees zero trades are executed against live exchanges.

---

## 3. Interactive FastAPI Manual Evaluation

For reviewers who prefer direct HTTP interaction, follow these steps to start the API and test the endpoints.

### Step 3.1: Initialize Database & Ingest Policies
```powershell
# 1. Apply sequential migrations and seed starter data
python scripts/seed_database.py --database-url sqlite:///demo_rebalancing.db --dataset-dir data/starter

# 2. Ingest compliance policy documents into vector store
python scripts/ingest_policies.py --database-url sqlite:///demo_rebalancing.db --use-fake-embeddings
```

### Step 3.2: Start the FastAPI Server
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive OpenAPI Swagger UI is available at:
`http://127.0.0.1:8000/docs`

---

## 4. Manual API Request Examples

### 4.1. Portfolio Valuation
**Request:**
```http
GET /api/v1/portfolios/PORT-INV-000001-02/valuation?as_of_date=2026-01-15 HTTP/1.1
Host: 127.0.0.1:8000
```

**curl:**
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/portfolios/PORT-INV-000001-02/valuation?as_of_date=2026-01-15"
```

**Expected Response (HTTP 200 OK):**
```json
{
  "portfolio_id": "PORT-INV-000001-02",
  "as_of_date": "2026-01-15",
  "total_market_value": "436718.2847",
  "positions": [
    {
      "holding_id": "HOLD-PORT-INV-000001-02-INS-000018",
      "instrument_id": "INS-000018",
      "symbol": "CSH-USD-MM",
      "asset_class": "CASH",
      "quantity": "25200.0000",
      "unit_price": "1.0000",
      "market_value": "25200.0000",
      "price_date": "2025-02-11"
    }
  ]
}
```

---

### 4.2. Portfolio Drift Analysis
**Request:**
```http
GET /api/v1/portfolios/PORT-INV-000001-02/drift?as_of_date=2026-01-15 HTTP/1.1
Host: 127.0.0.1:8000
```

**curl:**
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/portfolios/PORT-INV-000001-02/drift?as_of_date=2026-01-15"
```

**Expected Response (HTTP 200 OK):**
```json
{
  "portfolio_id": "PORT-INV-000001-02",
  "as_of_date": "2026-01-15",
  "total_market_value": "436718.2847",
  "rebalance_trigger": {
    "status": "TRIGGERED",
    "rebalance_required": true,
    "triggered_asset_classes": ["DEBT"]
  },
  "drifts": [
    {
      "asset_class": "DEBT",
      "target_weight": "35.0000",
      "current_weight": "77.4447",
      "percentage_drift": "42.4447",
      "monetary_drift": "185330.6384",
      "action_signal": "SELL"
    }
  ]
}
```

---

### 4.3. Initiate Orchestrated Workflow Run
Initiates the end-to-end deterministic rebalance workflow, including valuation, drift, proposal generation, policy retrieval, and LLM explanation generation.

**Request:**
```http
POST /api/v1/workflows HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json
Authorization: Bearer dev-reviewer-token

{
  "portfolio_id": "PORT-INV-000001-02",
  "as_of_date": "2026-01-15",
  "request_key": "DEMO-RUN-001",
  "policy_query": "cash buffer and equity limit"
}
```

**curl:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/workflows" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-reviewer-token" \
  -d '{"portfolio_id": "PORT-INV-000001-02", "as_of_date": "2026-01-15", "request_key": "DEMO-RUN-001", "policy_query": "cash buffer and equity limit"}'
```

---

### 4.4. Human Review Approval / Rejection
Governance actions require an authenticated reviewer principal. In development mode with `ALLOW_DEV_MOCK_AUTH=true`, the Bearer token `dev-reviewer-token` establishes identity as `REV-DEV-01` (`REVIEWER`).

#### Reject a Proposal with Mandatory Reason
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/proposals/RB-2026-000004/reject" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-reviewer-token" \
  -d '{"reason": "Quarter-end tax rebalancing deferred to next cycle."}'
```

#### Approve an Eligible Proposal
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/proposals/RB-2026-000004/approve" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-reviewer-token" \
  -d '{"notes": "Rebalancing strategy verified against risk profile."}'
```

#### Query Proposal Audit Events
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/proposals/RB-2026-000004/audit"
```

---

## 5. Authentication & Security Notes

1. **Production Default**: All requests require verified cryptographic Bearer tokens. Client-supplied identities (`X-Reviewer-Id`) are strictly rejected.
2. **Development Mock**: When `APP_ENV=development` and `ALLOW_DEV_MOCK_AUTH=true`, standard test tokens are enabled:
   - `Bearer dev-reviewer-token` -> Role: `REVIEWER`, Principal: `REV-DEV-01`
   - `Bearer dev-admin-token` -> Role: `ADMIN`, Principal: `REV-DEV-ADMIN`
   - `Bearer dev-viewer-token` -> Role: `VIEWER` (rejected with HTTP 403 on approval/rejection endpoints)
3. **Idempotency Protection**: Repeated identical workflow requests with the same `request_key` return existing cached results without duplicate rebalancing runs. Changing parameters with an existing `request_key` returns `HTTP 409 Conflict`.

---

## 6. Troubleshooting

- **Database Connection Refused**:
  - Check that PostgreSQL is running or use SQLite (`sqlite:///demo_rebalancing.db`).
- **Ollama Connection Warning**:
  - The system will log a warning if Ollama is offline and fall back gracefully to structured policy citations. To enable full generative explanations, run:
    ```bash
    ollama run llama3:latest
    ```
- **Permission Denied (HTTP 403)**:
  - Ensure you pass `-H "Authorization: Bearer dev-reviewer-token"`. The endpoint enforces `PERMITTED_APPROVAL_ROLES = {"REVIEWER", "ADMIN", "COMPLIANCE_OFFICER", "PORTFOLIO_MANAGER"}`.

