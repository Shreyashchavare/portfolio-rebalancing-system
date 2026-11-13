import { useProposalAudit } from '@/hooks/useApprovals';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { History, Clock, CheckCircle2, XCircle } from 'lucide-react';

interface ProposalAuditHistoryProps {
  proposalId?: string;
  className?: string;
}

export function ProposalAuditHistory({ proposalId, className }: ProposalAuditHistoryProps) {
  const { data, isLoading, isError } = useProposalAudit(proposalId);

  if (!proposalId) {
    return (
      <Card className={className}>
        <CardHeader>
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-brand-600 dark:text-brand-400" />
            <CardTitle className="text-sm">Audit Trail &amp; Governance Traceability</CardTitle>
          </div>
          <CardDescription className="text-xs">
            Select a proposal to inspect its immutable chronological audit records.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="py-8 text-center text-xs text-slate-500 dark:text-slate-400">
            No proposal selected.
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-brand-600 dark:text-brand-400" />
            <CardTitle className="text-sm">Audit Trail &mdash; {proposalId}</CardTitle>
          </div>
          <Badge variant="navy" size="sm" className="font-mono">
            {data?.total_count || 0} AUDIT EVENTS
          </Badge>
        </div>
        <CardDescription className="text-xs">
          Cryptographically recorded actions from GET /api/v1/proposals/{proposalId}/audit
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="py-8 text-center text-xs text-slate-500 dark:text-slate-400">
            Loading immutable audit trail...
          </div>
        ) : isError || !data?.events?.length ? (
          <div className="py-6 text-center text-xs text-slate-500 dark:text-slate-400 space-y-1">
            <p>
              Zero audit events recorded for proposal <span className="font-mono font-semibold text-slate-700 dark:text-slate-300">{proposalId}</span>.
            </p>
            <p className="text-[11px] text-slate-400 max-w-md mx-auto leading-relaxed">
              Audit records are generated when an authorized reviewer signs off (Approve or Reject) in the Governance &amp; Approvals desk.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {data.events.map((evt) => {
              const isApprove = evt.action === 'APPROVE' || evt.decision === 'APPROVED';
              const isReject = evt.action === 'REJECT' || evt.decision === 'REJECTED';

              return (
                <div
                  key={evt.event_id}
                  className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 text-xs"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-1.5">
                    <div className="flex items-center gap-2">
                      {isApprove ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                      ) : isReject ? (
                        <XCircle className="w-4 h-4 text-rose-600 dark:text-rose-400" />
                      ) : (
                        <Clock className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                      )}
                      <span className="font-semibold text-slate-900 dark:text-slate-100">
                        {evt.action} {evt.entity_type}
                      </span>
                      {evt.decision && (
                        <Badge
                          variant={isApprove ? 'success' : isReject ? 'danger' : 'neutral'}
                          size="sm"
                        >
                          {evt.decision}
                        </Badge>
                      )}
                    </div>
                    <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                      {new Date(evt.timestamp).toLocaleString()}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-slate-600 dark:text-slate-400 mt-2 pt-2 border-t border-slate-200 dark:border-slate-700">
                    <div>
                      <span className="text-slate-400">Actor Identity:</span>{' '}
                      <span className="font-mono font-medium text-slate-800 dark:text-slate-200">
                        {evt.actor_id}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400">Event ID:</span>{' '}
                      <span className="font-mono text-slate-800 dark:text-slate-200 truncate">
                        {evt.event_id}
                      </span>
                    </div>
                  </div>

                  {evt.reason && (
                    <div className="mt-2 p-2 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-[11px] text-slate-700 dark:text-slate-300">
                      <span className="font-medium text-slate-500">Rationale:</span> {evt.reason}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
