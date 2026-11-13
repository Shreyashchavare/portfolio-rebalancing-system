import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { Modal } from '@/components/ui/Modal';
import { FinancialMetricCard } from '@/components/ui/FinancialMetricCard';
import { ProposalAuditHistory } from '@/components/business/ProposalAuditHistory';
import { useAuth } from '@/hooks/useAuth';
import { useApproveProposal, useRejectProposal, useProposal, useProposals } from '@/hooks/useApprovals';
import { approvalService } from '@/services/api/approvalService';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Clock,
  UserCheck,
  FileCheck2,
  RotateCw,
  AlertTriangle,
} from 'lucide-react';

export function ApprovalsPage() {
  const { reviewer, canApprove, setPersona, isDevelopment } = useAuth();
  const [proposalId, setProposalId] = useState('RB-2026-000002');
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);
  const [isApproveModalOpen, setIsApproveModalOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [approvalNotes, setApprovalNotes] = useState('');
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const isViewer = reviewer?.role === 'VIEWER';

  const { data: proposalList, refetch: refetchList } = useProposals();
  const { data: proposal, refetch: refetchProposal } = useProposal(proposalId);
  const approveMutation = useApproveProposal();
  const rejectMutation = useRejectProposal();

  const handleResetProposal = async () => {
    try {
      await approvalService.resetProposal(proposalId);
      refetchProposal();
      refetchList();
      setFeedbackMessage({
        type: 'success',
        message: `Proposal ${proposalId} reset to PENDING_REVIEW. You can now execute and test approval or rejection.`,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Reset failed';
      setFeedbackMessage({
        type: 'error',
        message: `Reset failed: ${msg}`,
      });
    }
  };

  const proposalStatus = proposal?.status || 'PENDING_REVIEW';
  const trades = proposal?.trades || [];
  const totalNotional = trades.reduce((acc, t) => acc + parseFloat(t.trade_value || '0'), 0);
  const hardBreaches = proposal?.constraint_findings?.filter((f) => f.is_violated && f.severity === 'HARD') || [];
  const isBlockedByHardConstraint = hardBreaches.length > 0;

  const handleApproveSubmit = async () => {
    if (isViewer) {
      setFeedbackMessage({
        type: 'error',
        message: 'Access Denied: Callers with VIEWER role cannot approve proposals (HTTP 403 Forbidden).',
      });
      setIsApproveModalOpen(false);
      return;
    }

    if (isBlockedByHardConstraint) {
      setFeedbackMessage({
        type: 'error',
        message: 'Action Blocked: Proposal violates one or more hard policy constraints and cannot be approved.',
      });
      setIsApproveModalOpen(false);
      return;
    }

    try {
      const response = await approveMutation.mutateAsync({
        proposalId,
        payload: { notes: approvalNotes.trim() || undefined },
      });
      refetchProposal();
      setFeedbackMessage({
        type: 'success',
        message: `Proposal ${response.proposal_id} successfully APPROVED by ${response.reviewer_id} (Reviewed at ${new Date(response.reviewed_at).toLocaleTimeString()}). Trades staged for broker execution.`,
      });
      setIsApproveModalOpen(false);
      setApprovalNotes('');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Approval failed';
      setFeedbackMessage({
        type: 'error',
        message: `Approval failed: ${msg}`,
      });
      setIsApproveModalOpen(false);
    }
  };

  const handleRejectSubmit = async () => {
    if (!rejectionReason.trim()) {
      setFeedbackMessage({
        type: 'error',
        message: 'Validation Error: Rejection reason cannot be empty or whitespace.',
      });
      return;
    }

    if (isViewer) {
      setFeedbackMessage({
        type: 'error',
        message: 'Access Denied: Callers with VIEWER role cannot reject proposals (HTTP 403 Forbidden).',
      });
      setIsRejectModalOpen(false);
      return;
    }

    try {
      const response = await rejectMutation.mutateAsync({
        proposalId,
        payload: { reason: rejectionReason.trim() },
      });
      refetchProposal();
      setFeedbackMessage({
        type: 'success',
        message: `Proposal ${response.proposal_id} REJECTED by ${response.reviewer_id}. Reason recorded in immutable audit log.`,
      });
      setIsRejectModalOpen(false);
      setRejectionReason('');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Rejection failed';
      setFeedbackMessage({
        type: 'error',
        message: `Rejection failed: ${msg}`,
      });
      setIsRejectModalOpen(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Governance &amp; Approvals
            </h2>
            <Badge variant="brand" size="sm">
              MANDATORY HUMAN GATE
            </Badge>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Authenticated human-in-the-loop signoff, mandatory rejection justification, and append-only audit trail.
          </p>
        </div>

        {/* Active Reviewer Context Display */}
        <div className="flex items-center gap-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-2 px-3 shadow-sm">
          <UserCheck className="w-4 h-4 text-brand-600 dark:text-brand-400" />
          <div className="text-xs">
            <span className="text-slate-500 dark:text-slate-400">Authenticated: </span>
            <span className="font-mono font-semibold text-slate-900 dark:text-slate-100">{reviewer?.reviewer_id} </span>
            <Badge variant={reviewer?.role === 'ADMIN' ? 'danger' : reviewer?.role === 'VIEWER' ? 'neutral' : 'brand'} size="sm">
              {reviewer?.role}
            </Badge>
          </div>
        </div>
      </div>

      {/* Critical Invariant Banner */}
      <Alert variant="info" title="Human Review Boundary (Inviolable Financial Invariant)">
        Approving a proposal marks its trade recommendations as <code>APPROVED</code> and writes an atomic record to the immutable <code>audit_events</code> table. Real custodial holdings are <strong>never mutated directly</strong>. Live order routing occurs exclusively through external broker execution gateways.
      </Alert>

      {/* Role Warning Banner if VIEWER */}
      {isViewer && (
        <Alert variant="warning" title="Read-Only Reviewer Role Active">
          Your active principal has role <code>VIEWER</code>. Under backend authorization policies, governance actions (approvals and rejections) will be rejected with <code>HTTP 403 Forbidden</code>. Switch reviewer roles in the header to test authorized actions.
        </Alert>
      )}

      {/* Action Feedback Banner */}
      {feedbackMessage && (
        <Alert
          variant={feedbackMessage.type === 'success' ? 'success' : 'error'}
          title={feedbackMessage.type === 'success' ? 'Governance Action Completed' : 'Governance Action Blocked'}
        >
          {feedbackMessage.message}
        </Alert>
      )}

      {/* Proposal ID Selector Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <FileCheck2 className="w-4 h-4 text-brand-600 dark:text-brand-400" />
            <label htmlFor="proposal-select" className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              Select Proposal:
            </label>
            <select
              id="proposal-select"
              aria-label="Select Target Proposal"
              value={proposalId}
              onChange={(e) => setProposalId(e.target.value)}
              className="font-mono text-xs px-2.5 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-brand-500 cursor-pointer"
            >
              {proposalList && proposalList.length > 0 ? (
                proposalList.map((p) => (
                  <option key={p.proposal_id} value={p.proposal_id}>
                    {p.proposal_id} ({p.portfolio_id}) &mdash; {p.status}
                  </option>
                ))
              ) : (
                <option value="RB-2026-000002">RB-2026-000002 (PORT-INV-000001-02) &mdash; PENDING_REVIEW</option>
              )}
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <span>or ID:</span>
            <input
              id="proposal-id-input"
              type="text"
              value={proposalId}
              onChange={(e) => setProposalId(e.target.value)}
              placeholder="e.g. RB-2026-000002"
              className="font-mono text-xs px-2 py-1 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-brand-500 w-36"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              refetchProposal();
              refetchList();
              setFeedbackMessage(null);
            }}
            leftIcon={<RotateCw className="w-3 h-3" />}
          >
            Refresh Status
          </Button>
        </div>
      </div>

      {/* Role Notice if not authorized to approve */}
      {!canApprove && (
        <Alert variant="info" title="Dual-Key Fiduciary Authorization Notice">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <span>
              Your current active role is <strong>{reviewer?.role || 'VIEWER'}</strong>. Institutional compliance requires a Risk / Compliance Reviewer (<code>REV-DEV-01</code>) or System Administrator to approve or reject staged proposals.
            </span>
            {isDevelopment && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPersona('COMPLIANCE')}
                leftIcon={<UserCheck className="w-3.5 h-3.5" />}
              >
                Switch to Reviewer Role
              </Button>
            )}
          </div>
        </Alert>
      )}

      {/* Governance Decision Context Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <FinancialMetricCard
          title="Staged Proposal ID"
          value={proposalId}
          badgeText="TARGET"
          badgeVariant="neutral"
          subtitle="Target date: 2026-01-15"
          icon={<FileCheck2 className="w-4 h-4 text-brand-600 dark:text-brand-400" />}
          accentBorder="brand"
        />

        <FinancialMetricCard
          title="Review Decision State"
          value={proposalStatus}
          badgeText={proposalStatus === 'APPROVED' ? 'READY FOR EXECUTION' : proposalStatus === 'REJECTED' ? 'TERMINAL' : 'AWAITING REVIEW'}
          badgeVariant={proposalStatus === 'APPROVED' ? 'success' : proposalStatus === 'REJECTED' ? 'danger' : 'warning'}
          subtitle="One-way lifecycle state"
          icon={<ShieldCheck className="w-4 h-4 text-slate-600 dark:text-slate-400" />}
          accentBorder={proposalStatus === 'APPROVED' ? 'success' : proposalStatus === 'REJECTED' ? 'danger' : 'warning'}
        />

        <FinancialMetricCard
          title="Total Rebalance Trades"
          value={`${trades.length} ${trades.length === 1 ? 'Trade' : 'Trades'}`}
          badgeText={trades.length > 0 && trades[0] ? `${trades[0].trade_side} ${trades[0].symbol || trades[0].instrument_id}` : 'NO ORDERS'}
          badgeVariant="brand"
          subtitle={`Notional: $${totalNotional.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          icon={<Clock className="w-4 h-4 text-slate-600 dark:text-slate-400" />}
          accentBorder="neutral"
        />

        <FinancialMetricCard
          title="Hard Constraint Evaluation"
          value={`${hardBreaches.length} ${hardBreaches.length === 1 ? 'Breach' : 'Breaches'}`}
          badgeText={isBlockedByHardConstraint ? 'BLOCKED BY CONSTRAINTS' : 'CLEARED FOR APPROVAL'}
          badgeVariant={isBlockedByHardConstraint ? 'danger' : 'success'}
          subtitle={isBlockedByHardConstraint ? 'Hard policy violations detected' : 'All mandates satisfied'}
          icon={isBlockedByHardConstraint ? <AlertTriangle className="w-4 h-4 text-rose-600 dark:text-rose-400" /> : <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />}
          accentBorder={isBlockedByHardConstraint ? 'danger' : 'success'}
        />
      </div>

      {/* Constraint Violation Alert if Blocked */}
      {isBlockedByHardConstraint && (
        <Alert variant="error" title="Fiduciary Constraint Policy Violation Detected">
          This proposal violates {hardBreaches.length} hard policy {hardBreaches.length === 1 ? 'mandate' : 'mandates'}. Under fiduciary governance rules, approval is strictly blocked until allocation or constraint parameters are rectified.
        </Alert>
      )}

      {/* Pending Proposal Review Card */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <CardTitle>Proposal Verification &amp; Authorization Action</CardTitle>
              <CardDescription>
                Examine proposed rebalance trades, constraint findings, and execute governance decision
              </CardDescription>
            </div>

            {/* Approval / Rejection Action Buttons */}
            {proposalStatus === 'PENDING_REVIEW' ? (
              <div className="flex items-center gap-2">
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => setIsRejectModalOpen(true)}
                  disabled={!canApprove}
                  leftIcon={<XCircle className="w-4 h-4" />}
                >
                  Reject Proposal
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setIsApproveModalOpen(true)}
                  disabled={!canApprove || isBlockedByHardConstraint}
                  leftIcon={<CheckCircle2 className="w-4 h-4" />}
                >
                  Approve Proposal
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Badge
                  variant={proposalStatus === 'APPROVED' ? 'success' : 'danger'}
                  size="sm"
                >
                  {proposalStatus}
                </Badge>
                {canApprove && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleResetProposal}
                    leftIcon={<RotateCw className="w-3.5 h-3.5" />}
                  >
                    Reset to Pending Review
                  </Button>
                )}
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {trades.length > 0 ? (
            <div className="space-y-2">
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                Staged Proposed Orders ({trades.length}):
              </span>
              {trades.map((t) => (
                <div
                  key={t.trade_id}
                  className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <Badge variant={t.trade_side === 'BUY' ? 'success' : 'danger'} size="sm">
                        {t.trade_side}
                      </Badge>
                      <span className="text-xs font-mono font-bold text-slate-900 dark:text-slate-100">
                        {t.symbol} &bull; {parseFloat(t.quantity).toFixed(4)} Lots @ ${parseFloat(t.unit_price).toFixed(2)}
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 block">
                      {t.instrument_name} ({t.asset_class}) &bull; Notional: ${parseFloat(t.trade_value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="text-right">
                    <Badge variant="brand" size="sm">
                      FEE: ${parseFloat(t.fee_amount).toFixed(2)} ({t.fee_schedule_id || 'FEE-STD'})
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500 dark:text-slate-400 py-3 text-center">
              No proposed trades staged for proposal {proposalId}.
            </p>
          )}

          {/* Constraint Findings Summary */}
          {proposal?.constraint_findings && proposal.constraint_findings.length > 0 && (
            <div className="pt-2 border-t border-slate-200 dark:border-slate-800 space-y-2">
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                Gatekeeper Constraint Evaluations:
              </span>
              {proposal.constraint_findings.slice(0, 4).map((cf, i) => (
                <div
                  key={i}
                  className={`p-2.5 rounded-lg border text-xs ${
                    cf.is_violated
                      ? cf.severity === 'HARD'
                        ? 'border-rose-200 dark:border-rose-900/60 bg-rose-50/50 dark:bg-rose-950/30 text-rose-900 dark:text-rose-200'
                        : 'border-amber-200 dark:border-amber-900/60 bg-amber-50/50 dark:bg-amber-950/30 text-amber-900 dark:text-amber-200'
                      : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{cf.severity}: {cf.constraint_name}</span>
                    <Badge variant={cf.is_violated ? (cf.severity === 'HARD' ? 'danger' : 'warning') : 'success'} size="sm">
                      {cf.is_violated ? (cf.severity === 'HARD' ? 'VIOLATION' : 'WARNING') : 'PASSED'}
                    </Badge>
                  </div>
                  <p className="text-[11px] mt-1 text-slate-600 dark:text-slate-400">{cf.message}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Proposal Audit Trail Card */}
      <ProposalAuditHistory proposalId={proposalId} />

      {/* Approve Modal */}
      <Modal
        isOpen={isApproveModalOpen}
        onClose={() => setIsApproveModalOpen(false)}
        title="Confirm Proposal Approval"
        description={`Authorizing proposal ${proposalId} will stage recommended trades for external execution.`}
      >
        <div className="space-y-4 pt-2">
          <Alert variant="warning" title="Authoritative Signoff Required">
            You are signing off on this proposal as <strong>{reviewer?.reviewer_id}</strong> ({reviewer?.role}). This action is recorded atomically in the audit log.
          </Alert>

          <div>
            <label htmlFor="approval-notes" className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
              Approval Notes (Optional):
            </label>
            <textarea
              id="approval-notes"
              value={approvalNotes}
              onChange={(e) => setApprovalNotes(e.target.value)}
              placeholder="e.g. Approved equity rebalancing to conform portfolio to IPS target corridor."
              rows={3}
              className="w-full text-xs p-2 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
            <Button variant="outline" size="sm" onClick={() => setIsApproveModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleApproveSubmit}
              isLoading={approveMutation.isPending}
              leftIcon={<CheckCircle2 className="w-4 h-4" />}
            >
              Sign &amp; Approve
            </Button>
          </div>
        </div>
      </Modal>

      {/* Reject Modal */}
      <Modal
        isOpen={isRejectModalOpen}
        onClose={() => setIsRejectModalOpen(false)}
        title="Confirm Proposal Rejection"
        description={`Rejecting proposal ${proposalId} marks it as permanently terminal.`}
      >
        <div className="space-y-4 pt-2">
          <Alert variant="error" title="Mandatory Rejection Justification">
            Financial regulations require a non-empty audit justification reason for all rejected rebalancing proposals.
          </Alert>

          <div>
            <label htmlFor="rejection-reason" className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
              Justification Reason <span className="text-rose-500">*</span>:
            </label>
            <textarea
              id="rejection-reason"
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="e.g. Market volatility warrants delaying trade execution until after the CPI release."
              rows={3}
              className="w-full text-xs p-2 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-rose-500"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
            <Button variant="outline" size="sm" onClick={() => setIsRejectModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={handleRejectSubmit}
              isLoading={rejectMutation.isPending}
              leftIcon={<XCircle className="w-4 h-4" />}
            >
              Confirm Rejection
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
