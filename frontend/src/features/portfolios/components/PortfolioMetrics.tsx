import { FinancialMetricCard } from '@/components/ui/FinancialMetricCard';
import { formatCurrency, formatPercent } from '@/lib/utils';
import { DollarSign, Wallet, TrendingUp, Layers, AlertTriangle, ShieldCheck } from 'lucide-react';
import type { usePortfolios } from '../hooks/usePortfolios';

interface PortfolioMetricsProps {
  metrics: ReturnType<typeof usePortfolios>['metrics'];
}

export function PortfolioMetrics({ metrics }: PortfolioMetricsProps) {
  if (!metrics) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-24 rounded-lg bg-slate-100 dark:bg-slate-800/50 animate-pulse border border-slate-200 dark:border-slate-800" />
        ))}
      </div>
    );
  }

  const investedWeight = metrics.totalMarketValue > 0
    ? ((metrics.investedMarketValue / metrics.totalMarketValue) * 100)
    : 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {/* 1. Total Portfolio Market Value */}
      <FinancialMetricCard
        title="Total Market Value"
        value={formatCurrency(metrics.totalMarketValue)}
        badgeText={`As-of ${metrics.asOfDate}`}
        badgeVariant="brand"
        subtitle={`${metrics.assetClassCount} Asset Classes`}
        icon={<DollarSign className="w-4 h-4 text-brand-600 dark:text-brand-400" />}
        accentBorder="brand"
      />

      {/* 2. Cash Buffer & Solvency */}
      <FinancialMetricCard
        title="Available Cash Buffer"
        value={formatCurrency(metrics.cashMarketValue)}
        badgeText={`${formatPercent(metrics.cashWeight)} Weight`}
        badgeVariant={metrics.cashWeight >= 5.0 ? 'success' : 'warning'}
        subtitle={metrics.cashWeight >= 5.0 ? 'Solvent Cash Reserve' : 'Low Cash Buffer (<5%)'}
        icon={<Wallet className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />}
        accentBorder={metrics.cashWeight >= 5.0 ? 'success' : 'warning'}
      />

      {/* 3. Invested Capital */}
      <FinancialMetricCard
        title="Invested Portfolio Value"
        value={formatCurrency(metrics.investedMarketValue)}
        badgeText={`${formatPercent(investedWeight)} Invested`}
        badgeVariant="neutral"
        subtitle="Non-cash asset holdings"
        icon={<TrendingUp className="w-4 h-4 text-slate-600 dark:text-slate-400" />}
        accentBorder="neutral"
      />

      {/* 4. Maximum Asset Drift */}
      <FinancialMetricCard
        title="Max Absolute Drift"
        value={metrics.maxDriftAssetClass ? `${metrics.maxDriftPp.toFixed(2)} pp` : '0.00 pp'}
        badgeText={metrics.isTriggered ? 'CORRIDOR TRIGGERED' : 'WITHIN TOLERANCE'}
        badgeVariant={metrics.isTriggered ? 'warning' : 'success'}
        subtitle={metrics.maxDriftAssetClass ? `${metrics.maxDriftAssetClass} Drift` : 'No Active Drift'}
        icon={
          metrics.isTriggered ? (
            <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          ) : (
            <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          )
        }
        accentBorder={metrics.isTriggered ? 'warning' : 'success'}
      />

      {/* 5. Total Holdings Count */}
      <FinancialMetricCard
        title="Portfolio Holdings"
        value={`${metrics.positionCount} Positions`}
        badgeText={
          metrics.stalePositionsCount > 0
            ? `${metrics.stalePositionsCount} Stale Price(s)`
            : 'All Prices Fresh'
        }
        badgeVariant={metrics.stalePositionsCount > 0 ? 'warning' : 'success'}
        subtitle="Individual instrument lots"
        icon={<Layers className="w-4 h-4 text-slate-600 dark:text-slate-400" />}
        accentBorder={metrics.stalePositionsCount > 0 ? 'warning' : 'neutral'}
      />
    </div>
  );
}

