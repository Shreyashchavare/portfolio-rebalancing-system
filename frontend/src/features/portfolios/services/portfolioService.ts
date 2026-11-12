import { apiRequest } from '@/services/api/client';
import { API_ENDPOINTS } from '@/services/api/endpoints';
import type {
  PortfolioValuationResult,
  PortfolioDriftResult,
  AssetAllocationChartItem,
  TargetVsActualComparisonItem,
  PortfolioReference,
} from '../types/portfolio';
import { ASSET_CLASS_COLORS } from '../types/portfolio';

export const portfolioService = {
  /**
   * Fetch all registered portfolios from the backend.
   * Calls GET /api/v1/portfolios
   */
  async listPortfolios(): Promise<PortfolioReference[]> {
    return apiRequest<PortfolioReference[]>({
      method: 'GET',
      url: API_ENDPOINTS.PORTFOLIOS,
    });
  },

  /**
   * Fetch portfolio valuation and holding positions as of a target date.
   * Calls GET /api/v1/portfolios/{portfolio_id}/valuation
   */
  async getValuation(portfolioId: string, asOfDate?: string): Promise<PortfolioValuationResult> {
    const params = asOfDate ? { as_of_date: asOfDate } : undefined;
    return apiRequest<PortfolioValuationResult>({
      method: 'GET',
      url: API_ENDPOINTS.PORTFOLIO_VALUATION(encodeURIComponent(portfolioId)),
      params,
    });
  },

  /**
   * Fetch portfolio allocation drift and rebalance trigger evaluations.
   * Calls GET /api/v1/portfolios/{portfolio_id}/drift
   */
  async getDrift(portfolioId: string, asOfDate?: string): Promise<PortfolioDriftResult> {
    const params = asOfDate ? { as_of_date: asOfDate } : undefined;
    return apiRequest<PortfolioDriftResult>({
      method: 'GET',
      url: API_ENDPOINTS.PORTFOLIO_DRIFT(encodeURIComponent(portfolioId)),
      params,
    });
  },

  /**
   * Transform backend AssetClassAllocation into chart items for Recharts Pie/Donut.
   */
  formatAllocationChartData(allocations: PortfolioValuationResult['asset_classes']): AssetAllocationChartItem[] {
    return allocations.map((item) => {
      const val = parseFloat(item.market_value) || 0;
      const weight = parseFloat(item.current_weight) || 0;
      return {
        name: item.asset_class,
        value: val,
        weight: weight,
        color: ASSET_CLASS_COLORS[item.asset_class] || '#64748B',
      };
    });
  },

  /**
   * Transform backend AssetClassDrift into chart items for Target vs Actual comparison.
   */
  formatTargetComparisonData(drifts: PortfolioDriftResult['drifts']): TargetVsActualComparisonItem[] {
    return drifts.map((item) => ({
      assetClass: item.asset_class,
      actualWeight: parseFloat(item.current_weight) || 0,
      targetWeight: parseFloat(item.target_weight) || 0,
      driftPp: parseFloat(item.percentage_drift) || 0,
      actionSignal: item.action_signal || 'HOLD',
    }));
  },

  /**
   * Derive high-level dashboard metrics from valuation and drift results.
   */
  deriveMetrics(valuation?: PortfolioValuationResult, drift?: PortfolioDriftResult) {
    if (!valuation) {
      return null;
    }

    const totalVal = parseFloat(valuation.total_market_value) || 0;
    const cashAllocation = valuation.asset_classes.find((a) => a.asset_class === 'CASH');
    const cashVal = cashAllocation ? parseFloat(cashAllocation.market_value) || 0 : 0;
    const cashWeight = cashAllocation ? parseFloat(cashAllocation.current_weight) || 0 : 0;
    const investedVal = Math.max(0, totalVal - cashVal);
    const positionCount = valuation.positions.length;

    let maxDriftPp = 0;
    let maxDriftAssetClass = '';
    if (drift && drift.drifts.length > 0) {
      for (const d of drift.drifts) {
        const absD = Math.abs(parseFloat(d.percentage_drift) || 0);
        if (absD > maxDriftPp) {
          maxDriftPp = absD;
          maxDriftAssetClass = d.asset_class;
        }
      }
    }

    const isTriggered = drift?.rebalance_trigger?.status === 'TRIGGERED';
    const stalePositionsCount = valuation.positions.filter((p) => p.price_age_days > 0).length;

    return {
      totalMarketValue: totalVal,
      cashMarketValue: cashVal,
      cashWeight,
      investedMarketValue: investedVal,
      positionCount,
      assetClassCount: valuation.asset_classes.length,
      maxDriftPp,
      maxDriftAssetClass,
      isTriggered,
      triggerEvaluation: drift?.rebalance_trigger,
      stalePositionsCount,
      asOfDate: valuation.as_of_date,
    };
  },
};
