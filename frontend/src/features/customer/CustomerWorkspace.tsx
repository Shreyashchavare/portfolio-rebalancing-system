import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { usePortfolioValuation } from '@/features/portfolios/hooks/usePortfolioValuation';
import { usePortfolioDrift } from '@/features/portfolios/hooks/usePortfolioDrift';
import { AssetAllocationChart } from '@/features/portfolios/components/AssetAllocationChart';
import { TargetAllocationChart } from '@/features/portfolios/components/TargetAllocationChart';
import { HoldingsTable } from '@/features/portfolios/components/HoldingsTable';
import { ProposalAuditHistory } from '@/components/business/ProposalAuditHistory';
import { BusinessWorkflowLifecycle } from '@/components/business/BusinessWorkflowLifecycle';
import {
  Briefcase,
  PieChart,
  Scale,
  History,
  TrendingDown,
  DollarSign,
  ShieldCheck,
  AlertTriangle,
} from 'lucide-react';

const DEFAULT_AS_OF_DATE = '2026-01-15';

export function CustomerWorkspace() {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlTab = searchParams.get('tab') as 'overview' | 'portfolio' | 'recommendations' | 'activity' | null;
  const [activeTab, setActiveTabState] = useState<'overview' | 'portfolio' | 'recommendations' | 'activity'>(
    urlTab || 'overview'
  );

  useEffect(() => {
    if (urlTab) {
      setActiveTabState(urlTab);
    }
  }, [urlTab]);

  const setActiveTab = (tab: 'overview' | 'portfolio' | 'recommendations' | 'activity') => {
    setActiveTabState(tab);
    setSearchParams({ tab });
  };

  const portfolioId = 'PORT-INV-000001-02';

  const { data: valuation, isLoading: isValLoading } = usePortfolioValuation(portfolioId, DEFAULT_AS_OF_DATE);
  const { data: drift } = usePortfolioDrift(portfolioId, DEFAULT_AS_OF_DATE);

  const totalValue = parseFloat(valuation?.total_market_value || '0');
  const hasDriftAlert = drift?.rebalance_trigger?.status === 'TRIGGERED' || drift?.rebalance_trigger?.rebalance_required === true;
  const triggeredClass = drift?.rebalance_trigger?.triggered_asset_classes?.[0] || 'Asset Classes';

  return (
    <div className="space-y-6">
      {/* Customer Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Customer Account Portal
            </h2>
            <Badge variant="brand" size="sm">
              PORTFOLIO HOLDER
            </Badge>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Personal wealth account &bull; Account Reference: <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">{portfolioId}</span>
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <Badge variant="neutral" size="sm" className="font-mono">
            READ-ONLY VIEW
          </Badge>
          <span className="text-slate-400">&bull;</span>
          <span className="text-slate-500 dark:text-slate-400">Institutional Fiduciary Custody</span>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div role="tablist" aria-label="Customer Navigation" className="flex items-center gap-1.5 border-b border-slate-200 dark:border-slate-800 overflow-x-auto pb-px">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'overview'}
          onClick={() => setActiveTab('overview')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'overview'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <PieChart className="w-3.5 h-3.5" />
          <span>Overview</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'portfolio'}
          onClick={() => setActiveTab('portfolio')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'portfolio'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <Briefcase className="w-3.5 h-3.5" />
          <span>My Portfolio</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'recommendations'}
          onClick={() => setActiveTab('recommendations')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'recommendations'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <Scale className="w-3.5 h-3.5" />
          <span>Recommendations</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'activity'}
          onClick={() => setActiveTab('activity')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'activity'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <History className="w-3.5 h-3.5" />
          <span>Activity</span>
        </button>
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Key Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-500 dark:text-slate-400">Total Portfolio Value</span>
                  <DollarSign className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                </div>
                <div className="text-xl font-mono font-bold text-slate-900 dark:text-slate-100">
                  {isValLoading ? '...' : `$${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                </div>
                <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 block">
                  As of date: {valuation?.as_of_date || 'Current'}
                </span>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-500 dark:text-slate-400">Allocation Corridor Health</span>
                  <TrendingDown className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={hasDriftAlert ? 'warning' : 'success'}>
                    {hasDriftAlert ? 'REBALANCE RECOMMENDED' : 'WITHIN TOLERANCE'}
                  </Badge>
                </div>
                <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 block">
                  Status: {drift?.rebalance_trigger?.status || 'NORMAL'}
                </span>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-500 dark:text-slate-400">Governance Protection</span>
                  <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                  Dual-Key Sign-off Enforced
                </div>
                <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 block">
                  No automated execution without review
                </span>
              </CardContent>
            </Card>
          </div>

          {/* Allocation Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <AssetAllocationChart
              assetClasses={valuation?.asset_classes || []}
              totalMarketValue={valuation?.total_market_value || '0'}
            />
            <TargetAllocationChart
              drifts={drift?.drifts || []}
              rebalanceTrigger={drift?.rebalance_trigger}
            />
          </div>
        </div>
      )}

      {/* Tab 2: My Portfolio */}
      {activeTab === 'portfolio' && (
        <div className="space-y-6">
          <HoldingsTable
            positions={valuation?.positions || []}
            totalMarketValue={valuation?.total_market_value || '0'}
          />
        </div>
      )}

      {/* Tab 3: Recommendations */}
      {activeTab === 'recommendations' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Advisor Recommendation Summary</CardTitle>
              <CardDescription className="text-xs">
                Proposed adjustments prepared by portfolio operations based on your Investment Policy Statement (IPS).
              </CardDescription>
            </CardHeader>
            <CardContent>
              {hasDriftAlert ? (
                <div className="p-4 rounded-xl border border-amber-200 dark:border-amber-900/60 bg-amber-50/70 dark:bg-amber-950/30 text-xs text-amber-950 dark:text-amber-200 space-y-2">
                  <div className="flex items-center gap-2 font-bold">
                    <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                    <span>Portfolio Drift Trigger Detected ({triggeredClass})</span>
                  </div>
                  <p className="text-[11px] leading-relaxed">
                    Your portfolio allocation has drifted beyond the policy tolerance band. An operations analyst has staged rebalancing orders to restore your asset class weights to their benchmark targets.
                  </p>
                  <div className="pt-2 text-[11px] text-slate-500 dark:text-slate-400">
                    Proposed trades require fiduciary compliance approval before execution. You do not need to take any action.
                  </div>
                </div>
              ) : (
                <div className="py-8 text-center text-xs text-slate-500 dark:text-slate-400">
                  Your portfolio is currently aligned with your target allocations. No rebalancing is needed.
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 4: Activity */}
      {activeTab === 'activity' && (
        <div className="space-y-6">
          <BusinessWorkflowLifecycle
            currentStage={hasDriftAlert ? 'drift_calculated' : 'holdings_evaluated'}
            portfolioId={portfolioId}
          />
          <ProposalAuditHistory proposalId="RB-2026-000002" />
        </div>
      )}
    </div>
  );
}
