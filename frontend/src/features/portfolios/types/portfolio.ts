/**
 * Type definitions for Portfolio Analytics, Valuation, and Drift.
 * Exactly mapped to FastAPI backend Pydantic schemas in app/schemas/portfolio_analytics.py.
 */

export interface PositionValuation {
  holding_id: string;
  portfolio_id: string;
  instrument_id: string;
  symbol: string | null;
  instrument_name: string | null;
  asset_class: string;
  quantity: string;
  unit_price: string;
  market_value: string;
  price_date: string | null;
  price_age_days: number;
  is_stale: boolean | null;
  diagnostic: string | null;
}

export interface AssetClassAllocation {
  asset_class: string;
  market_value: string;
  current_weight: string; // Percentage [0, 100]
}

export interface PortfolioValuationResult {
  portfolio_id: string;
  as_of_date: string; // YYYY-MM-DD
  total_market_value: string;
  positions: PositionValuation[];
  asset_classes: AssetClassAllocation[];
}

export interface AssetClassDrift {
  asset_class: string;
  current_market_value: string;
  target_market_value: string;
  current_weight: string; // [0, 100]
  target_weight: string; // [0, 100]
  percentage_drift: string; // Percentage points (current_weight - target_weight)
  monetary_drift: string; // Dollar drift
  action_signal: 'BUY' | 'SELL' | 'HOLD' | string | null;
}

export interface RebalanceTriggerEvaluation {
  status: 'TRIGGERED' | 'NOT_TRIGGERED' | 'NOT_CONFIGURED' | string;
  rebalance_required: boolean | null;
  triggered_asset_classes: string[];
  triggered_positions: string[];
  policy_description: string | null;
}

export interface PortfolioDriftResult {
  portfolio_id: string;
  as_of_date: string;
  total_market_value: string;
  drifts: AssetClassDrift[];
  rebalance_trigger: RebalanceTriggerEvaluation | null;
}

/**
 * Reference portfolio metadata for known institutional portfolios in the starter dataset.
 * Since GET /api/v1/portfolios catalog is unsupported by the backend, this provides
 * institutional context for standard portfolios while allowing manual custom ID entry.
 */
export interface PortfolioReference {
  portfolio_id: string;
  portfolio_name: string;
  investor_id: string;
  base_currency: string;
  mandate: string;
}

export const SEEDED_PORTFOLIO_REFERENCES: PortfolioReference[] = [
  {
    portfolio_id: 'PORT-INV-000001-02',
    portfolio_name: 'Dakota Meridian Balanced Strategic 2',
    investor_id: 'INV-000001',
    base_currency: 'USD',
    mandate: 'Balanced Strategic Allocation',
  },
  {
    portfolio_id: 'PORT-INV-000001-01',
    portfolio_name: 'Dakota Meridian Balanced Strategic 1 (Legacy)',
    investor_id: 'INV-000001',
    base_currency: 'USD',
    mandate: 'Conservative Rebalance',
  },
  {
    portfolio_id: 'PORT-INV-000002-01',
    portfolio_name: 'Avery Valence Conservative Liquidity 1',
    investor_id: 'INV-000002',
    base_currency: 'USD',
    mandate: 'Capital Preservation',
  },
  {
    portfolio_id: 'PORT-INV-000002-02',
    portfolio_name: 'Avery Valence Capital Preservation 2',
    investor_id: 'INV-000002',
    base_currency: 'USD',
    mandate: 'Income & Liquidity',
  },
  {
    portfolio_id: 'PORT-INV-000003-01',
    portfolio_name: 'Logan Apex Growth & Income 1',
    investor_id: 'INV-000003',
    base_currency: 'USD',
    mandate: 'Aggressive Growth',
  },
  {
    portfolio_id: 'PORT-INV-000003-02',
    portfolio_name: 'Logan Apex Core Multi-Asset 2',
    investor_id: 'INV-000003',
    base_currency: 'USD',
    mandate: 'Core Multi-Asset',
  },
  {
    portfolio_id: 'PORT-API-01',
    portfolio_name: 'Standard Evaluation Portfolio (API Fixture)',
    investor_id: 'INV-API-01',
    base_currency: 'USD',
    mandate: 'Evaluation Multi-Asset',
  },
];

/**
 * Standard colors for asset classes across both themes.
 */
export const ASSET_CLASS_COLORS: Record<string, string> = {
  EQUITY: '#2563EB', // Blue-600
  FIXED_INCOME: '#059669', // Emerald-600
  CASH: '#0284C7', // Sky-600
  COMMODITIES: '#D97706', // Amber-600
  REAL_ESTATE: '#7C3AED', // Violet-600
  UNKNOWN: '#64748B', // Slate-500
};

export interface AssetAllocationChartItem {
  name: string;
  value: number; // Monetary market value
  weight: number; // Current weight %
  color: string;
}

export interface TargetVsActualComparisonItem {
  assetClass: string;
  actualWeight: number;
  targetWeight: number;
  driftPp: number; // Percentage point drift
  actionSignal: string;
}

