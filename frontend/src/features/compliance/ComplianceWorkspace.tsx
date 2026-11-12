import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ProposalDetailsCard } from '@/components/business/ProposalDetailsCard';
import { ProposalAuditHistory } from '@/components/business/ProposalAuditHistory';
import { BusinessWorkflowLifecycle } from '@/components/business/BusinessWorkflowLifecycle';
import { policyService } from '@/services/api/policyService';
import { useAuth } from '@/hooks/useAuth';
import { useProposals, useProposal } from '@/hooks/useApprovals';
import type { PolicyAskResponse } from '@/types/policies';
import type { RebalanceProposalResponse } from '@/types/rebalancing';
import {
  ShieldCheck,
  FileCheck,
  FileText,
  History,
  Search,
  Send,
} from 'lucide-react';

const DEFAULT_REVIEW_PROPOSAL: RebalanceProposalResponse = {
  proposal_id: 'PROP-DEMO-01',
  portfolio_id: 'PORT-INV-000001-02',
  as_of_date: '2026-01-15',
  status: 'PENDING_REVIEW',
  review_decision: 'PENDING',
  review_reason: null,
  pre_trade_portfolio_value: '436718.28',
  post_trade_portfolio_value: '436590.98',
  created_at: '2026-01-15T10:00:00Z',
  trades: [
    {
      trade_id: 'TRD-000007',
      proposal_id: 'PROP-DEMO-01',
      instrument_id: 'INS-000008',
      symbol: 'DB-GL-SOV',
      instrument_name: 'Global Sovereign Aggregate Debt',
      asset_class: 'DEBT',
      trade_side: 'SELL',
      quantity: '1210.0000',
      unit_price: '101.7223',
      trade_value: '123083.9830',
      fee_amount: '55.7710',
      fee_schedule_id: 'FEE-DEB-S-02',
      status: 'PROPOSED',
      diagnostic: null,
    },
    {
      trade_id: 'TRD-000008',
      proposal_id: 'PROP-DEMO-01',
      instrument_id: 'INS-000001',
      symbol: 'EQ-US-TECH',
      instrument_name: 'US Large Cap Technology Benchmark',
      asset_class: 'EQUITY',
      trade_side: 'BUY',
      quantity: '1349.0000',
      unit_price: '142.1590',
      trade_value: '191772.4910',
      fee_amount: '120.8862',
      fee_schedule_id: 'FEE-EQU-B-01',
      status: 'PROPOSED',
      diagnostic: null,
    },
  ],
  simulation: {
    pre_trade_portfolio_value: '436718.28',
    post_trade_portfolio_value: '436590.98',
    pre_trade_cash: '25200.00',
    post_trade_cash: '234208.84',
    total_executable_fees: '176.66',
    positions: [],
    asset_classes: [],
    residual_drifts: {},
  },
  constraint_findings: [
    {
      constraint_id: 'CONST-CASH-FLOOR',
      constraint_name: 'Minimum Cash Buffer (5.0%)',
      constraint_type: 'CASH_BUFFER',
      severity: 'HARD',
      scope_type: 'PORTFOLIO',
      scope_reference_id: 'PORT-INV-000001-02',
      threshold_value: '5.00',
      threshold_unit: 'PERCENT',
      is_violated: false,
      affected_instrument_id: null,
      message: 'Post-trade cash (5.84%) satisfies minimum required cash buffer of 5.0%.',
    },
  ],
  warnings: [],
  is_executable: true,
  requires_human_review: true,
};

export function ComplianceWorkspace() {
  const { reviewer } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const urlTab = searchParams.get('tab') as 'queue' | 'details' | 'policies' | 'audit' | null;
  const [activeTab, setActiveTabState] = useState<'queue' | 'details' | 'policies' | 'audit'>(
    urlTab || 'queue'
  );

  useEffect(() => {
    if (urlTab) {
      setActiveTabState(urlTab);
    }
  }, [urlTab]);

  const setActiveTab = (tab: 'queue' | 'details' | 'policies' | 'audit') => {
    setActiveTabState(tab);
    setSearchParams({ tab });
  };

  const [selectedProposalId, setSelectedProposalId] = useState('PROP-DEMO-01');

  // Real backend queries
  const { data: proposalsList, refetch: refetchProposals } = useProposals();
  const { data: fetchedProposal, refetch: refetchActiveProposal } = useProposal(selectedProposalId);

  useEffect(() => {
    if (proposalsList && proposalsList[0] && selectedProposalId === 'PROP-DEMO-01') {
      setSelectedProposalId(proposalsList[0].proposal_id);
    }
  }, [proposalsList, selectedProposalId]);

  // Policy Q&A state
  const [policyQuestion, setPolicyQuestion] = useState('What are the maximum equity concentration limits?');
  const [policyAnswer, setPolicyAnswer] = useState<PolicyAskResponse | null>(null);
  const [isAskingPolicy, setIsAskingPolicy] = useState(false);

  const queueItems = (proposalsList && proposalsList.length > 0)
    ? proposalsList
    : [DEFAULT_REVIEW_PROPOSAL];

  const activeProposal: RebalanceProposalResponse =
    fetchedProposal ||
    queueItems.find((p) => p.proposal_id === selectedProposalId) ||
    queueItems[0] ||
    DEFAULT_REVIEW_PROPOSAL;

  const handleAskPolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!policyQuestion.trim()) return;
    setIsAskingPolicy(true);
    try {
      const resp = await policyService.ask({ query: policyQuestion.trim() });
      setPolicyAnswer(resp);
    } catch {
      // Handled
    } finally {
      setIsAskingPolicy(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Compliance Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Risk &amp; Compliance Review Desk
            </h2>
            <Badge variant="navy" size="sm">
              MANDATORY DUAL-KEY GOVERNANCE
            </Badge>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Independent fiduciary review of rebalancing proposals against IPS mandates and legal constraints.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <Badge variant="brand" size="sm" className="font-mono">
            REVIEWER IDENTITY: {reviewer?.reviewer_id || 'REV-DEV-01'}
          </Badge>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div role="tablist" aria-label="Compliance Navigation" className="flex items-center gap-1.5 border-b border-slate-200 dark:border-slate-800 overflow-x-auto pb-px">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'queue'}
          onClick={() => setActiveTab('queue')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'queue'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Review Queue</span>
          <Badge variant="warning" size="sm" className="ml-1 text-[9px] py-0 px-1 font-mono">
            {proposalsList ? proposalsList.filter(p => p.status === 'PENDING_REVIEW').length : 0} PENDING
          </Badge>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'details'}
          onClick={() => setActiveTab('details')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'details'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <FileCheck className="w-3.5 h-3.5" />
          <span>Proposal Details</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'policies'}
          onClick={() => setActiveTab('policies')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'policies'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Policy Checks (RAG)</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'audit'}
          onClick={() => setActiveTab('audit')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'audit'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <History className="w-3.5 h-3.5" />
          <span>Audit History</span>
        </button>
      </div>

      {/* Tab 1: Review Queue */}
      {activeTab === 'queue' && (
        <div className="space-y-6">
          <BusinessWorkflowLifecycle
            currentStage="compliance_reviewed"
            proposalStatus={activeProposal?.status || 'PENDING_REVIEW'}
            proposalId={selectedProposalId}
          />

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Pending Proposal Governance Worklist</CardTitle>
              <CardDescription className="text-xs">
                Proposals staged by Operations Analysts requiring human sign-off before trade order dispatch.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {queueItems.map((p) => {
                  const isPending = p.status === 'PENDING_REVIEW';
                  const isSelected = p.proposal_id === selectedProposalId;
                  const tradesCount = p.trades?.length || 0;
                  const totalFees = p.simulation?.total_executable_fees || '0.00';

                  return (
                    <div
                      key={p.proposal_id}
                      onClick={() => {
                        setSelectedProposalId(p.proposal_id);
                        setActiveTab('details');
                      }}
                      className={`py-3 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/40 p-2 rounded-lg cursor-pointer transition-colors ${
                        isSelected ? 'bg-slate-50 dark:bg-slate-800/60 ring-1 ring-brand-500/30' : ''
                      }`}
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-xs text-slate-900 dark:text-slate-100">
                            {p.proposal_id}
                          </span>
                          <Badge
                            variant={isPending ? 'warning' : p.status === 'APPROVED' ? 'success' : 'danger'}
                            size="sm"
                          >
                            {isPending ? 'PENDING HUMAN REVIEW' : p.status}
                          </Badge>
                          <Badge variant="neutral" size="sm" className="font-mono text-[10px]">
                            {p.portfolio_id}
                          </Badge>
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">
                          Evaluated on {p.as_of_date} &bull; {tradesCount} Proposed {tradesCount === 1 ? 'Order' : 'Orders'} &bull; Est. Fees: ${parseFloat(totalFees).toFixed(2)}
                        </div>
                      </div>

                      <Button variant={isPending ? 'primary' : 'outline'} size="sm">
                        {isPending ? 'Inspect & Decide' : 'View Details'}
                      </Button>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 2: Proposal Details & Actions */}
      {activeTab === 'details' && (
        <div className="space-y-6">
          {activeProposal ? (
            <ProposalDetailsCard
              proposal={activeProposal}
              onRefresh={() => {
                refetchProposals();
                refetchActiveProposal();
              }}
            />
          ) : (
            <div className="py-8 text-center text-xs text-slate-500 dark:text-slate-400">
              Select a proposal from the Review Queue to inspect trade details and constraint findings.
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Policy Checks (RAG) */}
      {activeTab === 'policies' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                <CardTitle className="text-sm">Compliance Policy Assistant (Policy RAG)</CardTitle>
              </div>
              <CardDescription className="text-xs">
                Query grounded investment policies, client mandates, and concentration constraints using FastEmbed ONNX.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <form onSubmit={handleAskPolicy} className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={policyQuestion}
                    onChange={(e) => setPolicyQuestion(e.target.value)}
                    placeholder="Ask an investment compliance question (e.g., turnover limit, single stock cap)..."
                    className="w-full text-xs pl-9 pr-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  isLoading={isAskingPolicy}
                  leftIcon={<Send className="w-3.5 h-3.5" />}
                >
                  Ask Policy
                </Button>
              </form>

              {policyAnswer && (
                <div className="p-4 rounded-xl border border-blue-200 dark:border-blue-900/60 bg-blue-50/70 dark:bg-blue-950/30 text-xs space-y-3">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-blue-950 dark:text-blue-100">Grounded Answer:</span>
                      <Badge variant="brand" size="sm">
                        {policyAnswer.retrieval_status}
                      </Badge>
                    </div>
                    <p className="text-slate-800 dark:text-slate-200 leading-relaxed">
                      {policyAnswer.answer}
                    </p>
                  </div>

                  {policyAnswer.citations.length > 0 && (
                    <div className="pt-2 border-t border-blue-200 dark:border-blue-800/80">
                      <span className="font-semibold text-slate-900 dark:text-slate-100 block mb-1">
                        Citations &amp; Document Evidence:
                      </span>
                      <div className="space-y-1.5">
                        {policyAnswer.citations.map((c, i) => (
                          <div key={i} className="p-2 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-[11px]">
                            <span className="font-bold text-slate-900 dark:text-slate-100">{c.document_title}</span>{' '}
                            <span className="text-slate-400 font-mono">v{c.version} ({c.section_title || 'General'})</span>
                            {c.excerpt && <p className="text-slate-600 dark:text-slate-300 italic mt-0.5">&ldquo;{c.excerpt}&rdquo;</p>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 4: Audit History */}
      {activeTab === 'audit' && (
        <div className="space-y-6">
          <ProposalAuditHistory proposalId={selectedProposalId} />
        </div>
      )}
    </div>
  );
}
