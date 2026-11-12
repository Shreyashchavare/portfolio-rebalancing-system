import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useHealth } from '@/hooks/useHealth';
import { getApiBaseUrl } from '@/services/api/client';
import { SEEDED_PORTFOLIO_REFERENCES } from '@/features/portfolios/types/portfolio';
import {
  LayoutDashboard,
  Users,
  Database,
  AlertTriangle,
  Terminal,
  RotateCw,
  Briefcase,
  Scale,
  ShieldCheck,
  FileText,
  Workflow,
  ArrowRight,
  Shield,
  CheckCircle2,
  Lock,
  Cpu,
} from 'lucide-react';

export function AdminWorkspace() {
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'reference' | 'data-quality' | 'diagnostics'>('overview');
  const { data: health, isLoading: isHealthLoading, refetch: refetchHealth, isError: isHealthError } = useHealth();
  const apiBaseUrl = getApiBaseUrl() || '(Vite Reverse Proxy: /api & /health)';

  return (
    <div className="space-y-6">
      {/* Admin Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              System Administration &amp; Reference Console
            </h2>
            <Badge variant="danger" size="sm">
              ADMINISTRATIVE CONTROL
            </Badge>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Operational reference data oversight, data quality surveillance, and engine diagnostics.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchHealth()}
            isLoading={isHealthLoading}
            leftIcon={<RotateCw className="w-3.5 h-3.5" />}
          >
            Probe Health
          </Button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div role="tablist" aria-label="Admin Navigation" className="flex items-center gap-1.5 border-b border-slate-200 dark:border-slate-800 overflow-x-auto pb-px">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'overview'}
          onClick={() => setActiveTab('overview')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'overview'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <LayoutDashboard className="w-3.5 h-3.5" />
          <span>Overview</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'users'}
          onClick={() => setActiveTab('users')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'users'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>Users &amp; Roles</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'reference'}
          onClick={() => setActiveTab('reference')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'reference'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <Database className="w-3.5 h-3.5" />
          <span>Reference Data</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'data-quality'}
          onClick={() => setActiveTab('data-quality')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'data-quality'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>Data Quality</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'diagnostics'}
          onClick={() => setActiveTab('diagnostics')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'diagnostics'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <Terminal className="w-3.5 h-3.5" />
          <span>System Diagnostics</span>
        </button>
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Top Operational Status Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-4">
                <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">FastAPI Service Status</span>
                <div className="flex items-center gap-2">
                  {isHealthError || health?.status !== 'healthy' ? (
                    <Badge variant="warning">OFFLINE</Badge>
                  ) : (
                    <Badge variant="success">HEALTHY (200 OK)</Badge>
                  )}
                </div>
                <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 block">
                  Backend Router: /health
                </span>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">Authorization Enforcement</span>
                <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                  Strict Dual-Key Governance
                </div>
                <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 block">
                  Roles: ADMIN, REVIEWER, VIEWER
                </span>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">Institutional Custody</span>
                <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                  <span className="text-brand-600 dark:text-brand-400 font-bold">{SEEDED_PORTFOLIO_REFERENCES.length}</span> Portfolios Configured
                </div>
                <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 block">
                  Active Drift Surveillance
                </span>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">Semantic Policy RAG</span>
                <div className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5" /> FastEmbed ONNX
                </div>
                <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 block">
                  384-dim BGE Embeddings
                </span>
              </CardContent>
            </Card>
          </div>

          {/* Platform Operational Modules Launchpad */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <LayoutDashboard className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                    Platform Operational Modules
                  </CardTitle>
                  <CardDescription className="text-xs mt-0.5">
                    Direct access to portfolio analytics, optimization engines, and governance review desks.
                  </CardDescription>
                </div>
                <Badge variant="neutral" size="sm">5 Core Modules</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
                <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 hover:border-brand-500/50 transition-all flex flex-col justify-between group">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400">
                        <Briefcase className="w-4 h-4" />
                      </div>
                      <h4 className="text-xs font-semibold text-slate-900 dark:text-slate-100">Portfolios Directory</h4>
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed mb-3">
                      Multi-asset holdings, cash balances, historical price lookups, and allocation drift surveillance across all mandates.
                    </p>
                  </div>
                  <Link
                    to="/portfolios"
                    className="inline-flex items-center justify-between text-xs font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 pt-2 border-t border-slate-200/80 dark:border-slate-800/80"
                  >
                    <span>Launch Surveillance</span>
                    <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
                  </Link>
                </div>

                <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 hover:border-brand-500/50 transition-all flex flex-col justify-between group">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-900/50 text-emerald-600 dark:text-emerald-400">
                        <Scale className="w-4 h-4" />
                      </div>
                      <h4 className="text-xs font-semibold text-slate-900 dark:text-slate-100">Rebalancing Engine</h4>
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed mb-3">
                      Deterministic lot-sizing integer rounding, tiered broker fee schedules, minimum trade thresholds, and cash overdraft protection.
                    </p>
                  </div>
                  <Link
                    to="/rebalancing"
                    className="inline-flex items-center justify-between text-xs font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 pt-2 border-t border-slate-200/80 dark:border-slate-800/80"
                  >
                    <span>Open Calculation Stepper</span>
                    <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
                  </Link>
                </div>

                <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 hover:border-brand-500/50 transition-all flex flex-col justify-between group">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/50 text-purple-600 dark:text-purple-400">
                        <ShieldCheck className="w-4 h-4" />
                      </div>
                      <h4 className="text-xs font-semibold text-slate-900 dark:text-slate-100">Dual-Key Approvals</h4>
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed mb-3">
                      Mandatory human-in-the-loop review boundary, hard/soft constraint findings, rejection justification gate, and immutable audit logging.
                    </p>
                  </div>
                  <Link
                    to="/approvals"
                    className="inline-flex items-center justify-between text-xs font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 pt-2 border-t border-slate-200/80 dark:border-slate-800/80"
                  >
                    <span>Inspect Review Desk</span>
                    <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
                  </Link>
                </div>

                <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 hover:border-brand-500/50 transition-all flex flex-col justify-between group">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="p-2 rounded-lg bg-amber-100 dark:bg-amber-900/50 text-amber-600 dark:text-amber-400">
                        <FileText className="w-4 h-4" />
                      </div>
                      <h4 className="text-xs font-semibold text-slate-900 dark:text-slate-100">Policy Knowledgebase</h4>
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed mb-3">
                      Investment policy statements (IPS), ESG exclusion rules, FastEmbed vector embeddings, and temporal validity compliance filtering.
                    </p>
                  </div>
                  <Link
                    to="/policies"
                    className="inline-flex items-center justify-between text-xs font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 pt-2 border-t border-slate-200/80 dark:border-slate-800/80"
                  >
                    <span>Query Vector Store</span>
                    <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
                  </Link>
                </div>

                <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 hover:border-brand-500/50 transition-all flex flex-col justify-between group">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400">
                        <Workflow className="w-4 h-4" />
                      </div>
                      <h4 className="text-xs font-semibold text-slate-900 dark:text-slate-100">Workflow Orchestrator</h4>
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed mb-3">
                      8-stage deterministic state machine from proposal initiation through policy grounding to final human review gate.
                    </p>
                  </div>
                  <Link
                    to="/workflows"
                    className="inline-flex items-center justify-between text-xs font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 pt-2 border-t border-slate-200/80 dark:border-slate-800/80"
                  >
                    <span>View Orchestration State</span>
                    <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
                  </Link>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Inviolable Financial Invariants */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <CardTitle className="text-sm font-semibold">Core Architectural Invariants &amp; Security Guardrails</CardTitle>
              </div>
              <CardDescription className="text-xs">
                Inviolable principles enforced across the entire YottaFlex backend and client application.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 space-y-1">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    <span className="font-semibold text-slate-900 dark:text-slate-100">Mathematical Determinism</span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed pl-5.5">
                    Valuations, drift calculations, lot rounding, tiered fee schedules, and cash solvency verifications are calculated by pure Python algorithms. Generative LLMs are barred from calculating quantities.
                  </p>
                </div>

                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 space-y-1">
                  <div className="flex items-center gap-2">
                    <Lock className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
                    <span className="font-semibold text-slate-900 dark:text-slate-100">Zero Live Mutation Invariant</span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed pl-5.5">
                    Custodial holding records in PostgreSQL are strictly read-only during rebalancing. Trade proposals are staged for review; live execution occurs exclusively via broker gateways.
                  </p>
                </div>

                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 space-y-1">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400 shrink-0" />
                    <span className="font-semibold text-slate-900 dark:text-slate-100">Dual-Key Fiduciary Human Gate</span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed pl-5.5">
                    Algorithmic recommendations cannot be executed automatically. Authenticated human reviewer sign-off is mandatory. Hard constraint breaches permanently block proposal approval.
                  </p>
                </div>

                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 space-y-1">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
                    <span className="font-semibold text-slate-900 dark:text-slate-100">Grounded Semantic Retrieval</span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed pl-5.5">
                    Policy justifications are strictly cited from active investment mandates via FastEmbed ONNX vector embeddings. Temporal validity constraints ensure only in-effect policies are retrieved.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 2: Users & Roles */}
      {activeTab === 'users' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                <CardTitle className="text-sm">User &amp; Role Identity Management</CardTitle>
              </div>
              <CardDescription className="text-xs">
                Authentication, credentials, and role tiers recognized by the YottaFlex backend.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 rounded-xl border border-blue-200 dark:border-blue-900/60 bg-blue-50/70 dark:bg-blue-950/30 text-xs text-blue-950 dark:text-blue-200 leading-relaxed">
                <span className="font-bold block mb-1">Authoritative Identity Governance Note:</span>
                In strict compliance with institutional security architecture, YottaFlex does not store raw passwords or provide standalone user-creation forms. Identity authentication and role mapping are provided via enterprise OAuth2/OIDC single sign-on (SSO) and HTTP Bearer tokens.
              </div>

              <div className="space-y-2">
                <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 flex items-center justify-between text-xs">
                  <div>
                    <span className="font-semibold text-slate-900 dark:text-slate-100 block">ADMIN</span>
                    <span className="text-slate-500 dark:text-slate-400">Full administrative and override authority</span>
                  </div>
                  <Badge variant="danger" size="sm">AUTHORITATIVE</Badge>
                </div>

                <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 flex items-center justify-between text-xs">
                  <div>
                    <span className="font-semibold text-slate-900 dark:text-slate-100 block">REVIEWER</span>
                    <span className="text-slate-500 dark:text-slate-400">Governance sign-off and proposal approval authority</span>
                  </div>
                  <Badge variant="brand" size="sm">AUTHORITATIVE</Badge>
                </div>

                <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 flex items-center justify-between text-xs">
                  <div>
                    <span className="font-semibold text-slate-900 dark:text-slate-100 block">VIEWER</span>
                    <span className="text-slate-500 dark:text-slate-400">Read-only monitoring; mutations return HTTP 403 Forbidden</span>
                  </div>
                  <Badge variant="neutral" size="sm">READ-ONLY</Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 3: Reference Data */}
      {activeTab === 'reference' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                <CardTitle className="text-sm">Reference Data Architecture</CardTitle>
              </div>
              <CardDescription className="text-xs">
                Authoritative financial models persisted in PostgreSQL 17 / SQLAlchemy 2.x.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <span className="font-bold text-slate-900 dark:text-slate-100 block mb-0.5">Instrument Catalog</span>
                  <span className="text-slate-500 dark:text-slate-400">Multi-asset securities across Equity, Fixed Income, Cash, and Commodities.</span>
                </div>

                <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <span className="font-bold text-slate-900 dark:text-slate-100 block mb-0.5">Fee Tier Schedules</span>
                  <span className="text-slate-500 dark:text-slate-400">Deterministic lot-size and percentage-tier transaction cost model.</span>
                </div>

                <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <span className="font-bold text-slate-900 dark:text-slate-100 block mb-0.5">Target Allocation Profiles</span>
                  <span className="text-slate-500 dark:text-slate-400">Investor benchmark corridor weights summing strictly to 100%.</span>
                </div>

                <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <span className="font-bold text-slate-900 dark:text-slate-100 block mb-0.5">Policy Constraint Rules</span>
                  <span className="text-slate-500 dark:text-slate-400">Mandate gatekeeper: Cash Floor, Single Asset Concentration, Turnover limits.</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 4: Data Quality */}
      {activeTab === 'data-quality' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                <CardTitle className="text-sm">Price Staleness &amp; Integrity Controls</CardTitle>
              </div>
              <CardDescription className="text-xs">
                Financial safety constraints governing market price timestamps.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 space-y-1">
                <span className="font-semibold text-slate-900 dark:text-slate-100 block">
                  Deterministic Price Age Threshold
                </span>
                <p className="text-slate-500 dark:text-slate-400 text-[11px] leading-relaxed">
                  The valuation service computes <span className="font-mono">price_age_days = (as_of_date - price_date).days</span>. Any price exceeding the configured staleness tolerance is flagged with diagnostics. Missing prices abort proposal execution with HTTP 422 Unprocessable Content.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 5: System Diagnostics */}
      {activeTab === 'diagnostics' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                <CardTitle className="text-sm">FastAPI Backend Telemetry</CardTitle>
              </div>
              <CardDescription className="text-xs">
                Live connectivity diagnostics to root health and reverse proxy endpoints.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-xs">
                <span className="text-slate-600 dark:text-slate-400">Endpoint Health Check</span>
                {isHealthLoading ? (
                  <Badge variant="neutral">CHECKING...</Badge>
                ) : isHealthError || health?.status !== 'healthy' ? (
                  <Badge variant="warning">OFFLINE</Badge>
                ) : (
                  <Badge variant="success">HEALTHY (200 OK)</Badge>
                )}
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-xs">
                <span className="text-slate-600 dark:text-slate-400">Resolved Base URL</span>
                <span className="font-mono bg-white dark:bg-slate-900 px-2 py-0.5 rounded border border-slate-200 dark:border-slate-700">
                  {apiBaseUrl}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
