import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { DataTable, type Column } from '@/components/ui/DataTable';
import {
  CheckCircle2,
  Clock,
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface WorkflowRunItem {
  workflowId: string;
  portfolioId: string;
  status: 'PENDING_HUMAN_REVIEW' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  requestKey: string;
  proposalId: string;
  startedAt: string;
  completedAt: string;
}

const SAMPLE_WORKFLOWS: WorkflowRunItem[] = [
  {
    workflowId: 'WF-20260115-A1B2C3D4',
    portfolioId: 'PORT-INV-000001-01',
    status: 'PENDING_HUMAN_REVIEW',
    requestKey: 'wf-req-20260115-001',
    proposalId: 'RB-20260115-000001',
    startedAt: '2026-01-15T10:00:00Z',
    completedAt: '2026-01-15T10:00:05Z',
  },
];

const LIFECYCLE_STAGES = [
  { id: 'RECEIVED', label: '1. Received', status: 'completed' },
  { id: 'VALIDATING', label: '2. Validating', status: 'completed' },
  { id: 'ANALYZING', label: '3. Drift Analysis', status: 'completed' },
  { id: 'GENERATING_PROPOSAL', label: '4. Proposal & Fees', status: 'completed' },
  { id: 'RETRIEVING_POLICIES', label: '5. FastEmbed RAG', status: 'completed' },
  { id: 'GENERATING_EXPLANATION', label: '6. Grounded Summary', status: 'completed' },
  { id: 'PENDING_HUMAN_REVIEW', label: '7. Human Review', status: 'active' },
];

export function WorkflowsPage() {
  const [selectedWorkflow] = useState(SAMPLE_WORKFLOWS[0]);

  const columns: Column<WorkflowRunItem>[] = [
    {
      key: 'workflowId',
      header: 'Workflow Run ID',
      render: (item) => <span className="font-mono font-semibold text-slate-900 dark:text-slate-100">{item.workflowId}</span>,
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
          variant={item.status === 'PENDING_HUMAN_REVIEW' ? 'warning' : item.status === 'COMPLETED' ? 'success' : 'neutral'}
          size="sm"
        >
          {item.status}
        </Badge>
      ),
    },
    {
      key: 'requestKey',
      header: 'Idempotency Key',
      render: (item) => <span className="font-mono text-[11px] text-slate-500">{item.requestKey}</span>,
    },
    {
      key: 'proposalId',
      header: 'Generated Proposal',
      render: (item) => (
        <Link to="/approvals" className="font-mono text-xs text-brand-600 dark:text-brand-400 hover:underline">
          {item.proposalId}
        </Link>
      ),
    },
    {
      key: 'completedAt',
      header: 'Execution Time',
      render: () => <span className="font-mono text-[11px] text-slate-500">5.0s</span>,
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

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" leftIcon={<Clock className="w-3.5 h-3.5" />}>
            Auto-Refresh: 5s
          </Button>
        </div>
      </div>

      {/* Idempotency Notice */}
      <Alert variant="info" title="Deterministic State Machine &amp; Idempotency Protection">
        Proposal generation is executed <strong>at most once</strong> per request key. Identical request hashes return the cached workflow run with full proposal, simulation, and grounded policy citations.
      </Alert>

      {/* Visual State Transition Pipeline Stepper */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Execution State Machine Transition Pipeline</CardTitle>
              <CardDescription>
                Live stage progress for execution run {selectedWorkflow?.workflowId}
              </CardDescription>
            </div>
            <Badge variant="warning" size="sm">
              HALTED AT REVIEW GATE
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
            {LIFECYCLE_STAGES.map((stage, idx) => {
              const isCompleted = stage.status === 'completed';
              const isActive = stage.status === 'active';

              return (
                <div
                  key={stage.id}
                  className={`p-2.5 rounded-lg border text-xs transition-all ${
                    isActive
                      ? 'border-amber-500 bg-amber-50/50 dark:bg-amber-950/30 ring-2 ring-amber-500/20'
                      : isCompleted
                      ? 'border-emerald-200 dark:border-emerald-800/60 bg-emerald-50/40 dark:bg-emerald-950/20'
                      : 'border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-[10px] text-slate-400">0{idx + 1}</span>
                    {isCompleted ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                    ) : isActive ? (
                      <Clock className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 animate-pulse" />
                    ) : null}
                  </div>
                  <div className="font-semibold text-slate-900 dark:text-slate-100 text-[11px] truncate">
                    {stage.label}
                  </div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-1 capitalize font-mono">
                    {isActive ? 'Pending Review' : 'Passed'}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Workflow Run History Table */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Workflow Runs</CardTitle>
          <CardDescription>
            Historical execution records, idempotency keys, and output linkages
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={SAMPLE_WORKFLOWS}
            keyExtractor={(item) => item.workflowId}
          />
        </CardContent>
      </Card>
    </div>
  );
}
