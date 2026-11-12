import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import type { RebalanceProposalResponse } from '@/types/rebalancing';
import {
  Scale,
  DollarSign,
  AlertTriangle,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useApproveProposal, useRejectProposal } from '@/hooks/useApprovals';

interface ProposalDetailsCardProps {
  proposal: RebalanceProposalResponse;
  onRefresh?: () => void;
}

export function ProposalDetailsCard({ proposal, onRefresh }: ProposalDetailsCardProps) {
  const { canApprove } = useAuth();
  const approveMutation = useApproveProposal();
  const rejectMutation = useRejectProposal();

  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [approvalNotes, setApprovalNotes] = useState('');
  const [isApproveModalOpen, setIsApproveModalOpen] = useState(false);

  const handleApprove = async () => {
    try {
      await approveMutation.mutateAsync({
        proposalId: proposal.proposal_id,
        payload: { notes: approvalNotes.trim() || undefined },
      });
      setIsApproveModalOpen(false);
      onRefresh?.();
    } catch {
      // Error handled by react-query / ui feedback
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) return;
    try {
      await rejectMutation.mutateAsync({
        proposalId: proposal.proposal_id,
        payload: { reason: rejectReason.trim() },
      });
      setIsRejectModalOpen(false);
      onRefresh?.();
    } catch {
      // Error handled by react-query
    }
  };

  const isPending = proposal.status === 'PENDING_REVIEW' || proposal.review_decision === 'PENDING';
  const isApproved = proposal.status === 'APPROVED' || proposal.review_decision === 'APPROVED';
  const isRejected = proposal.status === 'REJECTED' || proposal.review_decision === 'REJECTED';

  return (
    <div className="space-y-6">
      {/* Proposal Summary Header */}
      <Card>
        <CardHeader className="pb-3 border-b border-slate-100 dark:border-slate-800">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <Scale className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                <CardTitle className="text-base">
                  Rebalancing Proposal &mdash; {proposal.proposal_id}
                </CardTitle>
                <Badge
                  variant={isApproved ? 'success' : isRejected ? 'danger' : 'warning'}
                  size="sm"
                >
                  {proposal.status}
                </Badge>
              </div>
              <CardDescription className="text-xs mt-0.5">
                Target Portfolio: <span className="font-mono font-semibold">{proposal.portfolio_id}</span> &bull; Evaluation Date: <span className="font-mono">{proposal.as_of_date}</span>
              </CardDescription>
            </div>

            {/* Reviewer Action Buttons */}
            {canApprove && isPending && (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsRejectModalOpen(true)}
                  leftIcon={<XCircle className="w-4 h-4 text-rose-500" />}
                >
                  Reject Proposal
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setIsApproveModalOpen(true)}
                  leftIcon={<CheckCircle2 className="w-4 h-4" />}
                >
                  Approve Trades
                </Button>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
              <span className="text-[11px] text-slate-500 dark:text-slate-400 block">Pre-Trade Value</span>
              <span className="text-sm font-mono font-bold text-slate-900 dark:text-slate-100">
                ${parseFloat(proposal.pre_trade_portfolio_value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
              <span className="text-[11px] text-slate-500 dark:text-slate-400 block">Simulated Post-Trade</span>
              <span className="text-sm font-mono font-bold text-slate-900 dark:text-slate-100">
                ${parseFloat(proposal.post_trade_portfolio_value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
              <span className="text-[11px] text-slate-500 dark:text-slate-400 block">Proposed Orders</span>
              <span className="text-sm font-mono font-bold text-slate-900 dark:text-slate-100">
                {proposal.trades.length} Trades
              </span>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
              <span className="text-[11px] text-slate-500 dark:text-slate-400 block">Estimated Fees</span>
              <span className="text-sm font-mono font-bold text-slate-900 dark:text-slate-100">
                ${parseFloat(proposal.simulation.total_executable_fees || '0').toFixed(2)}
              </span>
            </div>
          </div>

          {/* Decision Reason Banner if reviewed */}
          {proposal.review_reason && (
            <div className="mt-4 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-xs text-amber-900 dark:text-amber-200">
              <span className="font-semibold block mb-0.5">Governance Decision Note:</span>
              {proposal.review_reason}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Proposed Trades Grid */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-brand-600 dark:text-brand-400" />
              <CardTitle className="text-sm">Proposed Execution Orders</CardTitle>
            </div>
            <Badge variant="navy" size="sm">
              DETERMINISTIC RECOMMENDATIONS
            </Badge>
          </div>
          <CardDescription className="text-xs">
            Generated trade orders constrained by minimum lot sizes and transaction fee schedules.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {proposal.trades.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500 dark:text-slate-400">
              No trades proposed. Portfolio is within target corridor tolerance.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400">
                    <th className="pb-2 font-medium">Side</th>
                    <th className="pb-2 font-medium">Security</th>
                    <th className="pb-2 font-medium">Asset Class</th>
                    <th className="pb-2 font-medium text-right">Quantity</th>
                    <th className="pb-2 font-medium text-right">Price</th>
                    <th className="pb-2 font-medium text-right">Notional</th>
                    <th className="pb-2 font-medium text-right">Fee</th>
                    <th className="pb-2 font-medium text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {proposal.trades.map((trade) => {
                    const isBuy = trade.trade_side === 'BUY';
                    return (
                      <tr key={trade.trade_id || trade.instrument_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                        <td className="py-2.5">
                          <span
                            className={`inline-flex items-center gap-1 font-bold text-[11px] px-2 py-0.5 rounded ${
                              isBuy
                                ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-300'
                                : 'bg-rose-100 text-rose-800 dark:bg-rose-950/70 dark:text-rose-300'
                            }`}
                          >
                            {isBuy ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                            {trade.trade_side}
                          </span>
                        </td>
                        <td className="py-2.5 font-medium text-slate-900 dark:text-slate-100">
                          <div>{trade.symbol || trade.instrument_id}</div>
                          <div className="text-[10px] text-slate-400 truncate max-w-[180px]">{trade.instrument_name}</div>
                        </td>
                        <td className="py-2.5">
                          <Badge variant="neutral" size="sm" className="text-[10px]">
                            {trade.asset_class}
                          </Badge>
                        </td>
                        <td className="py-2.5 font-mono text-right text-slate-900 dark:text-slate-100">
                          {parseFloat(trade.quantity).toLocaleString()}
                        </td>
                        <td className="py-2.5 font-mono text-right text-slate-700 dark:text-slate-300">
                          ${parseFloat(trade.unit_price).toFixed(2)}
                        </td>
                        <td className="py-2.5 font-mono font-semibold text-right text-slate-900 dark:text-slate-100">
                          ${parseFloat(trade.trade_value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td className="py-2.5 font-mono text-right text-slate-500 dark:text-slate-400">
                          ${parseFloat(trade.fee_amount || '0').toFixed(2)}
                        </td>
                        <td className="py-2.5 text-center">
                          <Badge variant={trade.status === 'BLOCKED' ? 'danger' : 'brand'} size="sm">
                            {trade.status}
                          </Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Simulated Post-Trade Allocations & Constraint Verification */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Post-Trade Asset Class Simulation</CardTitle>
            <CardDescription className="text-xs">
              Simulated weight shifts vs. investment policy target weights
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {proposal.simulation.asset_classes.map((alloc) => {
                const target = parseFloat(alloc.target_weight);
                const post = parseFloat(alloc.post_trade_weight);
                const drift = parseFloat(alloc.post_trade_drift);

                return (
                  <div key={alloc.asset_class} className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                    <div className="flex items-center justify-between text-xs font-semibold text-slate-900 dark:text-slate-100 mb-1">
                      <span>{alloc.asset_class}</span>
                      <span className="font-mono">{post.toFixed(2)}% (Target: {target.toFixed(2)}%)</span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
                      <span>Post-Trade Value: ${parseFloat(alloc.post_trade_market_value).toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
                      <span className={`font-mono font-semibold ${Math.abs(drift) > 2 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                        Residual Drift: {drift > 0 ? `+${drift.toFixed(2)}%` : `${drift.toFixed(2)}%`}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Policy Constraint Findings */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <CardTitle className="text-sm">Policy Constraint Evaluation</CardTitle>
            </div>
            <CardDescription className="text-xs">
              Hard and soft constraint gatekeeper verification
            </CardDescription>
          </CardHeader>
          <CardContent>
            {proposal.constraint_findings.length === 0 ? (
              <div className="p-4 rounded-lg bg-emerald-50/70 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span className="text-xs text-emerald-900 dark:text-emerald-200">
                  All investment policy constraints satisfied. Zero mandate violations detected.
                </span>
              </div>
            ) : (
              <div className="space-y-2">
                {proposal.constraint_findings.map((cf) => (
                  <div
                    key={cf.constraint_id}
                    className={`p-3 rounded-lg border text-xs ${
                      cf.is_violated
                        ? cf.severity === 'HARD'
                          ? 'border-rose-300 bg-rose-50/70 dark:border-rose-900/60 dark:bg-rose-950/30 text-rose-900 dark:text-rose-200'
                          : 'border-amber-300 bg-amber-50/70 dark:border-amber-900/60 dark:bg-amber-950/30 text-amber-900 dark:text-amber-200'
                        : 'border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-800/60 text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold">{cf.constraint_name}</span>
                      <Badge variant={cf.is_violated ? (cf.severity === 'HARD' ? 'danger' : 'warning') : 'success'} size="sm">
                        {cf.is_violated ? `${cf.severity} VIOLATION` : 'SATISFIED'}
                      </Badge>
                    </div>
                    <p className="text-[11px] leading-relaxed opacity-90">{cf.message}</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Approve Modal */}
      {isApproveModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 dark:bg-black/70 backdrop-blur-sm">
          <Card className="max-w-md w-full shadow-xl">
            <CardHeader>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                <CardTitle>Approve Rebalancing Proposal</CardTitle>
              </div>
              <CardDescription>
                Confirm fiduciary approval of proposal {proposal.proposal_id}. All proposed trades will be marked APPROVED.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Approval Notes (Optional)
                </label>
                <textarea
                  value={approvalNotes}
                  onChange={(e) => setApprovalNotes(e.target.value)}
                  placeholder="Record fiduciary sign-off rationale..."
                  className="w-full text-xs p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  rows={3}
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button variant="outline" size="sm" onClick={() => setIsApproveModalOpen(false)}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleApprove}
                  isLoading={approveMutation.isPending}
                >
                  Confirm Approval
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Reject Modal */}
      {isRejectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 dark:bg-black/70 backdrop-blur-sm">
          <Card className="max-w-md w-full shadow-xl border-rose-200 dark:border-rose-900/60">
            <CardHeader>
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400" />
                <CardTitle>Reject Rebalancing Proposal</CardTitle>
              </div>
              <CardDescription>
                A non-empty justification reason is mandatory by compliance audit policy.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Rejection Reason <span className="text-rose-500">*</span>
                </label>
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Specify reason (e.g. Excessive turnover, cash buffer violation, market volatility)..."
                  className="w-full text-xs p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-rose-500"
                  rows={3}
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button variant="outline" size="sm" onClick={() => setIsRejectModalOpen(false)}>
                  Cancel
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  disabled={!rejectReason.trim()}
                  onClick={handleReject}
                  isLoading={rejectMutation.isPending}
                >
                  Confirm Rejection
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
