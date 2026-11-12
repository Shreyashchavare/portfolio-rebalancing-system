import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { Modal } from '@/components/ui/Modal';
import { DataTable, type Column } from '@/components/ui/DataTable';
import { FinancialMetricCard } from '@/components/ui/FinancialMetricCard';
import { useAuth } from '@/hooks/useAuth';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Clock,
  UserCheck,
  FileCheck2,
  History,
  Info,
} from 'lucide-react';

interface AuditItem {
  eventId: string;
  action: 'APPROVE' | 'REJECT' | 'PROPOSAL_GENERATED';
  actorId: string;
  role: string;
  timestamp: string;
  reason: string;
}

const SAMPLE_AUDIT_LOG: AuditItem[] = [
  {
    eventId: 'AUDIT-20260115-001',
    action: 'APPROVE',
    actorId: 'REV-DEV-01',
    role: 'REVIEWER',
    timestamp: '2026-01-15T10:30:00Z',
    reason: 'Approved equity rebalancing to conform portfolio to IPS target corridor.',
  },
  {
    eventId: 'AUDIT-20260114-002',
    action: 'REJECT',
    actorId: 'REV-DEV-ADMIN',
    role: 'ADMIN',
    timestamp: '2026-01-14T14:15:00Z',
    reason: 'Market volatility warrants delaying trade execution until CPI print.',
  },
];

export function ApprovalsPage() {
  const { reviewer } = useAuth();
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [proposalStatus, setProposalStatus] = useState<'PENDING_REVIEW' | 'APPROVED' | 'REJECTED'>('PENDING_REVIEW');
  const [errorMessage, setErrorMessage] = useState('');

  const isViewer = reviewer?.role === 'VIEWER';

  const handleApprove = () => {
    if (isViewer) {
      setErrorMessage('Access Denied: Callers with VIEWER role cannot approve proposals (HTTP 403 Forbidden).');
      return;
    }
    setProposalStatus('APPROVED');
    setErrorMessage('');
  };

  const handleRejectSubmit = () => {
    if (!rejectionReason.trim()) {
      setErrorMessage('Validation Error: Rejection reason cannot be empty or whitespace.');
      return;
    }
    if (isViewer) {
      setErrorMessage('Access Denied: Callers with VIEWER role cannot reject proposals (HTTP 403 Forbidden).');
      setIsRejectModalOpen(false);
      return;
    }
    setProposalStatus('REJECTED');
    setIsRejectModalOpen(false);
    setErrorMessage('');
  };

  const auditColumns: Column<AuditItem>[] = [
    {
      key: 'eventId',
      header: 'Audit Event ID',
      render: (item) => <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">{item.eventId}</span>,
    },
    {
      key: 'action',
      header: 'Decision Action',
      render: (item) => (
        <Badge
          variant={item.action === 'APPROVE' ? 'success' : item.action === 'REJECT' ? 'danger' : 'neutral'}
          size="sm"
        >
          {item.action}
        </Badge>
      ),
    },
    {
      key: 'actorId',
      header: 'Reviewer Principal',
      render: (item) => (
        <div>
          <span className="font-mono text-xs font-semibold text-slate-900 dark:text-slate-100">{item.actorId}</span>
          <span className="text-[10px] text-slate-400 block">{item.role}</span>
        </div>
      ),
    },
    {
      key: 'timestamp',
      header: 'Timestamp',
      render: (item) => <span className="font-mono text-[11px] text-slate-500">{item.timestamp}</span>,
    },
    {
      key: 'reason',
      header: 'Mandatory Justification Reason',
      render: (item) => <span className="text-xs text-slate-700 dark:text-slate-300">{item.reason}</span>,
    },
  ];

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

      {/* Action Error Banner */}
      {errorMessage && (
        <Alert variant="error" title="Governance Action Blocked">
          {errorMessage}
        </Alert>
      )}

      {/* Governance Decision Context Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <FinancialMetricCard
          title="Staged Proposal ID"
          value="RB-20260115-000001"
          badgeText="PORT-INV-000001-01"
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
          value="1 Trade"
          badgeText="SELL AAPL &bull; 660 Lots"
          badgeVariant="brand"
          subtitle="Notional: $118,800.00"
          icon={<Clock className="w-4 h-4 text-slate-600 dark:text-slate-400" />}
          accentBorder="neutral"
        />

        <FinancialMetricCard
          title="Hard Constraint Evaluation"
          value="0 Breaches"
          badgeText="CLEARED FOR APPROVAL"
          badgeVariant="success"
          subtitle="All mandates satisfied"
          icon={<CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />}
          accentBorder="success"
        />
      </div>

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
            {proposalStatus === 'PENDING_REVIEW' && (
              <div className="flex items-center gap-2">
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => setIsRejectModalOpen(true)}
                  leftIcon={<XCircle className="w-4 h-4" />}
                >
                  Reject Proposal
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleApprove}
                  leftIcon={<CheckCircle2 className="w-4 h-4" />}
                >
                  Approve Proposal
                </Button>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">Trade Execution Detail</span>
              <Badge variant="navy" size="sm">Single Trade Ticket</Badge>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
              <div>
                <span className="text-slate-400 text-[10px] block">SECURITY</span>
                <span className="font-semibold text-slate-900 dark:text-slate-100">AAPL (Apple Inc.)</span>
              </div>
              <div>
                <span className="text-slate-400 text-[10px] block">ACTION</span>
                <span className="font-semibold text-rose-600 dark:text-rose-400">SELL 660 LOTS</span>
              </div>
              <div>
                <span className="text-slate-400 text-[10px] block">NOTIONAL VALUE</span>
                <span className="font-semibold text-slate-900 dark:text-slate-100">$118,800.00</span>
              </div>
              <div>
                <span className="text-slate-400 text-[10px] block">BROKER FEE</span>
                <span className="font-semibold text-slate-900 dark:text-slate-100">$125.00</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Immutable Append-Only Audit Trail Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <History className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <div>
                <CardTitle>Chronological Immutable Audit Log</CardTitle>
                <CardDescription>
                  Permanent append-only record from PostgreSQL audit_events (Zero update or delete operations permitted)
                </CardDescription>
              </div>
            </div>
            <Badge variant="success" size="sm">
              Append-Only Guaranteed
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={auditColumns}
            data={SAMPLE_AUDIT_LOG}
            keyExtractor={(item) => item.eventId}
          />
        </CardContent>
      </Card>

      {/* Mandatory Rejection Modal */}
      <Modal
        isOpen={isRejectModalOpen}
        onClose={() => setIsRejectModalOpen(false)}
        title="Reject Rebalance Proposal"
        description="The backend requires a non-empty business justification reason to permanently reject a proposal."
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setIsRejectModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" size="sm" onClick={handleRejectSubmit}>
              Confirm Rejection
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <label className="block text-xs font-medium text-slate-700 dark:text-slate-300">
            Mandatory Rejection Reason <span className="text-rose-500">*</span>
          </label>
          <textarea
            rows={3}
            value={rejectionReason}
            onChange={(e) => setRejectionReason(e.target.value)}
            placeholder="e.g. Market volatility warrants pausing equity sales today..."
            className="w-full p-2.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
          />
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500 dark:text-slate-400">
            <Info className="w-3.5 h-3.5 text-slate-400" />
            <span>This reason will be recorded immutably in the audit trail.</span>
          </div>
        </div>
      </Modal>
    </div>
  );
}
