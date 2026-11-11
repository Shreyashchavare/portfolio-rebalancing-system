# REST API Reference: Portfolio Rebalancing Recommendation System

**Base URL:** `http://localhost:8000`
**API Specification:** OpenAPI 3.1.0 (Interactive Swagger UI available at `/docs`, ReDoc at `/redoc`)
**Data Formats:** JSON (`application/json`)
**Date Format:** ISO 8601 (`YYYY-MM-DD` for dates, `YYYY-MM-DDTHH:MM:SSZ` for timestamps)

---

## 1. Authentication & Authorization Model

### 1.1 Header Format
Governance and workflow initiation endpoints require an authenticated reviewer identity supplied via the standard HTTP `Authorization` header:

```http
Authorization: Bearer <token>
```

### 1.2 Reviewer Roles & Permissions
Four distinct reviewer roles are supported:
- `PORTFOLIO_MANAGER` (Full governance and workflow execution permissions)
- `COMPLIANCE_OFFICER` (Full governance and workflow execution permissions)
- `ADMIN` (Administrative override and review permissions)
- `REVIEWER` (Standard proposal review and approval permissions)
- `VIEWER` (Read-only access; cannot initiate workflows, approve, or reject proposals)

### 1.3 Security Policies
1. **Fail-Closed Default**: In production environments (`APP_ENV=production`), unverified client tokens are rejected with `HTTP 401 Unauthorized`. Arbitrary tokens or client-supplied reviewer headers (`X-Reviewer-Id`) are never trusted.
2. **Development Mock Authentication**: Local testing environments may enable `ENABLE_DEV_MOCK_AUTH=true` in `.env` to test with pre-configured mock tokens:
   - `dev-reviewer-token` (Role: `REVIEWER`, ID: `REV-DEV-01`)
   - `dev-admin-token` (Role: `ADMIN`, ID: `REV-DEV-ADMIN`)
   - `dev-viewer-token` (Role: `VIEWER`, ID: `REV-DEV-VIEWER` — triggers `HTTP 403 Forbidden` on governance actions)

---

## 2. Standard Error Responses

All error responses adhere to standard FastAPI error structures:

```json
{
  "detail": "Descriptive, sanitized error message"
}
```

| HTTP Status | Reason | Typical Scenario |
|---|---|---|
| `400 Bad Request` | Client syntax error | Path traversal attempted (`..`), invalid file extension |
| `401 Unauthorized` | Missing / invalid credentials | Missing Bearer token, expired token, unconfigured IdP |
| `403 Forbidden` | Insufficient permissions | Caller has `VIEWER` role attempting an approval action |
| `404 Not Found` | Entity does not exist | Portfolio ID, proposal ID, or document ID not found in database |
| `409 Conflict` | Idempotency conflict | Request key reused with different request payload parameters |
| `422 Unprocessable Entity` | Business / validation rule failure | Missing market price on as-of date, hard constraint violation, empty rejection reason |
| `500 Internal Server Error` | Unexpected server error | Unhandled system exception (sanitized to prevent internal leaks) |

---

## 3. Endpoints

### 3.1 System Core

#### `GET /health`
- **Purpose**: Verify application health and operational status.
- **Authentication**: None (Public).
- **Parameters**: None.
- **Response (200 OK)**:
```json
{
  "status": "healthy"
}
```

---

### 3.2 Portfolio Analytics

#### `GET /api/v1/portfolios/{portfolio_id}/valuation`
- **Purpose**: Compute aggregate portfolio market valuation, individual position market values, and asset-class weights as of a target date.
- **Authentication**: None.
- **Parameters**:
  - `portfolio_id` (Path, string, required): Target portfolio identifier (e.g. `PORT-000001-01`).
  - `as_of_date` (Query, date, optional): Valuation date (`YYYY-MM-DD`). Defaults to current date if omitted.
- **Response (200 OK)**:
```json
{
  "portfolio_id": "PORT-000001-01",
  "as_of_date": "2026-01-15",
  "total_market_value": "1050000.0000",
  "positions": [
    {
      "holding_id": "HOLD-PORT-000001-01-INS-000001",
      "portfolio_id": "PORT-000001-01",
      "instrument_id": "INS-000001",
      "symbol": "AAPL",
      "instrument_name": "Apple Inc.",
      "asset_class": "EQUITY",
      "quantity": "2500.0000",
      "unit_price": "180.0000",
      "market_value": "450000.0000",
      "price_date": "2026-01-15",
      "price_age_days": 0,
      "is_stale": false,
      "diagnostic": null
    }
  ],
  "asset_classes": [
    {
      "asset_class": "EQUITY",
      "market_value": "750000.0000",
      "current_weight": "71.4286"
    },
    {
      "asset_class": "CASH",
      "market_value": "300000.0000",
      "current_weight": "28.5714"
    }
  ]
}
```
- **Error Statuses**: `404 Not Found` (unknown portfolio), `422 Unprocessable Entity` (missing market price on date).

---

#### `GET /api/v1/portfolios/{portfolio_id}/drift`
- **Purpose**: Evaluate asset class weight drift against target allocations and check if rebalancing triggers have fired.
- **Authentication**: None.
- **Parameters**:
  - `portfolio_id` (Path, string, required): Target portfolio identifier.
  - `as_of_date` (Query, date, optional): As-of evaluation date.
- **Response (200 OK)**:
```json
{
  "portfolio_id": "PORT-000001-01",
  "as_of_date": "2026-01-15",
  "total_market_value": "1050000.0000",
  "drifts": [
    {
      "asset_class": "EQUITY",
      "current_market_value": "750000.0000",
      "target_market_value": "630000.0000",
      "current_weight": "71.4286",
      "target_weight": "60.0000",
      "percentage_drift": "11.4286",
      "monetary_drift": "120000.3000",
      "action_signal": "SELL"
    },
    {
      "asset_class": "CASH",
      "current_market_value": "300000.0000",
      "target_market_value": "420000.0000",
      "current_weight": "28.5714",
      "target_weight": "40.0000",
      "percentage_drift": "-11.4286",
      "monetary_drift": "-120000.3000",
      "action_signal": "BUY"
    }
  ],
  "rebalance_trigger": {
    "status": "TRIGGERED",
    "rebalance_required": true,
    "triggered_asset_classes": ["EQUITY", "CASH"],
    "triggered_positions": [],
    "policy_description": "Drift exceeds absolute 5.0% rebalance corridor threshold"
  }
}
```
- **Error Statuses**: `404 Not Found` (unknown portfolio), `422 Unprocessable Entity` (missing price data).

---

### 3.3 Deterministic Rebalancing Engine

#### `POST /api/v1/portfolios/{portfolio_id}/rebalance/proposals`
- **Purpose**: Generate standalone deterministic recommendations, run in-memory simulation, evaluate constraints, and persist a proposal.
- **Authentication**: None.
- **Parameters**:
  - `portfolio_id` (Path, string, required): Target portfolio identifier.
  - `as_of_date` (Query, date, optional): Fallback evaluation date.
- **Request Body (optional)**:
```json
{
  "as_of_date": "2026-01-15"
}
```
- **Response (201 Created)**:
```json
{
  "proposal_id": "RB-20260115-000001",
  "portfolio_id": "PORT-000001-01",
  "as_of_date": "2026-01-15",
  "status": "PENDING_REVIEW",
  "review_decision": "PENDING",
  "review_reason": null,
  "pre_trade_portfolio_value": "1050000.0000",
  "post_trade_portfolio_value": "1049875.0000",
  "created_at": "2026-01-15T10:00:00Z",
  "trades": [
    {
      "trade_id": "TRD-20260115-0001",
      "proposal_id": "RB-20260115-000001",
      "instrument_id": "INS-000001",
      "symbol": "AAPL",
      "instrument_name": "Apple Inc.",
      "asset_class": "EQUITY",
      "trade_side": "SELL",
      "quantity": "660.0000",
      "unit_price": "180.0000",
      "trade_value": "118800.0000",
      "fee_amount": "125.0000",
      "fee_schedule_id": "FEE-USD-EQ-B1",
      "status": "PROPOSED",
      "diagnostic": null
    }
  ],
  "simulation": {
    "pre_trade_portfolio_value": "1050000.0000",
    "post_trade_portfolio_value": "1049875.0000",
    "pre_trade_cash": "300000.0000",
    "post_trade_cash": "418675.0000",
    "total_executable_fees": "125.0000",
    "positions": [],
    "asset_classes": [],
    "residual_drifts": {}
  },
  "constraint_findings": [],
  "warnings": [],
  "is_executable": true,
  "requires_human_review": true
}
```
- **Error Statuses**: `404 Not Found`, `422 Unprocessable Entity` (hard constraint violation or missing market price).

---

### 3.4 Policy RAG & Semantic Retrieval

#### `POST /api/v1/policies/ingest`
- **Purpose**: Atomically extract, chunk, embed, and store a policy document (Markdown or PDF) into the relational vector store.
- **Authentication**: None.
- **Request Body**:
```json
{
  "policy_family_id": "FAM-ESG-EXCLUSION",
  "title": "ESG Exclusion Policy",
  "document_type": "ESG_EXCLUSION",
  "version": "1.0",
  "effective_from": "2026-01-01",
  "effective_to": null,
  "status": "ACTIVE",
  "file_path": "policy_documents/esg_exclusion_policy_v1.md"
}
```
- **Response (201 Created)**:
```json
{
  "id": "DOC-ESG-001",
  "policy_family_id": "FAM-ESG-EXCLUSION",
  "title": "ESG Exclusion Policy",
  "filename": "esg_exclusion_policy_v1.md",
  "document_type": "ESG_EXCLUSION",
  "version": "1.0",
  "chunk_count": 4,
  "sha256_checksum": "a8f3b8c3d9...",
  "uploaded_at": "2026-01-15T12:00:00Z"
}
```
- **Error Statuses**: `400 Bad Request` (path traversal or unsupported file type), `404 Not Found` (source file missing), `422 Unprocessable Entity` (version conflict or invalid dates).

---

#### `POST /api/v1/policies/search`
- **Purpose**: Execute date-filtered semantic cosine similarity search against active policy chunks. Does not require an active LLM daemon.
- **Authentication**: None.
- **Request Body**:
```json
{
  "query": "What are the rules regarding thermal coal and tobacco?",
  "as_of_date": "2026-01-15",
  "document_type": "ESG_EXCLUSION",
  "top_k": 3,
  "similarity_threshold": 0.4
}
```
- **Response (200 OK)**:
```json
{
  "query": "What are the rules regarding thermal coal and tobacco?",
  "as_of_date": "2026-01-15",
  "results": [
    {
      "chunk_id": "DOC-ESG-001-chunk-002",
      "document_id": "DOC-ESG-001",
      "policy_family_id": "FAM-ESG-EXCLUSION",
      "document_title": "ESG Exclusion Policy",
      "document_version": "1.0",
      "section_title": "Exclusion Criteria",
      "content": "Zero holdings permitted in companies deriving revenue from tobacco leaf cultivation... Companies generating greater than 5% from thermal coal are barred.",
      "similarity_score": 0.8245,
      "token_count": 85,
      "chunk_index": 2
    }
  ],
  "total_results": 1
}
```

---

#### `POST /api/v1/policies/ask`
- **Purpose**: Ask a natural-language compliance question, retrieve relevant chunks, and generate an answer grounded in cited policy text.
- **Authentication**: None.
- **Request Body**:
```json
{
  "query": "Is thermal coal prohibited?",
  "as_of_date": "2026-01-15",
  "top_k": 3
}
```
- **Response (200 OK)**:
```json
{
  "query": "Is thermal coal prohibited?",
  "as_of_date": "2026-01-15",
  "answer": "Yes. Companies generating greater than 5% of annual revenues from thermal coal extraction are barred [DOC-ESG-001:chunk-002].",
  "has_sufficient_evidence": true,
  "retrieval_status": "ANSWERED",
  "citations": [
    {
      "document_id": "DOC-ESG-001",
      "policy_family_id": "FAM-ESG-EXCLUSION",
      "document_title": "ESG Exclusion Policy",
      "version": "1.0",
      "section_title": "Exclusion Criteria",
      "chunk_id": "DOC-ESG-001-chunk-002",
      "excerpt": "Companies generating greater than 5% from thermal coal are barred."
    }
  ],
  "retrieved_chunks": [],
  "warnings": [],
  "requires_human_review": false
}
```

---

#### `GET /api/v1/policies/{document_id}`
- **Purpose**: Retrieve document metadata and chunk summaries without exposing raw embedding vectors or internal filesystem paths.
- **Authentication**: None.
- **Parameters**: `document_id` (Path, string, required).
- **Response (200 OK)**:
```json
{
  "id": "DOC-ESG-001",
  "policy_family_id": "FAM-ESG-EXCLUSION",
  "title": "ESG Exclusion Policy",
  "filename": "esg_exclusion_policy_v1.md",
  "document_type": "ESG_EXCLUSION",
  "version": "1.0",
  "effective_from": "2026-01-01",
  "effective_to": null,
  "status": "ACTIVE",
  "sha256_checksum": "a8f3b8c3d9...",
  "uploaded_at": "2026-01-15T12:00:00Z",
  "chunk_count": 4,
  "chunks": [
    {
      "id": "DOC-ESG-001-chunk-000",
      "chunk_index": 0,
      "section_title": "Scope and Objectives",
      "token_count": 64,
      "content_preview": "Applies to all investor portfolios designated with an ESG..."
    }
  ]
}
```
- **Error Statuses**: `404 Not Found`.

---

### 3.5 Workflow Orchestration

#### `POST /api/v1/workflows`
- **Purpose**: Initiate or resume an end-to-end orchestrated rebalancing workflow with idempotency protection. Coordinates analytics, proposal generation, simulation, policy retrieval, and grounded explanation.
- **Authentication**: **Mandatory Bearer Token** (`PORTFOLIO_MANAGER`, `COMPLIANCE_OFFICER`, `ADMIN`, `REVIEWER`).
- **Request Body**:
```json
{
  "portfolio_id": "PORT-000001-01",
  "as_of_date": "2026-01-15",
  "request_key": "wf-req-20260115-001",
  "policy_query": "Rebalance portfolio under ESG mandates"
}
```
- **Response (200 OK)**:
```json
{
  "workflow_id": "WF-20260115-A1B2C3D4",
  "portfolio_id": "PORT-000001-01",
  "as_of_date": "2026-01-15",
  "status": "PENDING_HUMAN_REVIEW",
  "request_key": "wf-req-20260115-001",
  "proposal_id": "RB-20260115-000001",
  "proposal": {
    "proposal_id": "RB-20260115-000001",
    "portfolio_id": "PORT-000001-01",
    "as_of_date": "2026-01-15",
    "status": "PENDING_REVIEW",
    "review_decision": "PENDING",
    "review_reason": null,
    "pre_trade_portfolio_value": "1050000.0000",
    "post_trade_portfolio_value": "1049875.0000",
    "created_at": "2026-01-15T10:00:00Z",
    "trades": [],
    "simulation": {
      "pre_trade_portfolio_value": "1050000.0000",
      "post_trade_portfolio_value": "1049875.0000",
      "pre_trade_cash": "300000.0000",
      "post_trade_cash": "418675.0000",
      "total_executable_fees": "125.0000",
      "positions": [],
      "asset_classes": [],
      "residual_drifts": {}
    },
    "constraint_findings": [],
    "warnings": [],
    "is_executable": true,
    "requires_human_review": true
  },
  "explanation": {
    "status": "SUCCESS",
    "summary": "Rebalancing sells overweight equity (AAPL) to align portfolio with 60% equity target allocation while strictly adhering to cash minimums.",
    "citations": [
      {
        "document_id": "DOC-ESG-001",
        "policy_family_id": "FAM-ESG-EXCLUSION",
        "document_title": "ESG Exclusion Policy",
        "version": "1.0",
        "section_title": "Exclusion Criteria",
        "chunk_id": "DOC-ESG-001-chunk-002",
        "excerpt": "Zero holdings permitted in companies deriving revenue..."
      }
    ],
    "warnings": [],
    "requires_human_review": true
  },
  "policy_evidence": [],
  "warnings": [],
  "errors": [],
  "requires_human_review": true,
  "error_code": null,
  "error_message": null,
  "started_at": "2026-01-15T10:00:00Z",
  "completed_at": "2026-01-15T10:00:05Z",
  "created_at": "2026-01-15T10:00:00Z"
}
```
- **Error Statuses**:
  - `401 Unauthorized`: Missing or invalid Bearer token.
  - `403 Forbidden`: Authenticated user lacks reviewer role (e.g. `VIEWER`).
  - `404 Not Found`: `portfolio_id` does not exist in database.
  - `409 Conflict`: `request_key` was already used with different payload parameters.
  - `422 Unprocessable Entity`: Business failure (missing market price data).

---

#### `GET /api/v1/workflows/{workflow_id}`
- **Purpose**: Retrieve the current execution status, proposal, simulation, and explanation for a workflow run.
- **Authentication**: None.
- **Parameters**: `workflow_id` (Path, string, required).
- **Response (200 OK)**: Identical to `WorkflowResponse` schema above.
- **Error Statuses**: `404 Not Found`.

---

### 3.6 Approval Governance & Audit Trail

#### `POST /api/v1/proposals/{proposal_id}/approve`
- **Purpose**: Authorized human reviewer approves an eligible proposal (`PENDING_REVIEW` or `DRAFT`), transitioning its trades to `APPROVED` and recording an atomic audit log.
- **Authentication**: **Mandatory Bearer Token** (`PORTFOLIO_MANAGER`, `COMPLIANCE_OFFICER`, `ADMIN`, `REVIEWER`).
- **Parameters**: `proposal_id` (Path, string, required).
- **Request Body (optional)**:
```json
{
  "notes": "Approved for execution by compliance officer"
}
```
- **Response (200 OK)**:
```json
{
  "proposal_id": "RB-20260115-000001",
  "status": "APPROVED",
  "review_decision": "APPROVED",
  "reviewer_id": "REV-DEV-01",
  "reviewed_at": "2026-01-15T10:30:00Z",
  "review_reason": "Approved for execution by compliance officer",
  "approved_trade_count": 1,
  "rejected_trade_count": 0,
  "blocked_trade_count": 0
}
```
- **Error Statuses**:
  - `401 Unauthorized`: Unauthenticated.
  - `403 Forbidden`: Insufficient role.
  - `404 Not Found`: Proposal ID not found.
  - `422 Unprocessable Entity`: Proposal is not in an approvable state, or contains hard constraint violations.

---

#### `POST /api/v1/proposals/{proposal_id}/reject`
- **Purpose**: Authorized reviewer rejects a proposal, transitioning its trades to `REJECTED` and recording an atomic audit log. Requires a mandatory non-empty justification reason.
- **Authentication**: **Mandatory Bearer Token** (`PORTFOLIO_MANAGER`, `COMPLIANCE_OFFICER`, `ADMIN`, `REVIEWER`).
- **Parameters**: `proposal_id` (Path, string, required).
- **Request Body**:
```json
{
  "reason": "Market volatility warrants pausing equity sales today."
}
```
- **Response (200 OK)**:
```json
{
  "proposal_id": "RB-20260115-000001",
  "status": "REJECTED",
  "review_decision": "REJECTED",
  "reviewer_id": "REV-DEV-01",
  "reviewed_at": "2026-01-15T10:35:00Z",
  "review_reason": "Market volatility warrants pausing equity sales today.",
  "approved_trade_count": 0,
  "rejected_trade_count": 1,
  "blocked_trade_count": 0
}
```
- **Error Statuses**:
  - `401 Unauthorized`: Unauthenticated.
  - `403 Forbidden`: Insufficient role.
  - `404 Not Found`: Proposal not found.
  - `422 Unprocessable Entity`: Reason is empty/whitespace or proposal is already terminal.

---

#### `GET /api/v1/proposals/{proposal_id}/audit`
- **Purpose**: Query chronological, immutable audit events associated with a rebalance proposal.
- **Authentication**: None.
- **Parameters**: `proposal_id` (Path, string, required).
- **Response (200 OK)**:
```json
{
  "events": [
    {
      "event_id": "AUDIT-20260115-001",
      "event_type": "PROPOSAL_APPROVAL",
      "action": "APPROVE",
      "decision": "APPROVED",
      "actor_id": "REV-DEV-01",
      "entity_type": "PROPOSAL",
      "entity_id": "RB-20260115-000001",
      "portfolio_id": "PORT-000001-01",
      "proposal_id": "RB-20260115-000001",
      "workflow_id": "WF-20260115-A1B2C3D4",
      "timestamp": "2026-01-15T10:30:00Z",
      "reason": "Approved for execution by compliance officer",
      "metadata_json": {
        "approved_trade_count": 1,
        "role": "PORTFOLIO_MANAGER"
      }
    }
  ],
  "total_count": 1
}
```
- **Error Statuses**: `404 Not Found`.
