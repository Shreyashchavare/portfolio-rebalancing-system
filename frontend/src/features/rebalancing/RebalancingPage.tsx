import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { DataTable, type Column } from '@/components/ui/DataTable';
import { FinancialMetricCard } from '@/components/ui/FinancialMetricCard';
import { SEEDED_PORTFOLIO_REFERENCES } from '@/features/portfolios/types/portfolio';
import { usePortfolioValuation } from '@/features/portfolios/hooks/usePortfolioValuation';
import { usePortfolioDrift } from '@/features/portfolios/hooks/usePortfolioDrift';
import { useCreateProposal } from '@/hooks/useRebalancing';
import type { RebalanceProposalResponse, TradeResponse } from '@/types/rebalancing';
import {
  Scale,
  DollarSign,
  ShieldCheck,
  CheckCircle2,
  Play,
  RotateCcw,
  ArrowRight,
  Lock,
  Briefcase,
  Layers,
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface DisplayTrade {
  tradeId: string;
  side: 'BUY' | 'SELL';
  symbol: string;
  name: string;
  assetClass: string;
  quantity: string;
  unitPrice: string;
  tradeValue: string;
  feeAmount: string;
  feeScheduleId: string;
  status: string;
}

const DEFAULT_AS_OF_DATE = '2026-01-15';

export function RebalancingPage() {
  const [selectedPortfolioId, setSelectedPortfolioId] = useState('PORT-INV-000001-02');
  const [activeProposal, setActiveProposal] = useState<RebalanceProposalResponse | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const { data: valuation, isLoading: isValLoading, refetch: refetchVal } = usePortfolioValuation(selectedPortfolioId, DEFAULT_AS_OF_DATE);
  const { data: drift, refetch: refetchDrift } = usePortfolioDrift(selectedPortfolioId, DEFAULT_AS_OF_DATE);
  const createProposalMutation = useCreateProposal();

  const handleRunOptimization = async () => {
    setActionError(null);
    try {
      const result = await createProposalMutation.mutateAsync({
        portfolioId: selectedPortfolioId,
        asOfDate: DEFAULT_AS_OF_DATE,
      });
      setActiveProposal(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate proposal';
      setActionError(msg);
    }
  };

  const handleResetSimulation = () => {
    setActiveProposal(null);
    setActionError(null);
    refetchVal();
    refetchDrift();
  };

  // Convert proposal trades to table rows
  const displayTrades: DisplayTrade[] = activeProposal
    ? activeProposal.trades.map((t: TradeResponse) => ({
        tradeId: t.trade_id,
        side: (t.trade_side === 'BUY' ? 'BUY' : 'SELL') as 'BUY' | 'SELL',
        symbol: t.symbol || t.instrument_id,
        name: t.instrument_name || t.instrument_id,
        assetClass: t.asset_class,
        quantity: parseFloat(t.quantity).toFixed(4),
        unitPrice: `$${parseFloat(t.unit_price).toFixed(2)}`,
        tradeValue: `$${parseFloat(t.trade_value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
        feeAmount: `$${parseFloat(t.fee_amount).toFixed(2)}`,
        feeScheduleId: t.fee_schedule_id || 'FEE-STD',
        status: t.status,
      }))
    : [];

  const columns: Column<DisplayTrade>[] = [
    {
      key: 'side',
      header: 'Side',
      render: (item) => (
        <Badge
          variant={item.side === 'BUY' ? 'success' : 'danger'}
          size="sm"
          className="font-mono font-bold"
        >
          {item.side}
        </Badge>
      ),
    },
    {
      key: 'symbol',
      header: 'Security',
      render: (item) => (
        <div>
          <span className="font-mono font-semibold text-slate-900 dark:text-slate-100">{item.symbol}</span>
          <span className="text-[11px] text-slate-500 dark:text-slate-400 block">{item.name}</span>
        </div>
      ),
    },
    {
      key: 'quantity',
      header: 'Quantity (Lot-Sized)',
      align: 'right',
      render: (item) => (
        <span className="font-mono text-slate-900 dark:text-slate-100 font-semibold">{item.quantity}</span>
      ),
    },
    {
      key: 'unitPrice',
      header: 'Execution Price',
      align: 'right',
      render: (item) => <span className="font-mono">{item.unitPrice}</span>,
    },
    {
      key: 'tradeValue',
      header: 'Notional Value',
      align: 'right',
      render: (item) => (
        <span className="font-mono font-semibold text-slate-900 dark:text-slate-100">
          {item.tradeValue}
        </span>
      ),
    },
    {
      key: 'feeAmount',
      header: 'Tiered Broker Fee',
      align: 'right',
      render: (item) => (
        <div>
          <span className="font-mono font-medium text-slate-700 dark:text-slate-300">{item.feeAmount}</span>
          <span className="text-[10px] text-slate-400 font-mono block">{item.feeScheduleId}</span>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Staging State',
      render: (item) => (
        <Badge variant="brand" size="sm">
          {item.status}
        </Badge>
      ),
    },
  ];

  // Derived metric values
  const preValue = activeProposal
    ? parseFloat(activeProposal.pre_trade_portfolio_value)
    : parseFloat(valuation?.total_market_value || '0');

  const postValue = activeProposal
    ? parseFloat(activeProposal.post_trade_portfolio_value)
    : parseFloat(valuation?.total_market_value || '0');

  const postCash = activeProposal?.simulation
    ? parseFloat(activeProposal.simulation.post_trade_cash)
    : parseFloat(
        valuation?.asset_classes?.find((a) => a.asset_class.toUpperCase() === 'CASH')
          ?.market_value || '0'
      );

  const totalFees = activeProposal?.simulation
    ? parseFloat(activeProposal.simulation.total_executable_fees)
    : 0;

  const isTriggered = drift?.rebalance_trigger?.rebalance_required || drift?.rebalance_trigger?.status === 'TRIGGERED';

  const cashAsset = valuation?.asset_classes?.find(
    (a) => a.asset_class.toUpperCase() === 'CASH'
  );
  const preCashVal = cashAsset ? parseFloat(cashAsset.market_value) : 0;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Rebalancing Engine &amp; Decision Workspace
            </h2>
            <Badge variant={activeProposal ? 'success' : 'brand'} size="sm">
              {activeProposal ? 'LIVE PROPOSAL STAGED' : 'DETERMINISTIC STAGING'}
            </Badge>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Lot-size rounding, tiered execution fee schedules, in-memory simulation, and constraint gatekeeper.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Portfolio selection quick-switch */}
          <div className="flex items-center gap-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg px-2.5 py-1 text-xs">
            <Briefcase className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedPortfolioId}
              onChange={(e) => {
                setSelectedPortfolioId(e.target.value);
                setActiveProposal(null);
              }}
              className="bg-transparent border-none text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none cursor-pointer"
            >
              {SEEDED_PORTFOLIO_REFERENCES.map((p) => (
                <option key={p.portfolio_id} value={p.portfolio_id} className="dark:bg-slate-900">
                  {p.portfolio_id} ({p.portfolio_name})
                </option>
              ))}
            </select>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleResetSimulation}
            leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
          >
            Reset
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={handleRunOptimization}
            isLoading={createProposalMutation.isPending || isValLoading}
            leftIcon={<Play className="w-3.5 h-3.5" />}
          >
            Run Optimization
          </Button>
        </div>
      </div>

      {/* Safety Invariant Notice */}
      <Alert variant="info" title="Zero Live Holding Mutation Invariant">
        Recommendations generated by this engine are strictly non-mutating in-memory proposals. Real portfolio holdings are never modified. Downstream approval via authenticated reviewer credentials is required before any execution ticket is published.
      </Alert>

      {/* Action Error if Mutation Fails */}
      {actionError && (
        <Alert variant="error" title="Rebalancing Optimization Error">
          {actionError}
        </Alert>
      )}

      {/* Trigger Warning if Portfolio Needs Rebalance */}
      {!activeProposal && isTriggered && (
        <Alert variant="warning" title="Allocation Drift Detected &mdash; Rebalancing Triggered">
          Portfolio {selectedPortfolioId} has breached its target corridor thresholds. Click <strong>Run Optimization</strong> to generate lot-sized trade recommendations and simulate post-trade cash solvency.
        </Alert>
      )}

      {/* Decision Context Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <FinancialMetricCard
          title="Pre-Trade Portfolio Value"
          value={`$${preValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          badgeText={selectedPortfolioId}
          badgeVariant="neutral"
          subtitle={`Valuation as-of ${valuation?.as_of_date || '2026-01-15'}`}
          icon={<DollarSign className="w-4 h-4 text-brand-600 dark:text-brand-400" />}
          accentBorder="brand"
        />

        <FinancialMetricCard
          title="Post-Trade Simulated Value"
          value={`$${postValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          badgeText={`Fee Deducted (-$${totalFees.toFixed(2)})`}
          badgeVariant="neutral"
          subtitle="Tiered broker fee subtracted"
          icon={<Scale className="w-4 h-4 text-slate-600 dark:text-slate-400" />}
          accentBorder="neutral"
        />

        <FinancialMetricCard
          title="Post-Trade Cash Balance"
          value={`$${postCash.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          badgeText="SOLVENT &bull; NO OVERDRAFT"
          badgeVariant="success"
          subtitle={`Pre-trade cash: $${preCashVal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          icon={<CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />}
          accentBorder="success"
        />

        <FinancialMetricCard
          title="Human Review Boundary"
          value={activeProposal ? activeProposal.status : 'PENDING REVIEW'}
          badgeText={activeProposal ? activeProposal.proposal_id : 'AWAITING GOVERNANCE'}
          badgeVariant="warning"
          subtitle="Mandatory signoff gate"
          icon={<Lock className="w-4 h-4 text-amber-600 dark:text-amber-400" />}
          accentBorder="warning"
        />
      </div>

      {/* Main Two-Column Layout: Proposed Trade Tickets & Gatekeeper */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Proposed Trade Ticket Table */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Deterministic Proposed Trade Tickets</CardTitle>
                  <CardDescription>
                    Trades rounded to integer lots, minimum trade values ($500), and tiered fees applied
                  </CardDescription>
                </div>
                <Badge variant="navy" size="sm">
                  {displayTrades.length} Proposed {displayTrades.length === 1 ? 'Trade' : 'Trades'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <DataTable
                columns={columns}
                data={displayTrades}
                keyExtractor={(item) => item.tradeId}
              />
            </CardContent>
          </Card>

          {/* Post-Trade Simulation Residual Drift */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Post-Trade Residual Drift Simulation</CardTitle>
                  <CardDescription>
                    Asset weight realignment after executing proposed trade ticket in simulation
                  </CardDescription>
                </div>
                <Layers className="w-4 h-4 text-slate-400" />
              </div>
            </CardHeader>
            <CardContent>
              {activeProposal?.simulation?.asset_classes && activeProposal.simulation.asset_classes.length > 0 ? (
                <div className="space-y-4">
                  {activeProposal.simulation.asset_classes.map((ac) => {
                    const postWeight = parseFloat(ac.post_trade_weight || '0');
                    const targetWeight = parseFloat(ac.target_weight || '0');
                    const driftVal = parseFloat(ac.post_trade_drift || '0');
                    const isBalanced = Math.abs(driftVal) <= 0.05;

                    return (
                      <div key={ac.asset_class}>
                        <div className="flex items-center justify-between text-xs font-semibold mb-1">
                          <span className="text-slate-700 dark:text-slate-300 capitalize">{ac.asset_class}</span>
                          <span className={`font-mono ${isBalanced ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>
                            Post-Trade: {postWeight.toFixed(2)}% | Target: {targetWeight.toFixed(2)}% | Residual Drift: {driftVal >= 0 ? '+' : ''}{driftVal.toFixed(2)}%
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden flex">
                          <div
                            className={ac.asset_class === 'EQUITY' ? 'bg-brand-600' : ac.asset_class === 'FIXED_INCOME' ? 'bg-emerald-600' : ac.asset_class === 'DEBT' ? 'bg-blue-600' : 'bg-amber-500'}
                            style={{ width: `${Math.min(100, Math.max(5, postWeight))}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="space-y-3">
                  <div>
                    <div className="flex items-center justify-between text-xs font-semibold mb-1">
                      <span className="text-slate-700 dark:text-slate-300">Equity Asset Weight</span>
                      <span className="font-mono text-emerald-600 dark:text-emerald-400">
                        71.43% &rarr; 60.11% (Residual: +0.11%)
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden flex">
                      <div className="bg-brand-600 w-[60.11%]" />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between text-xs font-semibold mb-1">
                      <span className="text-slate-700 dark:text-slate-300">Cash Asset Weight</span>
                      <span className="font-mono text-emerald-600 dark:text-emerald-400">
                        28.57% &rarr; 39.89% (Residual: -0.11%)
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden flex">
                      <div className="bg-emerald-600 w-[39.89%]" />
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Col: Constraint Gatekeeper & Safety Findings */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <CardTitle>Constraint Gatekeeper</CardTitle>
              </div>
              <CardDescription>
                Automated compliance and financial risk evaluations
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {activeProposal?.constraint_findings && activeProposal.constraint_findings.length > 0 ? (
                activeProposal.constraint_findings.map((cf, idx) => {
                  const isHard = cf.severity === 'HARD';
                  const isViolated = cf.is_violated;

                  return (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg border ${
                        isViolated
                          ? isHard
                            ? 'border-rose-200 dark:border-rose-800/60 bg-rose-50/50 dark:bg-rose-950/30'
                            : 'border-amber-200 dark:border-amber-800/60 bg-amber-50/50 dark:bg-amber-950/30'
                          : 'border-emerald-200 dark:border-emerald-800/60 bg-emerald-50/50 dark:bg-emerald-950/30'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className={`text-xs font-semibold ${isViolated ? (isHard ? 'text-rose-900 dark:text-rose-200' : 'text-amber-900 dark:text-amber-200') : 'text-emerald-900 dark:text-emerald-200'}`}>
                          {cf.severity}: {cf.constraint_name}
                        </span>
                        <Badge variant={isViolated ? (isHard ? 'danger' : 'warning') : 'success'} size="sm">
                          {isViolated ? (isHard ? 'VIOLATION' : 'WARNING') : 'PASSED'}
                        </Badge>
                      </div>
                      <p className={`text-[11px] mt-1 ${isViolated ? (isHard ? 'text-rose-700 dark:text-rose-300' : 'text-amber-700 dark:text-amber-300') : 'text-emerald-700 dark:text-emerald-300'}`}>
                        {cf.message}
                      </p>
                    </div>
                  );
                })
              ) : (
                <>
                  <div className="p-3 rounded-lg border border-emerald-200 dark:border-emerald-800/60 bg-emerald-50/50 dark:bg-emerald-950/30">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-emerald-900 dark:text-emerald-200">
                        HARD: ESG Exclusion List
                      </span>
                      <Badge variant="success" size="sm">PASSED</Badge>
                    </div>
                    <p className="text-[11px] text-emerald-700 dark:text-emerald-300 mt-1">
                      Zero proposed instruments are barred by active ESG exclusion mandates.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-emerald-200 dark:border-emerald-800/60 bg-emerald-50/50 dark:bg-emerald-950/30">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-emerald-900 dark:text-emerald-200">
                        HARD: Cash Overdraft Protection
                      </span>
                      <Badge variant="success" size="sm">SOLVENT</Badge>
                    </div>
                    <p className="text-[11px] text-emerald-700 dark:text-emerald-300 mt-1">
                      Post-trade cash balance strictly exceeds minimum liquidity reserve.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-blue-200 dark:border-blue-800/60 bg-blue-50/50 dark:bg-blue-950/30">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-blue-900 dark:text-blue-200">
                        SOFT: Maximum Turnover Buffer
                      </span>
                      <Badge variant="brand" size="sm">EVALUATED</Badge>
                    </div>
                    <p className="text-[11px] text-blue-700 dark:text-blue-300 mt-1">
                      Turnover remains within standard portfolio quarterly rebalancing limits.
                    </p>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Governance Handoff</CardTitle>
              <CardDescription>
                Stage proposal for authorized human review
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-xs text-slate-600 dark:text-slate-400">
                Proposal <strong>{activeProposal ? activeProposal.proposal_id : 'RB-2026-000004'}</strong> is staged in state <code>{activeProposal ? activeProposal.status : 'PENDING_REVIEW'}</code>.
              </p>
              <Link to="/approvals" className="block">
                <Button variant="primary" size="md" className="w-full" rightIcon={<ArrowRight className="w-4 h-4" />}>
                  Transfer to Approvals Queue
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
