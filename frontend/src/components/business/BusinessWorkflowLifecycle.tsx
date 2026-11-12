import {
  Briefcase,
  PieChart,
  TrendingDown,
  Scale,
  Activity,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Clock,
  History,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/utils';

export type WorkflowStage =
  | 'portfolio_selected'
  | 'holdings_evaluated'
  | 'drift_calculated'
  | 'recommendation_generated'
  | 'trades_simulated'
  | 'compliance_reviewed'
  | 'decision_rendered'
  | 'audit_logged';

interface BusinessWorkflowLifecycleProps {
  currentStage?: WorkflowStage;
  proposalStatus?: 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED' | 'DRAFT' | null;
  portfolioId?: string;
  proposalId?: string | null;
  className?: string;
}

export function BusinessWorkflowLifecycle({
  currentStage = 'holdings_evaluated',
  proposalStatus = null,
  portfolioId = 'PORT-INV-000001-02',
  proposalId = null,
  className,
}: BusinessWorkflowLifecycleProps) {
  const stages: {
    id: WorkflowStage;
    number: number;
    title: string;
    description: string;
    icon: typeof Briefcase;
    apiEndpoint: string;
  }[] = [
    {
      id: 'portfolio_selected',
      number: 1,
      title: 'Portfolio Selection',
      description: portfolioId,
      icon: Briefcase,
      apiEndpoint: 'PORTFOLIO_ID',
    },
    {
      id: 'holdings_evaluated',
      number: 2,
      title: 'Holdings & Targets',
      description: 'Valuation & asset classes',
      icon: PieChart,
      apiEndpoint: 'GET /valuation',
    },
    {
      id: 'drift_calculated',
      number: 3,
      title: 'Drift Calculation',
      description: 'Corridor threshold evaluation',
      icon: TrendingDown,
      apiEndpoint: 'GET /drift',
    },
    {
      id: 'recommendation_generated',
      number: 4,
      title: 'Recommendation',
      description: 'Deterministic orders',
      icon: Scale,
      apiEndpoint: 'POST /proposals',
    },
    {
      id: 'trades_simulated',
      number: 5,
      title: 'Trade Simulation',
      description: 'In-memory post-trade state',
      icon: Activity,
      apiEndpoint: 'SimulatedAllocations',
    },
    {
      id: 'compliance_reviewed',
      number: 6,
      title: 'Compliance Review',
      description: 'IPS policy constraints',
      icon: ShieldCheck,
      apiEndpoint: 'POST /policies/ask',
    },
    {
      id: 'decision_rendered',
      number: 7,
      title: 'Approval / Rejection',
      description: proposalStatus ? proposalStatus : 'Dual-key governance',
      icon: proposalStatus === 'APPROVED' ? CheckCircle2 : proposalStatus === 'REJECTED' ? XCircle : Clock,
      apiEndpoint: 'POST /approve | reject',
    },
    {
      id: 'audit_logged',
      number: 8,
      title: 'Audit Traceability',
      description: proposalId ? `${proposalId}` : 'Immutable event log',
      icon: History,
      apiEndpoint: 'GET /proposals/{id}/audit',
    },
  ];

  const getStageIndex = (stageId: WorkflowStage) => stages.findIndex((s) => s.id === stageId);
  const activeIdx = getStageIndex(currentStage);

  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardHeader className="pb-3 border-b border-slate-100 dark:border-slate-800">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <Scale className="w-4 h-4 text-brand-600 dark:text-brand-400" />
              <CardTitle className="text-sm">Central Rebalancing Lifecycle</CardTitle>
            </div>
            <CardDescription className="text-xs">
              Deterministic 8-stage pipeline from portfolio drift detection to immutable audit trail.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="brand" size="sm" className="font-mono">
              STAGE {activeIdx + 1} OF 8
            </Badge>
            {proposalStatus && (
              <Badge
                variant={proposalStatus === 'APPROVED' ? 'success' : proposalStatus === 'REJECTED' ? 'danger' : 'warning'}
                size="sm"
              >
                {proposalStatus}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        {/* Horizontal Stepper Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
          {stages.map((stage, idx) => {
            const Icon = stage.icon;
            const isCompleted = idx < activeIdx || (idx === 6 && proposalStatus === 'APPROVED');
            const isCurrent = idx === activeIdx;

            return (
              <div
                key={stage.id}
                className={cn(
                  'p-2.5 rounded-lg border text-left transition-all relative flex flex-col justify-between min-h-[92px]',
                  isCurrent
                    ? 'border-brand-500 bg-blue-50/70 dark:bg-blue-950/40 ring-1 ring-brand-500/30'
                    : isCompleted
                    ? 'border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/40 dark:bg-emerald-950/20'
                    : 'border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 opacity-70'
                )}
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span
                      className={cn(
                        'text-[10px] font-mono font-bold px-1.5 py-0.2 rounded',
                        isCurrent
                          ? 'bg-brand-600 text-white'
                          : isCompleted
                          ? 'bg-emerald-600 text-white'
                          : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                      )}
                    >
                      {stage.number}
                    </span>
                    <Icon
                      className={cn(
                        'w-3.5 h-3.5',
                        isCurrent
                          ? 'text-brand-600 dark:text-brand-400'
                          : isCompleted
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-slate-400'
                      )}
                    />
                  </div>
                  <div className="text-[11px] font-semibold text-slate-900 dark:text-slate-100 leading-tight">
                    {stage.title}
                  </div>
                </div>

                <div className="mt-2 pt-1.5 border-t border-slate-200/60 dark:border-slate-800/80">
                  <div className="text-[9px] font-mono text-slate-500 dark:text-slate-400 truncate">
                    {stage.apiEndpoint}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
