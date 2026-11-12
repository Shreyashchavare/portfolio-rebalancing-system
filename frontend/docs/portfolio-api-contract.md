# Portfolio Analytics & Valuation API Contract

**Verified Source Code Audit Date:** 2026-11-12  
**Target Systems:** FastAPI Backend (`app/api/v1/analytics.py`), SQLAlchemy Models (`app/models/`), Pydantic Schemas (`app/schemas/portfolio_analytics.py`), and Frontend Integration (`frontend/src/features/portfolios/`)

---

## 1. Executive Summary & Verification Findings

This document establishes the verified API contract between the YottaFlex FastAPI backend and the React/TypeScript frontend for all portfolio valuation, holdings, asset allocation, and drift monitoring workflows.

### Summary of Backend Endpoints

| Endpoint Path | HTTP Method | Auth Required | Status | Backend Handler |
|---|---|---|---|---|
| `/api/v1/portfolios/{portfolio_id}/valuation` | `GET` | No (Public / Open) | **Verified Implemented** | `app.api.v1.analytics:get_portfolio_valuation` |
| `/api/v1/portfolios/{portfolio_id}/drift` | `GET` | No (Public / Open) | **Verified Implemented** | `app.api.v1.analytics:get_portfolio_drift` |
| `/api/v1/portfolios` | `GET` | — | **Unsupported (Not Implemented)** | *Does not exist in backend routers* |
| `/api/v1/portfolios/{portfolio_id}/valuation/history` | `GET` | — | **Unsupported (Not Implemented)** | *Does not exist in backend routers* |
| `/api/v1/portfolios/{portfolio_id}/revalue` | `POST` | — | **Unsupported (Not Implemented)** | *Dynamically evaluated on GET* |

> [!IMPORTANT]
> **Strict Non-Creation of Backend Endpoints**: As mandated by financial safety guidelines and project boundaries, zero backend endpoints have been added or altered. The frontend must consume only what actually exists.

---

## 2. Verified Endpoint Specifications

### 2.1 `GET /api/v1/portfolios/{portfolio_id}/valuation`

#### Purpose
Computes aggregate portfolio market value, individual holding positions with price freshness/staleness diagnostics, and actual asset-class percentage allocations as of a target date.

#### Request Parameters
- **Path Parameter**:
  - `portfolio_id` (string, required): The unique portfolio identifier (e.g., `PORT-INV-000001-02`, `PORT-API-01`).
- **Query Parameter**:
  - `as_of_date` (string `YYYY-MM-DD`, optional): Target valuation date. If omitted, the backend defaults to `date.today()`.

#### HTTP Response Codes
- `200 OK`: Successful valuation computation.
- `404 Not Found`: Portfolio ID does not exist in the database (`{"detail": "Portfolio not found: <id>"}`).
- `422 Unprocessable Entity`: Missing market price for one or more instruments on or before the requested date (`{"detail": "Missing market price for instrument <id> on or before <date>"}`).
- `500 Internal Server Error`: Unhandled database or system exception (`{"detail": "An internal error occurred."}`).

#### Response Schema (`PortfolioValuationResult`)
```typescript
interface PositionValuation {
  holding_id: string;
  portfolio_id: string;
  instrument_id: string;
  symbol: string | null;            // e.g. "AAPL", "CSH-USD-MM", null if unassigned
  instrument_name: string | null;   // e.g. "Apple Inc.", "US Dollar Cash", null if unassigned
  asset_class: string;              // "EQUITY" | "FIXED_INCOME" | "CASH" | "COMMODITIES" | string
  quantity: string;                 // High-precision decimal string (e.g. "2500.0000")
  unit_price: string;               // High-precision decimal string (e.g. "180.0000")
  market_value: string;             // High-precision decimal string (e.g. "450000.0000")
  price_date: string | null;        // ISO date "YYYY-MM-DD" of the resolved market price
  price_age_days: number;           // (as_of_date - price_date).days (0 = current)
  is_stale: boolean | null;         // null if no staleness calendar policy is configured; true/false if evaluated
  diagnostic: string | null;        // e.g. "Price as of 2025-02-11 is 338 day(s) old relative to as-of date 2026-01-15"
}

interface AssetClassAllocation {
  asset_class: string;              // e.g. "EQUITY", "CASH", "FIXED_INCOME", "COMMODITIES"
  market_value: string;             // High-precision decimal string (e.g. "750000.0000")
  current_weight: string;           // Actual percentage weight [0, 100], 4 decimal places (e.g. "71.4286")
}

interface PortfolioValuationResult {
  portfolio_id: string;
  as_of_date: string;               // ISO date "YYYY-MM-DD"
  total_market_value: string;       // High-precision decimal string (e.g. "1050000.0000")
  positions: PositionValuation[];
  asset_classes: AssetClassAllocation[];
}
```

#### Realistic Example Payload
```json
{
  "portfolio_id": "PORT-INV-000001-02",
  "as_of_date": "2026-01-15",
  "total_market_value": "436718.2847",
  "positions": [
    {
      "holding_id": "HOLD-PORT-INV-000001-02-INS-000018",
      "portfolio_id": "PORT-INV-000001-02",
      "instrument_id": "INS-000018",
      "symbol": "CSH-USD-MM",
      "instrument_name": "USD Cash Buffer",
      "asset_class": "CASH",
      "quantity": "25200.0000",
      "unit_price": "1.0000",
      "market_value": "25200.0000",
      "price_date": "2025-02-11",
      "price_age_days": 338,
      "is_stale": null,
      "diagnostic": "Price as of 2025-02-11 is 338 day(s) old relative to as-of date 2026-01-15"
    },
    {
      "holding_id": "HOLD-PORT-INV-000001-02-INS-000001",
      "portfolio_id": "PORT-INV-000001-02",
      "instrument_id": "INS-000001",
      "symbol": "AAPL",
      "instrument_name": "Apple Inc.",
      "asset_class": "EQUITY",
      "quantity": "2000.0000",
      "unit_price": "150.0000",
      "market_value": "300000.0000",
      "price_date": "2026-01-15",
      "price_age_days": 0,
      "is_stale": false,
      "diagnostic": null
    }
  ],
  "asset_classes": [
    {
      "asset_class": "CASH",
      "market_value": "25200.0000",
      "current_weight": "5.7703"
    },
    {
      "asset_class": "EQUITY",
      "market_value": "300000.0000",
      "current_weight": "68.6919"
    },
    {
      "asset_class": "FIXED_INCOME",
      "market_value": "111518.2847",
      "current_weight": "25.5378"
    }
  ]
}
```

---

### 2.2 `GET /api/v1/portfolios/{portfolio_id}/drift`

#### Purpose
Calculates percentage and monetary drift between current asset-class weights and effective target allocations as of a target date, and determines whether rebalance triggers have fired under policy corridor constraints.

#### Request Parameters
- **Path Parameter**:
  - `portfolio_id` (string, required): The target portfolio identifier.
- **Query Parameter**:
  - `as_of_date` (string `YYYY-MM-DD`, optional): Target evaluation date. If omitted, defaults to `date.today()`.

#### HTTP Response Codes
- `200 OK`: Successful drift and rebalance trigger calculation.
- `404 Not Found`: Portfolio ID does not exist in the database.
- `422 Unprocessable Entity`: Missing market price data on or before the target date.
- `500 Internal Server Error`: Unhandled system error.

#### Response Schema (`PortfolioDriftResult`)
```typescript
interface AssetClassDrift {
  asset_class: string;              // e.g. "EQUITY", "CASH", "FIXED_INCOME", "COMMODITIES"
  current_market_value: string;     // High-precision decimal string
  target_market_value: string;      // High-precision decimal string: (target_weight / 100) * total_market_value
  current_weight: string;           // Actual percentage weight [0, 100] (e.g. "71.4286")
  target_weight: string;            // Mandated target percentage weight [0, 100] (e.g. "60.0000")
  percentage_drift: string;         // Percentage point difference: current_weight - target_weight (e.g. "+11.4286")
  monetary_drift: string;           // Dollar difference: (percentage_drift / 100) * total_market_value
  action_signal: "BUY" | "SELL" | "HOLD" | null;
}

interface RebalanceTriggerEvaluation {
  status: "TRIGGERED" | "NOT_TRIGGERED" | "NOT_CONFIGURED" | string;
  rebalance_required: boolean | null;
  triggered_asset_classes: string[]; // List of asset class names breaching corridor (e.g. ["EQUITY", "CASH"])
  triggered_positions: string[];     // Specific security identifiers breaching constraints (e.g. ["AAPL"])
  policy_description: string | null; // e.g. "Drift exceeds absolute 5.0% rebalance corridor threshold"
}

interface PortfolioDriftResult {
  portfolio_id: string;
  as_of_date: string;               // ISO date "YYYY-MM-DD"
  total_market_value: string;       // High-precision decimal string
  drifts: AssetClassDrift[];
  rebalance_trigger: RebalanceTriggerEvaluation | null;
}
```

#### Realistic Example Payload
```json
{
  "portfolio_id": "PORT-INV-000001-02",
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

---

## 3. Unsupported Capabilities & Frontend Strategies

### 1. `GET /api/v1/portfolios` (Portfolio Catalog)
- **Status**: **NOT IMPLEMENTED IN BACKEND**.
- **Frontend Architecture**: Provide a well-defined institutional portfolio selector loaded with known seeded portfolios from the database schema (`PORT-INV-000001-01`, `PORT-INV-000001-02`, `PORT-INV-000002-01`, `PORT-INV-000002-02`, `PORT-INV-000003-01`, `PORT-INV-000003-02`, `PORT-API-01`), as well as a custom portfolio ID input that queries live data. If an invalid or unseeded ID is entered, the frontend gracefully handles and displays the actual backend `404 Not Found` response.

### 2. Historical Valuation Time Series (`GET /api/v1/portfolios/{id}/valuation/history`)
- **Status**: **NOT IMPLEMENTED IN BACKEND**.
- **Frontend Architecture**: The UI explicitly displays an institutional banner: *"Historical valuation time series endpoint is not available in backend API. No synthetic timeseries are generated."* This upholds financial integrity and prevents misleading users with fabricated historical returns.

### 3. Revaluation Mutation Endpoint
- **Status**: **READ-ONLY VALUATION**. Valuation is calculated deterministically on every `GET` request.
- **Frontend Architecture**: The "Revalue" button triggers TanStack Query cache invalidation and refetches the live endpoints with the active as-of date.

---

## 4. Financial Calculation & Diagnostic Invariants

1. **Units & Precision**:
   - `total_market_value`, `market_value`, `unit_price`, and `monetary_drift` are high-precision currency values in USD.
   - `current_weight`, `target_weight`, and `percentage_drift` are percentage points ($[0.0000, 100.0000]$).
   - In charts and summaries, percentage-point differences ($\Delta\%$) are strictly labeled as **percentage points (pp)** or **drift %**, not percentage change.
2. **Staleness Diagnostics**:
   - `price_age_days == 0`: Price is current as of valuation date.
   - `price_age_days > 0`: Flagged visually with warning badges indicating exact days old (`{price_age_days}d stale`).
   - If `diagnostic` text is present in the response, it is surfaced directly in tooltips and badges.
3. **Trigger Evaluation**:
   - `status === "TRIGGERED"`: Prominent warning state indicating rebalance corridor threshold breach.
   - `status === "NOT_TRIGGERED"`: Success state confirming asset weights remain within permitted tolerance.
   - `status === "NOT_CONFIGURED"`: Neutral informational state.

