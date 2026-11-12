import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { FinancialMetricCard } from '@/components/ui/FinancialMetricCard';
import { EmptyState } from '@/components/feedback/EmptyState';
import {
  DollarSign,
  Briefcase,
  AlertTriangle,
  ShieldCheck,
  Scale,
  FileText,
  Workflow,
  ArrowRight,
  Clock,
  PieChart,
  ShieldAlert,
  Activity,
  CheckCircle2,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export function DashboardPage() {
  const currentDate = new Intl.DateTimeFormat('en-US', {
    dateStyle: 'full',
  }).format(new Date());

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Operations Dashboard
            </h2>
            <Badge variant="navy" size="sm">
              PHASE 8.2 DUAL THEME
            </Badge>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Grounded Semantic Rebalancing &amp; Human Governance &bull; {currentDate}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link to="/rebalancing">
            <Button variant="primary" size="sm" leftIcon={<Scale className="w-4 h-4" />}>
              Open Rebalancing
            </Button>
          </Link>
          <Link to="/workflows">
            <Button variant="outline" size="sm" leftIcon={<Workflow className="w-4 h-4" />}>
              View Workflows
            </Button>
          </Link>
        </div>
      </div>

      {/* Architectural Notice: Strict No-Fake-Data Banner */}
      <Alert variant="info" title="Dual Theme Enterprise Architecture Active">
        The YottaFlex frontend features complete Light and Dark theme design tokens and dedicated interaction patterns for each business domain. In strict compliance with financial governance standards, all KPI cards below are displayed as labeled placeholders until live portfolio valuation and rebalancing endpoints are wired in subsequent subphases.
      </Alert>

      {/* Financial Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <FinancialMetricCard
          title="Total Managed AUM"
          value="$—.—"
          badgeText="Awaiting Valuation Feed"
          badgeVariant="neutral"
          subtitle="All asset classes"
          icon={<DollarSign className="w-4 h-4 text-brand-600 dark:text-brand-400" />}
          accentBorder="brand"
        />

        <FinancialMetricCard
          title="Active Portfolios"
          value="—"
          badgeText="Awaiting Portfolio Store"
          badgeVariant="neutral"
          subtitle="Institutional & Retail"
          icon={<Briefcase className="w-4 h-4 text-slate-600 dark:text-slate-400" />}
          accentBorder="neutral"
        />

        <FinancialMetricCard
          title="Corridor Drift Alerts"
          value="—"
          badgeText="Drift Engine Inactive"
          badgeVariant="warning"
          subtitle="&gt;5.0% threshold"
          icon={<AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />}
          accentBorder="warning"
        />

        <FinancialMetricCard
          title="Pending Approvals"
          value="—"
          badgeText="Governance Queue Idle"
          badgeVariant="neutral"
          subtitle="Human review required"
          icon={<ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />}
          accentBorder="success"
        />
      </div>

      {/* Main Content Two-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Portfolio Distribution Overview */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Asset Class &amp; Target Allocation Matrix</CardTitle>
                <CardDescription>
                  Multi-asset distribution (Equity, Fixed Income, Cash, Commodities)
                </CardDescription>
              </div>
              <Badge variant="neutral" size="sm">
                Placeholder
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Visual allocation comparison bar placeholder */}
            <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
              <div className="flex items-center justify-between text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">
                <span>Asset Allocation Benchmark Corridors</span>
                <span className="font-mono text-[11px]">4 Asset Classes</span>
              </div>
              <div className="h-3 w-full rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden flex">
                <div className="bg-brand-600 w-[60%]" title="Equity Target: 60%" />
                <div className="bg-emerald-600 w-[20%]" title="Fixed Income Target: 20%" />
                <div className="bg-cyan-600 w-[15%]" title="Cash Target: 15%" />
                <div className="bg-amber-600 w-[5%]" title="Commodities Target: 5%" />
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3 pt-3 border-t border-slate-200 dark:border-slate-700/60 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-sm bg-brand-600" />
                  <span className="text-slate-700 dark:text-slate-300">Equity (60%)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-sm bg-emerald-600" />
                  <span className="text-slate-700 dark:text-slate-300">Fixed Income (20%)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-sm bg-cyan-600" />
                  <span className="text-slate-700 dark:text-slate-300">Cash (15%)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-sm bg-amber-600" />
                  <span className="text-slate-700 dark:text-slate-300">Commodities (5%)</span>
                </div>
              </div>
            </div>

            <EmptyState
              icon={PieChart}
              title="Portfolio Valuation Module Pending"
              description="Visual drift corridor charts and asset allocation breakdowns will connect to GET /api/v1/portfolios/{id}/drift in Phase 8.2."
              action={
                <Link to="/portfolios">
                  <Button variant="outline" size="sm" rightIcon={<ArrowRight className="w-4 h-4" />}>
                    View Portfolio Specifications
                  </Button>
                </Link>
              }
            />
          </CardContent>
        </Card>

        {/* Right Col: System Safety & Governance Indicators */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Financial Safety Invariants</CardTitle>
              <CardDescription>
                Deterministic rules enforced across all execution stages
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-start gap-3 p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">Zero Holdings Mutation</div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">All recommendation outputs are staged as proposals.</div>
                </div>
              </div>

              <div className="flex items-start gap-3 p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                <ShieldAlert className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">Hard Constraint Gatekeeper</div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">Mandate violations trigger automated rejection.</div>
                </div>
              </div>

              <div className="flex items-start gap-3 p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                <Activity className="w-4 h-4 text-brand-600 dark:text-brand-400 shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">Deterministic Calculations</div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">The LLM explains policy citations; it never calculates.</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Core System Modules</CardTitle>
              <CardDescription>
                Quick navigation to specialized operational workspaces
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <Link
                to="/portfolios"
                className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 hover:border-slate-200 dark:hover:border-slate-700 hover:bg-slate-50/80 dark:hover:bg-slate-800/60 transition-all group"
              >
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 rounded bg-blue-50 dark:bg-blue-950/60 text-brand-600 dark:text-brand-400">
                    <Briefcase className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-xs font-medium text-slate-900 dark:text-slate-100">Portfolio Analytics</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-brand-600 transition-colors" />
              </Link>

              <Link
                to="/rebalancing"
                className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 hover:border-slate-200 dark:hover:border-slate-700 hover:bg-slate-50/80 dark:hover:bg-slate-800/60 transition-all group"
              >
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 rounded bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
                    <Scale className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-xs font-medium text-slate-900 dark:text-slate-100">Rebalancing Engine</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-600 transition-colors" />
              </Link>

              <Link
                to="/approvals"
                className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 hover:border-slate-200 dark:hover:border-slate-700 hover:bg-slate-50/80 dark:hover:bg-slate-800/60 transition-all group"
              >
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 rounded bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400">
                    <ShieldCheck className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-xs font-medium text-slate-900 dark:text-slate-100">Governance &amp; Approvals</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-emerald-600 transition-colors" />
              </Link>

              <Link
                to="/policies"
                className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 hover:border-slate-200 dark:hover:border-slate-700 hover:bg-slate-50/80 dark:hover:bg-slate-800/60 transition-all group"
              >
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 rounded bg-cyan-50 dark:bg-cyan-950/60 text-cyan-600 dark:text-cyan-400">
                    <FileText className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-xs font-medium text-slate-900 dark:text-slate-100">Policy RAG</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-cyan-600 transition-colors" />
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Recent Activity Table Placeholder */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Recent Governance Activity &amp; Audit Trail</CardTitle>
              <CardDescription>
                Chronological log of proposals, reviewer decisions, and audit events
              </CardDescription>
            </div>
            <Badge variant="neutral" size="sm">
              Live Feed Disabled
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={Clock}
            title="No Recent Audit Activity Recorded"
            description="The immutable audit trail will stream live records from GET /api/v1/proposals/{id}/audit when proposals are created and reviewed."
            action={
              <Link to="/approvals">
                <Button variant="outline" size="sm">
                  Explore Governance Rules
                </Button>
              </Link>
            }
          />
        </CardContent>
      </Card>
    </div>
  );
}
