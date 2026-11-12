import { Alert } from '@/components/ui/Alert';
import { Skeleton } from '@/components/ui/Skeleton';
import { usePortfolios } from './hooks/usePortfolios';
import { PortfolioSelector } from './components/PortfolioSelector';
import { PortfolioMetrics } from './components/PortfolioMetrics';
import { AssetAllocationChart } from './components/AssetAllocationChart';
import { TargetAllocationChart } from './components/TargetAllocationChart';
import { DriftAnalysis } from './components/DriftAnalysis';
import { HoldingsTable } from './components/HoldingsTable';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export function PortfoliosPage() {
  const {
    selectedPortfolioId,
    asOfDate,
    setAsOfDate,
    activeReference,
    portfolioReferences,
    valuation,
    drift,
    metrics,
    isLoading,
    isFetching,
    isError,
    error,
    selectPortfolio,
    applyCustomId,
    revalue,
  } = usePortfolios();

  return (
    <div className="space-y-6">
      {/* 1. Interactive Selector & Header Controls */}
      <PortfolioSelector
        selectedPortfolioId={selectedPortfolioId}
        asOfDate={asOfDate}
        isFetching={isFetching}
        activeReference={activeReference}
        portfolioReferences={portfolioReferences}
        onSelectPortfolio={selectPortfolio}
        onSetAsOfDate={setAsOfDate}
        onApplyCustomId={applyCustomId}
        onRevalue={revalue}
      />

      {/* 2. Error Feedback if API fails */}
      {isError && (
        <Alert variant="error" title="Failed to Fetch Portfolio Analytics">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>
                {error?.message ||
                  'An error occurred communicating with the portfolio valuation service.'}
              </span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={revalue}
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Retry Query
            </Button>
          </div>
        </Alert>
      )}

      {/* 3. High-Density Financial Metrics */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="h-24 rounded-lg bg-slate-100 dark:bg-slate-800/50 p-4 border border-slate-200 dark:border-slate-800 space-y-2"
            >
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-6 w-32" />
              <Skeleton className="h-3 w-16" />
            </div>
          ))}
        </div>
      ) : (
        <PortfolioMetrics metrics={metrics} />
      )}

      {/* 4. Interactive Financial Visualizations Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-80 rounded-lg bg-slate-100 dark:bg-slate-800/50 p-6 border border-slate-200 dark:border-slate-800">
            <Skeleton className="h-5 w-40 mb-4" />
            <Skeleton className="h-56 w-full" />
          </div>
          <div className="h-80 rounded-lg bg-slate-100 dark:bg-slate-800/50 p-6 border border-slate-200 dark:border-slate-800">
            <Skeleton className="h-5 w-40 mb-4" />
            <Skeleton className="h-56 w-full" />
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Donut Chart: Asset Allocation Breakdown */}
          <AssetAllocationChart
            assetClasses={valuation?.asset_classes || []}
            totalMarketValue={valuation?.total_market_value || '0.0000'}
          />

          {/* Grouped Bar Chart: Target vs Actual Allocation */}
          <TargetAllocationChart
            drifts={drift?.drifts || []}
            rebalanceTrigger={drift?.rebalance_trigger || undefined}
          />
        </div>
      )}

      {/* 5. Detailed Drift Analysis & Rebalance Trigger Evaluation */}
      {isLoading ? (
        <div className="h-64 rounded-lg bg-slate-100 dark:bg-slate-800/50 p-6 border border-slate-200 dark:border-slate-800">
          <Skeleton className="h-5 w-48 mb-4" />
          <Skeleton className="h-44 w-full" />
        </div>
      ) : (
        <DriftAnalysis driftData={drift} />
      )}

      {/* 6. Holdings Explorer Table with Diagnostics */}
      {isLoading ? (
        <div className="h-72 rounded-lg bg-slate-100 dark:bg-slate-800/50 p-6 border border-slate-200 dark:border-slate-800">
          <Skeleton className="h-5 w-48 mb-4" />
          <Skeleton className="h-52 w-full" />
        </div>
      ) : (
        <HoldingsTable
          positions={valuation?.positions || []}
          totalMarketValue={valuation?.total_market_value || '0.0000'}
        />
      )}
    </div>
  );
}
