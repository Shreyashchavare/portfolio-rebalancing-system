import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { DataTable, type Column } from '@/components/ui/DataTable';
import { workflowService } from '@/services/api/workflowService';
import { approvalService } from '@/services/api/approvalService';
import { SEEDED_PORTFOLIO_REFERENCES } from '@/features/portfolios/types/portfolio';
import { useProposal, useApproveProposal } from '@/hooks/useApprovals';
import { useAuth } from '@/hooks/useAuth';
import type { WorkflowResponse } from '@/types/orchestration';
import {
  CheckCircle2,
  Clock,
  Play,
  Briefcase,
  ExternalLink,
  XCircle,
  RotateCw,
  UserCheck,
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface WorkflowRunItem {
  workflowId: string;
  portfolioId: string;
  status: string;
  requestKey: string;
  proposalId: string | null;
  startedAt: string;
  completedAt: string;
}

const INITIAL_WORKFLOWS: WorkflowRunItem[] = [
  {
    workflowId: 'WF-20260115-A1B2C3D4',
    portfolioId: 'PORT-INV-000001-02',
    status: 'PENDING_HUMAN_REVIEW',
    requestKey: 'wf-req-20260115-001',
    proposalId: 'RB-2026-000002',
    startedAt: '2026-01-15T10:00:00Z',
    completedAt: '2026-01-15T10:00:05Z',
  },
];

const LIFECYCLE_STAGES = [
  { id: 'RECEIVED', label: '1. Received', stageKey: 'RECEIVED' },
  { id: 'VALIDATING', label: '2. Validating', stageKey: 'VALIDATING' },
  { id: 'ANALYZING', label: '3. Drift Analysis', stageKey: 'ANALYZING' },
  { id: 'GENERATING_PROPOSAL', label: '4. Proposal & Fees', stageKey: 'GENERATING_PROPOSAL' },
  { id: 'RETRIEVING_POLICIES', label: '5. FastEmbed RAG', stageKey: 'RETRIEVING_POLICIES' },
  { id: 'GENERATING_EXPLANATION', label: '6. Grounded Summary', stageKey: 'GENERATING_EXPLANATION' },
  { id: 'PENDING_HUMAN_REVIEW', label: '7. Human Review', stageKey: 'PENDING_HUMAN_REVIEW' },
];

export function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<WorkflowRunItem[]>(INITIAL_WORKFLOWS);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState('PORT-INV-000001-02');
  const [activeWorkflow, setActiveWorkflow] = useState<WorkflowResponse | null>(null);
  const [isInitiating, setIsInitiating] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const activeProposalId =
    activeWorkflow?.proposal_id ||
    activeWorkflow?.proposal?.proposal_id ||
    workflows[0]?.proposalId;

  const { data: proposalData, refetch: refetchProposal } = useProposal(activeProposalId || undefined);

  const effectiveStatus = proposalData?.status
    ? proposalData.status === 'APPROVED'
      ? 'APPROVED'
      : proposalData.status === 'REJECTED'
      ? 'REJECTED'
      : 'PENDING_HUMAN_REVIEW'
    : activeWorkflow?.status || workflows[0]?.status;

  const isCompleted = effectiveStatus === 'APPROVED' || effectiveStatus === 'COMPLETED';
  const isRejected = effectiveStatus === 'REJECTED';
  const isHalted = effectiveStatus === 'PENDING_HUMAN_REVIEW';

  const { canApprove, setPersona, isDevelopment } = useAuth();
  const approveMutation = useApproveProposal();

  const handleDirectApprove = async () => {
    if (!activeProposalId) return;
    try {
      await approveMutation.mutateAsync({
        proposalId: activeProposalId,
        payload: { notes: 'Approved directly from Workflow Orchestration console.' },
      });
      refetchProposal();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Approval failed';
      setActionError(msg);
    }
  };

  const handleResetProposal = async () => {
    if (!activeProposalId) return;
    try {
      await approvalService.resetProposal(activeProposalId);
      refetchProposal();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Reset failed';
      setActionError(msg);
    }
  };

  const handleInitiateWorkflow = async () => {
    setIsInitiating(true);
    setActionError(null);
    try {
      const response = await workflowService.initiateWorkflow({
        portfolio_id: selectedPortfolioId,
        as_of_date: '2026-01-15',
        request_key: `wf-req-${Date.now()}`,
      });
      setActiveWorkflow(response);

      // Prepend to run list
      const newRun: WorkflowRunItem = {
        workflowId: response.workflow_id,
        portfolioId: response.portfolio_id,
        status: response.status,
        requestKey: response.request_key,
        proposalId: response.proposal_id || response.proposal?.proposal_id || null,
        startedAt: response.started_at || new Date().toISOString(),
        completedAt: response.completed_at || new Date().toISOString(),
      };
      setWorkflows((prev) => [newRun, ...prev]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Workflow initiation failed';
      setActionError(msg);
    } finally {
      setIsInitiating(false);
    }
  };

  const columns: Column<WorkflowRunItem>[] = [
    {
      key: 'workflowId',
      header: 'Workflow Run ID',
      render: (item) => (
        <span className="font-mono font-semibold text-slate-900 dark:text-slate-100">
          {item.workflowId}
        </span>
      ),
    },
    {
      key: 'portfolioId',
      header: 'Target Portfolio',
      render: (item) => <span className="font-mono text-xs">{item.portfolioId}</span>,
    },
    {
      key: 'status',
      header: 'Lifecycle Status',
      render: (item) => (
        <Badge
          variant={
            item.status === 'PENDING_HUMAN_REVIEW'
              ? 'warning'
              : item.status === 'COMPLETED'
              ? 'success'
              : item.status === 'FAILED'
              ? 'danger'
              : 'brand'
          }
          size="sm"
        >
          {item.status}
        </Badge>
      ),
    },
    {
      key: 'requestKey',
      header: 'Idempotency Key',
      render: (item) => (
        <span className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
          {item.requestKey}
        </span>
      ),
    },
    {
      key: 'proposalId',
      header: 'Generated Proposal',
      render: (item) =>
        item.proposalId ? (
          <Link
            to="/approvals"
            className="font-mono text-xs text-brand-600 dark:text-brand-400 hover:underline inline-flex items-center gap-1"
          >
            <span>{item.proposalId}</span>
            <ExternalLink className="w-3 h-3" />
          </Link>
        ) : (
          <span className="text-slate-400 text-xs">&mdash;</span>
        ),
    },
    {
      key: 'completedAt',
      header: 'Execution Time',
      render: () => <span className="font-mono text-[11px] text-slate-500">Live Completed</span>,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Workflow Orchestration &amp; State Monitoring
            </h2>
            <Badge variant="brand" size="sm">
              AGENTIC STATE MACHINE
            </Badge>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            End-to-end pipeline coordination, idempotency guards, and human review gating.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Portfolio quick select */}
          <div className="flex items-center gap-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg px-2.5 py-1 text-xs">
            <Briefcase className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedPortfolioId}
              onChange={(e) => setSelectedPortfolioId(e.target.value)}
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
            variant="primary"
            size="sm"
            onClick={handleInitiateWorkflow}
            isLoading={isInitiating}
            leftIcon={<Play className="w-3.5 h-3.5" />}
          >
            Initiate Workflow
          </Button>
        </div>
      </div>

      {/* Idempotency Notice */}
      <Alert variant="info" title="Deterministic State Machine &amp; Idempotency Protection">
        Proposal generation is executed <strong>at most once</strong> per request key. Identical request hashes return the cached workflow run with full proposal, simulation, and grounded policy citations.
      </Alert>

      {/* Action Error if Mutation Fails */}
      {actionError && (
        <Alert variant="error" title="Workflow Initiation Error">
          {actionError}
        </Alert>
      )}

      {/* Active Run Success Feedback */}
      {activeWorkflow && (
        <div className="p-4 rounded-xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/70 dark:bg-emerald-950/30 space-y-2">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span className="text-xs font-bold text-emerald-950 dark:text-emerald-100">
                Workflow {activeWorkflow.workflow_id} Transitioned to {activeWorkflow.status}
              </span>
            </div>
            <span className="font-mono text-[11px] text-emerald-700 dark:text-emerald-300">
              Request Key: {activeWorkflow.request_key}
            </span>
          </div>

          {activeWorkflow.explanation?.summary && (
            <p className="text-xs text-emerald-900 dark:text-emerald-200 font-sans leading-relaxed">
              <strong>Grounded Rationale:</strong> {activeWorkflow.explanation.summary}
            </p>
          )}

          {activeWorkflow.proposal_id && (
            <div className="pt-2 border-t border-emerald-200 dark:border-emerald-800/80 flex items-center justify-between text-xs">
              <span className="text-emerald-800 dark:text-emerald-300">
                Staged Proposal: <strong>{activeWorkflow.proposal_id}</strong>
              </span>
              <Link
                to="/approvals"
                className="font-medium text-emerald-800 dark:text-emerald-300 hover:underline flex items-center gap-1"
              >
                <span>Open in Governance Queue</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </Link>
            </div>
          )}
        </div>
      )}

      {/* Visual State Transition Pipeline Stepper */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Execution State Machine Transition Pipeline</CardTitle>
              <CardDescription>
                Live stage progress for execution run {activeWorkflow?.workflow_id || workflows[0]?.workflowId}
              </CardDescription>
            </div>
            <Badge
              variant={isCompleted ? 'success' : isRejected ? 'danger' : 'warning'}
              size="sm"
            >
              {isCompleted
                ? 'PIPELINE COMPLETED'
                : isRejected
                ? 'PROPOSAL REJECTED'
                : 'HALTED AT REVIEW GATE'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
            {LIFECYCLE_STAGES.map((stage, idx) => {
              const isPastStage = idx < 6;
              const isStage7 = idx === 6;

              const stagePassed = isPastStage || (isStage7 && isCompleted);
              const stageFailed = isStage7 && isRejected;
              const stagePending = isStage7 && isHalted;

              return (
                <div
                  key={stage.id}
                  className={`p-2.5 rounded-lg border text-xs transition-all ${
                    stagePending
                      ? 'border-amber-500 bg-amber-50/50 dark:bg-amber-950/30 ring-2 ring-amber-500/20'
                      : stagePassed
                      ? 'border-emerald-200 dark:border-emerald-800/60 bg-emerald-50/40 dark:bg-emerald-950/20'
                      : stageFailed
                      ? 'border-rose-200 dark:border-rose-900/60 bg-rose-50/40 dark:bg-rose-950/20'
                      : 'border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-[10px] text-slate-400">0{idx + 1}</span>
                    {stagePassed ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                    ) : stagePending ? (
                      <Clock className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 animate-pulse" />
                    ) : stageFailed ? (
                      <XCircle className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />
                    ) : null}
                  </div>
                  <div className="font-semibold text-slate-900 dark:text-slate-100 text-[11px] truncate">
                    {stage.label}
                  </div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-1 capitalize font-mono">
                    {stagePending
                      ? 'Pending Review'
                      : stagePassed
                      ? isStage7
                        ? 'Approved'
                        : 'Passed'
                      : stageFailed
                      ? 'Rejected'
                      : 'Pending'}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Interactive Gating / Completion Bar */}
          {isHalted && activeProposalId && (
            <div className="mt-4 p-3.5 rounded-lg border border-amber-200 dark:border-amber-900/60 bg-amber-50/70 dark:bg-amber-950/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 text-amber-950 dark:text-amber-200">
                <Clock className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 animate-pulse" />
                <span>
                  Stage 7 Gating: Fiduciary human signoff required for proposal{' '}
                  <strong className="font-mono">{activeProposalId}</strong>. Institutional policy halts execution until approved.
                </span>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                {canApprove ? (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleDirectApprove}
                    isLoading={approveMutation.isPending}
                    leftIcon={<CheckCircle2 className="w-3.5 h-3.5" />}
                  >
                    Approve Proposal &amp; Complete Workflow
                  </Button>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-amber-800 dark:text-amber-300 font-medium">
                      Requires Reviewer / Admin role to sign off
                    </span>
                    {isDevelopment && (
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => setPersona('COMPLIANCE')}
                        leftIcon={<UserCheck className="w-3.5 h-3.5" />}
                      >
                        Switch to Reviewer to Approve
                      </Button>
                    )}
                  </div>
                )}
                <Link to="/approvals">
                  <Button variant="outline" size="sm" rightIcon={<ExternalLink className="w-3.5 h-3.5" />}>
                    Open Approvals Desk
                  </Button>
                </Link>
              </div>
            </div>
          )}

          {isCompleted && activeProposalId && (
            <div className="mt-4 p-3 rounded-lg border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/70 dark:bg-emerald-950/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 text-emerald-950 dark:text-emerald-200">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span>
                  Stage 7 Completed: Proposal <strong className="font-mono">{activeProposalId}</strong> was approved. Execution pipeline has concluded and audit log recorded.
                </span>
              </div>
              <div className="flex items-center gap-2">
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
                <Link
                  to="/approvals"
                  className="font-medium text-emerald-700 dark:text-emerald-400 hover:underline flex items-center gap-1"
                >
                  <span>View Fiduciary Audit Decision</span>
                  <ExternalLink className="w-3 h-3" />
                </Link>
              </div>
            </div>
          )}

          {isRejected && activeProposalId && (
            <div className="mt-4 p-3 rounded-lg border border-rose-200 dark:border-rose-900/60 bg-rose-50/70 dark:bg-rose-950/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 text-rose-950 dark:text-rose-200">
                <XCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
                <span>
                  Stage 7 Terminal: Proposal <strong className="font-mono">{activeProposalId}</strong> was rejected by compliance. Rebalancing execution halted.
                </span>
              </div>
              <div className="flex items-center gap-2">
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
                <Link
                  to="/approvals"
                  className="font-medium text-rose-700 dark:text-rose-400 hover:underline flex items-center gap-1"
                >
                  <span>View Rejection Audit</span>
                  <ExternalLink className="w-3 h-3" />
                </Link>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Workflow Run History Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Recent Workflow Runs</CardTitle>
              <CardDescription>
                Historical execution records, idempotency keys, and output linkages
              </CardDescription>
            </div>
            <Badge variant="navy" size="sm">
              {workflows.length} {workflows.length === 1 ? 'Run' : 'Runs'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={workflows}
            keyExtractor={(item) => item.workflowId}
          />
        </CardContent>
      </Card>
    </div>
  );
}
