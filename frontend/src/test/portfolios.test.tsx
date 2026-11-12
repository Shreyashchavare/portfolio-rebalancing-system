import { describe, it, expect, beforeEach, vi } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { PortfoliosPage } from '@/features/portfolios/PortfoliosPage';
import { portfolioService } from '@/features/portfolios/services/portfolioService';
import { apiClient } from '@/services/api/client';
import type {
  PortfolioValuationResult,
  PortfolioDriftResult,
} from '@/features/portfolios/types/portfolio';
import { ApiError } from '@/types/api';

const MOCK_VALUATION: PortfolioValuationResult = {
  portfolio_id: 'PORT-INV-000001-02',
  as_of_date: '2026-01-15',
  total_market_value: '436718.2847',
  positions: [
    {
      holding_id: 'HOLD-PORT-INV-000001-02-INS-000018',
      portfolio_id: 'PORT-INV-000001-02',
      instrument_id: 'INS-000018',
      symbol: 'CSH-USD-MM',
      instrument_name: 'USD Cash Buffer',
      asset_class: 'CASH',
      quantity: '25200.0000',
      unit_price: '1.0000',
      market_value: '25200.0000',
      price_date: '2025-02-11',
      price_age_days: 338,
      is_stale: null,
      diagnostic: 'Price as of 2025-02-11 is 338 day(s) old relative to as-of date 2026-01-15',
    },
    {
      holding_id: 'HOLD-PORT-INV-000001-02-INS-000001',
      portfolio_id: 'PORT-INV-000001-02',
      instrument_id: 'INS-000001',
      symbol: 'AAPL',
      instrument_name: 'Apple Inc.',
      asset_class: 'EQUITY',
      quantity: '2000.0000',
      unit_price: '150.0000',
      market_value: '300000.0000',
      price_date: '2026-01-15',
      price_age_days: 0,
      is_stale: false,
      diagnostic: null,
    },
    {
      holding_id: 'HOLD-PORT-INV-000001-02-INS-000005',
      portfolio_id: 'PORT-INV-000001-02',
      instrument_id: 'INS-000005',
      symbol: null, // Test null symbol handling
      instrument_name: null, // Test null name handling
      asset_class: 'FIXED_INCOME',
      quantity: '1000.0000',
      unit_price: '111.5183',
      market_value: '111518.2847',
      price_date: '2026-01-15',
      price_age_days: 0,
      is_stale: false,
      diagnostic: null,
    },
  ],
  asset_classes: [
    {
      asset_class: 'CASH',
      market_value: '25200.0000',
      current_weight: '5.7703',
    },
    {
      asset_class: 'EQUITY',
      market_value: '300000.0000',
      current_weight: '68.6919',
    },
    {
      asset_class: 'FIXED_INCOME',
      market_value: '111518.2847',
      current_weight: '25.5378',
    },
  ],
};

const MOCK_DRIFT: PortfolioDriftResult = {
  portfolio_id: 'PORT-INV-000001-02',
  as_of_date: '2026-01-15',
  total_market_value: '436718.2847',
  drifts: [
    {
      asset_class: 'EQUITY',
      current_market_value: '300000.0000',
      target_market_value: '262030.9708',
      current_weight: '68.6919',
      target_weight: '60.0000',
      percentage_drift: '8.6919',
      monetary_drift: '37969.0292',
      action_signal: 'SELL',
    },
    {
      asset_class: 'CASH',
      current_market_value: '25200.0000',
      target_market_value: '43671.8285',
      current_weight: '5.7703',
      target_weight: '10.0000',
      percentage_drift: '-4.2297',
      monetary_drift: '-18471.8285',
      action_signal: 'BUY',
    },
    {
      asset_class: 'FIXED_INCOME',
      current_market_value: '111518.2847',
      target_market_value: '131015.4854',
      current_weight: '25.5378',
      target_weight: '30.0000',
      percentage_drift: '-4.4622',
      monetary_drift: '-19497.2007',
      action_signal: 'BUY',
    },
  ],
  rebalance_trigger: {
    status: 'TRIGGERED',
    rebalance_required: true,
    triggered_asset_classes: ['EQUITY'],
    triggered_positions: [],
    policy_description: 'Drift exceeds absolute 5.0% rebalance corridor threshold',
  },
};

describe('Portfolio Analytics & Valuation Experience (Phase 8.3)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  // 1. Service Layer Tests
  describe('portfolioService API mapping and transformations', () => {
    it('calls GET /api/v1/portfolios/{id}/valuation with correct parameters', async () => {
      const spy = vi.spyOn(apiClient, 'request').mockResolvedValueOnce({
        data: MOCK_VALUATION,
      });

      const res = await portfolioService.getValuation('PORT-INV-000001-02', '2026-01-15');
      expect(res.portfolio_id).toBe('PORT-INV-000001-02');
      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({
          method: 'GET',
          url: '/api/v1/portfolios/PORT-INV-000001-02/valuation',
          params: { as_of_date: '2026-01-15' },
        })
      );
    });

    it('calls GET /api/v1/portfolios/{id}/drift with correct parameters', async () => {
      const spy = vi.spyOn(apiClient, 'request').mockResolvedValueOnce({
        data: MOCK_DRIFT,
      });

      const res = await portfolioService.getDrift('PORT-INV-000001-02', '2026-01-15');
      expect(res.portfolio_id).toBe('PORT-INV-000001-02');
      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({
          method: 'GET',
          url: '/api/v1/portfolios/PORT-INV-000001-02/drift',
          params: { as_of_date: '2026-01-15' },
        })
      );
    });

    it('formats allocation data for donut charts correctly', () => {
      const chartData = portfolioService.formatAllocationChartData(MOCK_VALUATION.asset_classes);
      expect(chartData).toHaveLength(3);
      expect(chartData[0]?.name).toBe('CASH');
      expect(chartData[0]?.value).toBe(25200);
      expect(chartData[0]?.weight).toBe(5.7703);
    });

    it('formats target comparison data correctly', () => {
      const targetData = portfolioService.formatTargetComparisonData(MOCK_DRIFT.drifts);
      expect(targetData).toHaveLength(3);
      expect(targetData[0]?.assetClass).toBe('EQUITY');
      expect(targetData[0]?.actualWeight).toBe(68.6919);
      expect(targetData[0]?.targetWeight).toBe(60);
      expect(targetData[0]?.driftPp).toBe(8.6919);
      expect(targetData[0]?.actionSignal).toBe('SELL');
    });

    it('derives accurate high-level dashboard metrics', () => {
      const metrics = portfolioService.deriveMetrics(MOCK_VALUATION, MOCK_DRIFT);
      expect(metrics).not.toBeNull();
      expect(metrics?.totalMarketValue).toBeCloseTo(436718.2847, 2);
      expect(metrics?.cashMarketValue).toBe(25200);
      expect(metrics?.cashWeight).toBe(5.7703);
      expect(metrics?.positionCount).toBe(3);
      expect(metrics?.isTriggered).toBe(true);
      expect(metrics?.stalePositionsCount).toBe(1);
    });
  });

  // 2. Component Integration & Rendering Tests
  describe('PortfoliosPage Component Rendering', () => {
    it('renders the portfolio workspace with active portfolio selector and header controls', async () => {
      vi.spyOn(portfolioService, 'getValuation').mockResolvedValue(MOCK_VALUATION);
      vi.spyOn(portfolioService, 'getDrift').mockResolvedValue(MOCK_DRIFT);

      renderWithProviders(<PortfoliosPage />);

      expect(
        screen.getByRole('heading', { level: 2, name: /Portfolio Management/i })
      ).toBeInTheDocument();
      expect(screen.getByText('LIVE FASTAPI VALUATION')).toBeInTheDocument();
      expect(screen.getByLabelText(/Select Target Portfolio/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Valuation As-Of Date/i)).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Revalue/i })).toBeInTheDocument();
      });
    });

    it('renders financial metric summary cards with verified values', async () => {
      vi.spyOn(portfolioService, 'getValuation').mockResolvedValue(MOCK_VALUATION);
      vi.spyOn(portfolioService, 'getDrift').mockResolvedValue(MOCK_DRIFT);

      renderWithProviders(<PortfoliosPage />);

      await waitFor(() => {
        expect(screen.getAllByText('$436,718.28').length).toBeGreaterThan(0);
      });

      expect(screen.getAllByText('$25,200.00').length).toBeGreaterThan(0);
      expect(screen.getByText('3 Positions')).toBeInTheDocument();
      expect(screen.getByText('1 Stale Price(s)')).toBeInTheDocument();
      expect(screen.getByText('CORRIDOR TRIGGERED')).toBeInTheDocument();
    });

    it('renders the holdings table with security details, asset class badges, and staleness diagnostics', async () => {
      vi.spyOn(portfolioService, 'getValuation').mockResolvedValue(MOCK_VALUATION);
      vi.spyOn(portfolioService, 'getDrift').mockResolvedValue(MOCK_DRIFT);

      renderWithProviders(<PortfoliosPage />);

      await waitFor(() => {
        expect(screen.getByText('AAPL')).toBeInTheDocument();
      });

      expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
      expect(screen.getByText('CSH-USD-MM')).toBeInTheDocument();
      expect(screen.getByText('338d STALE')).toBeInTheDocument();

      // Verify null symbol fallback renders instrument_id
      expect(screen.getAllByText('INS-000005').length).toBeGreaterThan(0);
    });

    it('filters holdings dynamically via search input and asset-class dropdown', async () => {
      vi.spyOn(portfolioService, 'getValuation').mockResolvedValue(MOCK_VALUATION);
      vi.spyOn(portfolioService, 'getDrift').mockResolvedValue(MOCK_DRIFT);

      renderWithProviders(<PortfoliosPage />);

      await waitFor(() => {
        expect(screen.getByText('AAPL')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText(/Search symbol, name.../i);
      fireEvent.change(searchInput, { target: { value: 'Apple' } });

      expect(screen.getByText('AAPL')).toBeInTheDocument();
      expect(screen.queryByText('CSH-USD-MM')).not.toBeInTheDocument();

      fireEvent.change(searchInput, { target: { value: '' } });
      const filterSelect = screen.getByLabelText(/Filter by Asset Class/i);
      fireEvent.change(filterSelect, { target: { value: 'CASH' } });

      expect(screen.getByText('CSH-USD-MM')).toBeInTheDocument();
      expect(screen.queryByText('AAPL')).not.toBeInTheDocument();
    });

    it('renders drift analysis table with percentage point differences and rebalance alert', async () => {
      vi.spyOn(portfolioService, 'getValuation').mockResolvedValue(MOCK_VALUATION);
      vi.spyOn(portfolioService, 'getDrift').mockResolvedValue(MOCK_DRIFT);

      renderWithProviders(<PortfoliosPage />);

      await waitFor(() => {
        expect(screen.getByText('Asset Class Allocation Drift Analysis')).toBeInTheDocument();
      });

      expect(screen.getByText('Rebalance Corridor Triggered')).toBeInTheDocument();
      expect(
        screen.getByText(/Drift exceeds absolute 5.0% rebalance corridor threshold/i)
      ).toBeInTheDocument();
      expect(screen.getAllByText('+8.69 pp').length).toBeGreaterThan(0);
      expect(screen.getAllByText('-4.23 pp').length).toBeGreaterThan(0);
      expect(screen.getAllByText('-4.46 pp').length).toBeGreaterThan(0);
      expect(screen.getAllByText('SELL').length).toBeGreaterThan(0);
      expect(screen.getAllByText('BUY').length).toBeGreaterThan(0);
    });

    it('handles empty API responses gracefully without crashing', async () => {
      const emptyValuation: PortfolioValuationResult = {
        portfolio_id: 'PORT-EMPTY',
        as_of_date: '2026-01-15',
        total_market_value: '0.0000',
        positions: [],
        asset_classes: [],
      };
      const emptyDrift: PortfolioDriftResult = {
        portfolio_id: 'PORT-EMPTY',
        as_of_date: '2026-01-15',
        total_market_value: '0.0000',
        drifts: [],
        rebalance_trigger: null,
      };

      vi.spyOn(portfolioService, 'getValuation').mockResolvedValue(emptyValuation);
      vi.spyOn(portfolioService, 'getDrift').mockResolvedValue(emptyDrift);

      renderWithProviders(<PortfoliosPage />);

      await waitFor(() => {
        expect(
          screen.getByText(/No active asset class allocations recorded/i)
        ).toBeInTheDocument();
      });

      expect(
        screen.getByText(/No active holdings positions found for this portfolio/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/No drift metrics available for this portfolio/i)
      ).toBeInTheDocument();
    });

    it('displays error feedback when API returns 404 or network error', async () => {
      vi.spyOn(portfolioService, 'getValuation').mockRejectedValue(
        new ApiError({
          message: 'Portfolio not found: PORT-NONEXISTENT',
          status: 404,
        })
      );
      vi.spyOn(portfolioService, 'getDrift').mockRejectedValue(
        new ApiError({
          message: 'Portfolio not found: PORT-NONEXISTENT',
          status: 404,
        })
      );

      renderWithProviders(<PortfoliosPage />);

      await waitFor(() => {
        expect(
          screen.getByText(/Failed to Fetch Portfolio Analytics/i)
        ).toBeInTheDocument();
      });

      expect(
        screen.getByText(/Portfolio not found: PORT-NONEXISTENT/i)
      ).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Retry Query/i })).toBeInTheDocument();
    });

    it('renders point-in-time portfolio analytics cleanly without synthetic time series data', async () => {
      vi.spyOn(portfolioService, 'getValuation').mockResolvedValue(MOCK_VALUATION);
      vi.spyOn(portfolioService, 'getDrift').mockResolvedValue(MOCK_DRIFT);

      renderWithProviders(<PortfoliosPage />);

      await waitFor(() => {
        expect(
          screen.getByText(/Position Breakdown & Valuation Diagnostics/i)
        ).toBeInTheDocument();
      });
      // Verifies no unsupported time-series placeholder is rendered
      expect(
        screen.queryByText('Historical Valuation Time Series')
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText(/Historical Valuation Series Endpoint Unavailable/i)
      ).not.toBeInTheDocument();
    });
  });
});
