import { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { usePortfolioValuation } from '@/features/portfolios/hooks/usePortfolioValuation';
import { usePortfolioDrift } from '@/features/portfolios/hooks/usePortfolioDrift';
import { AssetAllocationChart } from '@/features/portfolios/components/AssetAllocationChart';
import { TargetAllocationChart } from '@/features/portfolios/components/TargetAllocationChart';
import { HoldingsTable } from '@/features/portfolios/components/HoldingsTable';
import { ProposalAuditHistory } from '@/components/business/ProposalAuditHistory';
import { BusinessWorkflowLifecycle, type WorkflowStage } from '@/components/business/BusinessWorkflowLifecycle';
import { SEEDED_PORTFOLIO_REFERENCES } from '@/features/portfolios/types/portfolio';
import { useProposals } from '@/hooks/useApprovals';
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

  const [portfolioId, setPortfolioId] = useState<string>('PORT-INV-000001-02');
  const activeRef = SEEDED_PORTFOLIO_REFERENCES.find((r) => r.portfolio_id === portfolioId);

  const { data: valuation, isLoading: isValLoading } = usePortfolioValuation(portfolioId, DEFAULT_AS_OF_DATE);
  const { data: drift } = usePortfolioDrift(portfolioId, DEFAULT_AS_OF_DATE);
  const { data: proposals } = useProposals({ portfolio_id: portfolioId });

  const latestProposal = proposals?.[0];
  const proposalId = latestProposal?.proposal_id || 'RB-2026-000002';

  const totalValue = parseFloat(valuation?.total_market_value || '0');
  const hasDriftAlert = drift?.rebalance_trigger?.status === 'TRIGGERED' || drift?.rebalance_trigger?.rebalance_required === true;
  const triggeredClass = drift?.rebalance_trigger?.triggered_asset_classes?.[0] || 'Asset Classes';

  const currentWorkflowStage = useMemo<WorkflowStage>(() => {
    if (!latestProposal) {
      return hasDriftAlert ? 'drift_calculated' : 'holdings_evaluated';
    }
    if (latestProposal.status === 'APPROVED') {
      return 'audit_logged';
    }
    if (latestProposal.status === 'REJECTED') {
      return 'decision_rendered';
    }
    if (latestProposal.status === 'PENDING_REVIEW') {
      return 'decision_rendered';
    }
    return 'recommendation_generated';
  }, [latestProposal, hasDriftAlert]);

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
            Personal wealth account &bull; Investor:{' '}
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              {activeRef ? activeRef.portfolio_name.split(' ').slice(0, 2).join(' ') : 'Account Holder'}
            </span>{' '}
            (<span className="font-mono">{activeRef?.investor_id || 'INV-000001'}</span>) &bull; Reference:{' '}
            <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">{portfolioId}</span>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 shadow-sm">
            <label htmlFor="customer-account-select" className="text-xs text-slate-500 dark:text-slate-400 font-medium">
              Profile:
            </label>
            <select
              id="customer-account-select"
              aria-label="Select Customer Account"
              value={portfolioId}
              onChange={(e) => setPortfolioId(e.target.value)}
              className="bg-transparent text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none cursor-pointer"
            >
              {SEEDED_PORTFOLIO_REFERENCES.map((ref) => (
                <option key={ref.portfolio_id} value={ref.portfolio_id} className="dark:bg-slate-900 text-slate-900 dark:text-slate-100">
                  {ref.investor_id}: {ref.portfolio_name.split(' ').slice(0, 2).join(' ')} ({ref.portfolio_id})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <Badge variant="neutral" size="sm" className="font-mono">
              READ-ONLY VIEW
            </Badge>
            <span className="text-slate-400 hidden sm:inline">&bull;</span>
            <span className="text-slate-500 dark:text-slate-400 hidden sm:inline">Institutional Fiduciary Custody</span>
          </div>
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
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-sm">Advisor Recommendation Summary</CardTitle>
                  <CardDescription className="text-xs">
                    Proposed adjustments prepared by portfolio operations based on your Investment Policy Statement (IPS).
                  </CardDescription>
                </div>
                {latestProposal && (
                  <Badge
                    variant={
                      latestProposal.status === 'APPROVED'
                        ? 'success'
                        : latestProposal.status === 'REJECTED'
                        ? 'danger'
                        : 'warning'
                    }
                    size="sm"
                  >
                    {latestProposal.status}
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
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
                <div className="py-4 text-center text-xs text-slate-500 dark:text-slate-400">
                  Your portfolio is currently aligned with your target allocations. No urgent rebalancing is needed.
                </div>
              )}

              {/* Staged Recommended Trades Table */}
              {latestProposal && latestProposal.trades && latestProposal.trades.length > 0 ? (
                <div className="space-y-2.5 pt-2 border-t border-slate-200 dark:border-slate-800">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                      Staged Trade Orders &mdash; Reference <span className="font-mono">{latestProposal.proposal_id}</span>
                    </h4>
                    <span className="text-[11px] text-slate-500">
                      {latestProposal.trades.length} {latestProposal.trades.length === 1 ? 'Order' : 'Orders'}
                    </span>
                  </div>

                  <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 font-semibold border-b border-slate-200 dark:border-slate-800">
                        <tr>
                          <th className="px-3 py-2">Security</th>
                          <th className="px-3 py-2">Class</th>
                          <th className="px-3 py-2">Action</th>
                          <th className="px-3 py-2 text-right">Quantity</th>
                          <th className="px-3 py-2 text-right">Unit Price</th>
                          <th className="px-3 py-2 text-right">Estimated Value</th>
                          <th className="px-3 py-2 text-right">Est. Fee</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {latestProposal.trades.map((t) => (
                          <tr key={t.trade_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                            <td className="px-3 py-2">
                              <span className="font-semibold text-slate-900 dark:text-slate-100">{t.symbol || t.instrument_id}</span>
                              <span className="text-[10px] text-slate-500 block truncate max-w-[200px]">{t.instrument_name}</span>
                            </td>
                            <td className="px-3 py-2">
                              <Badge variant="neutral" size="sm">{t.asset_class}</Badge>
                            </td>
                            <td className="px-3 py-2">
                              <Badge variant={t.trade_side === 'BUY' ? 'success' : 'danger'} size="sm">
                                {t.trade_side}
                              </Badge>
                            </td>
                            <td className="px-3 py-2 text-right font-mono">{parseFloat(t.quantity).toLocaleString()}</td>
                            <td className="px-3 py-2 text-right font-mono">${parseFloat(t.unit_price).toFixed(2)}</td>
                            <td className="px-3 py-2 text-right font-mono font-medium">${parseFloat(t.trade_value).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                            <td className="px-3 py-2 text-right font-mono text-slate-500">${parseFloat(t.fee_amount).toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="py-4 text-center text-xs text-slate-500 dark:text-slate-400">
                  No individual trade orders currently staged for this account.
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
            currentStage={currentWorkflowStage}
            proposalStatus={latestProposal?.status ?? null}
            portfolioId={portfolioId}
            proposalId={proposalId}
          />
          <ProposalAuditHistory proposalId={proposalId} />
        </div>
      )}
    </div>
  );
}
