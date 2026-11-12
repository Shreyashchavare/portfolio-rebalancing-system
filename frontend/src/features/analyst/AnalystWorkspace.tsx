import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { usePortfolioValuation } from '@/features/portfolios/hooks/usePortfolioValuation';
import { usePortfolioDrift } from '@/features/portfolios/hooks/usePortfolioDrift';
import { useCreateProposal } from '@/hooks/useRebalancing';
import { AssetAllocationChart } from '@/features/portfolios/components/AssetAllocationChart';
import { TargetAllocationChart } from '@/features/portfolios/components/TargetAllocationChart';
import { HoldingsTable } from '@/features/portfolios/components/HoldingsTable';
import { DriftAnalysis } from '@/features/portfolios/components/DriftAnalysis';
import { ProposalDetailsCard } from '@/components/business/ProposalDetailsCard';
import { BusinessWorkflowLifecycle } from '@/components/business/BusinessWorkflowLifecycle';
import type { RebalanceProposalResponse } from '@/types/rebalancing';
import {
  LayoutDashboard,
  Briefcase,
  Compass,
  Scale,
  Sparkles,
  RotateCw,
} from 'lucide-react';

const DEFAULT_AS_OF_DATE = '2026-01-15';

export function AnalystWorkspace() {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlTab = searchParams.get('tab') as 'dashboard' | 'portfolios' | 'drift' | 'proposals' | null;
  const [activeTab, setActiveTabState] = useState<'dashboard' | 'portfolios' | 'drift' | 'proposals'>(
    urlTab || 'dashboard'
  );

  useEffect(() => {
    if (urlTab) {
      setActiveTabState(urlTab);
    }
  }, [urlTab]);

  const setActiveTab = (tab: 'dashboard' | 'portfolios' | 'drift' | 'proposals') => {
    setActiveTabState(tab);
    setSearchParams({ tab });
  };

  const portfolioId = 'PORT-INV-000001-02';
  const [activeProposal, setActiveProposal] = useState<RebalanceProposalResponse | null>(null);

  const { data: valuation, isLoading: isValLoading, refetch: refetchVal } = usePortfolioValuation(portfolioId, DEFAULT_AS_OF_DATE);
  const { data: drift, refetch: refetchDrift } = usePortfolioDrift(portfolioId, DEFAULT_AS_OF_DATE);
  const createProposalMutation = useCreateProposal();

  const handleGenerateProposal = async () => {
    try {
      const result = await createProposalMutation.mutateAsync({
        portfolioId,
        asOfDate: DEFAULT_AS_OF_DATE,
      });
      setActiveProposal(result);
      setActiveTab('proposals');
    } catch {
      // Handled by react-query
    }
  };

  const totalValue = parseFloat(valuation?.total_market_value || '0');
  const requiresRebalance = drift?.rebalance_trigger?.status === 'TRIGGERED' || drift?.rebalance_trigger?.rebalance_required === true;

  return (
    <div className="space-y-6">
      {/* Analyst Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Operations Analyst Workspace
            </h2>
            <Badge variant="navy" size="sm">
              PORTFOLIO OPERATIONS
            </Badge>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Drift surveillance, trade generation, and pre-trade policy constraint evaluation.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              refetchVal();
              refetchDrift();
            }}
            leftIcon={<RotateCw className="w-3.5 h-3.5" />}
          >
            Refresh Analytics
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleGenerateProposal}
            isLoading={createProposalMutation.isPending}
            leftIcon={<Sparkles className="w-4 h-4" />}
          >
            Generate Proposal
          </Button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div role="tablist" aria-label="Analyst Navigation" className="flex items-center gap-1.5 border-b border-slate-200 dark:border-slate-800 overflow-x-auto pb-px">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'dashboard'}
          onClick={() => setActiveTab('dashboard')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'dashboard'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <LayoutDashboard className="w-3.5 h-3.5" />
          <span>Dashboard</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'portfolios'}
          onClick={() => setActiveTab('portfolios')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'portfolios'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <Briefcase className="w-3.5 h-3.5" />
          <span>Portfolios</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'drift'}
          onClick={() => setActiveTab('drift')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'drift'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <Compass className="w-3.5 h-3.5" />
          <span>Drift Analysis</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'proposals'}
          onClick={() => setActiveTab('proposals')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'proposals'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <Scale className="w-3.5 h-3.5" />
          <span>Proposals</span>
          {activeProposal && (
            <Badge variant="warning" size="sm" className="ml-1 text-[9px] py-0 px-1 font-mono">
              NEW
            </Badge>
          )}
        </button>
      </div>

      {/* Tab 1: Dashboard Overview */}
      {activeTab === 'dashboard' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-4">
                <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">Target Portfolio</span>
                <span className="text-sm font-mono font-bold text-slate-900 dark:text-slate-100 block">
                  {portfolioId}
                </span>
                <span className="text-[10px] text-slate-400 mt-1 block">Active Portfolio Scope</span>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">Live Portfolio Valuation</span>
                <span className="text-sm font-mono font-bold text-slate-900 dark:text-slate-100 block">
                  {isValLoading ? '...' : `$${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
                </span>
                <span className="text-[10px] text-slate-400 mt-1 block">FastAPI Analytics Service</span>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">Corridor Drift Status</span>
                <Badge variant={requiresRebalance ? 'warning' : 'success'}>
                  {requiresRebalance ? 'REBALANCE TRIGGERED' : 'BALANCED'}
                </Badge>
                <span className="text-[10px] text-slate-400 mt-1 block">
                  Status: {drift?.rebalance_trigger?.status || 'NORMAL'}
                </span>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">Dual-Key Governance</span>
                <span className="text-xs font-semibold text-slate-900 dark:text-slate-100 block">
                  Analyst Proposes &bull; Reviewer Approves
                </span>
                <span className="text-[10px] text-slate-400 mt-1 block">Strict Separation of Duties</span>
              </CardContent>
            </Card>
          </div>

          <BusinessWorkflowLifecycle
            currentStage={activeProposal ? 'trades_simulated' : requiresRebalance ? 'drift_calculated' : 'holdings_evaluated'}
            proposalStatus={activeProposal?.status}
            portfolioId={portfolioId}
            proposalId={activeProposal?.proposal_id}
          />

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

      {/* Tab 2: Portfolios */}
      {activeTab === 'portfolios' && (
        <div className="space-y-6">
          <HoldingsTable
            positions={valuation?.positions || []}
            totalMarketValue={valuation?.total_market_value || '0'}
          />
        </div>
      )}

      {/* Tab 3: Drift Analysis */}
      {activeTab === 'drift' && (
        <div className="space-y-6">
          <DriftAnalysis driftData={drift} />
        </div>
      )}

      {/* Tab 4: Proposals */}
      {activeTab === 'proposals' && (
        <div className="space-y-6">
          {activeProposal ? (
            <ProposalDetailsCard proposal={activeProposal} onRefresh={refetchDrift} />
          ) : (
            <Card>
              <CardContent className="py-12 text-center space-y-3">
                <Scale className="w-10 h-10 text-slate-400 mx-auto" />
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  No Active Rebalancing Proposal
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                  Click below to execute the deterministic trade recommendation engine for {portfolioId}.
                </p>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleGenerateProposal}
                  isLoading={createProposalMutation.isPending}
                  leftIcon={<Sparkles className="w-4 h-4" />}
                >
                  Generate Recommendation
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
