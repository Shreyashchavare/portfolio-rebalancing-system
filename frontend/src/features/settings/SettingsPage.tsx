import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/hooks/useAuth';
import { useHealth } from '@/hooks/useHealth';
import { useTheme } from '@/hooks/useTheme';
import { getApiBaseUrl } from '@/services/api/client';
import { DEV_MOCK_TOKENS } from '@/types/auth';
import { THEME_OPTIONS } from '@/types/theme';
import {
  Palette,
  UserCheck,
  Bell,
  ShieldCheck,
  Info,
  Terminal,
  Sun,
  Moon,
  Laptop,
  Check,
  RotateCw,
  CheckCircle2,
  AlertTriangle,
  Lock,
  Layers,
  Sliders,
  ExternalLink,
  ShieldAlert,
} from 'lucide-react';

type SettingsTab = 'appearance' | 'profile' | 'notifications' | 'security' | 'about' | 'diagnostics';

export function SettingsPage() {
  const { theme, resolvedTheme, setTheme } = useTheme();
  const { reviewer, activeMockToken, selectMockToken, isDevelopment } = useAuth();
  const { data: healthData, isLoading: isHealthLoading, refetch: refetchHealth, isError: isHealthError } = useHealth();
  const [activeTab, setActiveTab] = useState<SettingsTab>('appearance');
  const [tableDensity, setTableDensity] = useState<'normal' | 'compact'>('normal');

  const apiBaseUrl = getApiBaseUrl() || '(Vite Reverse Proxy: /api & /health)';
  const isDiagnosticsAuthorized = isDevelopment || reviewer?.role === 'ADMIN';

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              System Settings &amp; Configuration
            </h2>
            <Badge variant="navy" size="sm">
              INSTITUTIONAL PREFERENCES
            </Badge>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Personal display preferences, account profile, security verification, and platform information.
          </p>
        </div>

        {/* Workstation Badge */}
        <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Fiduciary Workstation</span>
          <Badge variant="neutral" size="sm" className="font-mono">
            {reviewer?.role || 'VIEWER'}
          </Badge>
        </div>
      </div>

      {/* Settings Navigation Tabs */}
      <div
        role="tablist"
        aria-label="Settings Categories"
        className="flex items-center gap-1.5 border-b border-slate-200 dark:border-slate-800 overflow-x-auto pb-px"
      >
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'appearance'}
          id="tab-appearance"
          onClick={() => setActiveTab('appearance')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'appearance'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <Palette className="w-3.5 h-3.5" />
          <span>Appearance</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'profile'}
          id="tab-profile"
          onClick={() => setActiveTab('profile')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'profile'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <UserCheck className="w-3.5 h-3.5" />
          <span>Profile</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'notifications'}
          id="tab-notifications"
          onClick={() => setActiveTab('notifications')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'notifications'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <Bell className="w-3.5 h-3.5" />
          <span>Notifications</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'security'}
          id="tab-security"
          onClick={() => setActiveTab('security')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'security'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Security &amp; Sessions</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'about'}
          id="tab-about"
          onClick={() => setActiveTab('about')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ${
            activeTab === 'about'
              ? 'border-brand-600 text-brand-700 dark:text-brand-400 dark:border-brand-400 bg-white dark:bg-slate-900 shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }`}
        >
          <Info className="w-3.5 h-3.5" />
          <span>About &amp; Support</span>
        </button>

        {/* Development or Admin Diagnostic Tab */}
        {isDiagnosticsAuthorized && (
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'diagnostics'}
            id="tab-diagnostics"
            onClick={() => setActiveTab('diagnostics')}
            className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium rounded-t-lg transition-colors border-b-2 -mb-px whitespace-nowrap ml-auto ${
              activeTab === 'diagnostics'
                ? 'border-indigo-600 text-indigo-700 dark:text-indigo-400 dark:border-indigo-400 bg-white dark:bg-slate-900 shadow-sm'
                : 'border-transparent text-slate-500 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-slate-50 dark:hover:bg-slate-800/50'
            }`}
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>System Diagnostics</span>
            <Badge variant="brand" size="sm" className="text-[9px] py-0 px-1 font-mono">
              {isDevelopment ? 'DEV' : 'ADMIN'}
            </Badge>
          </button>
        )}
      </div>

      {/* Tab 1: Appearance */}
      {activeTab === 'appearance' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Palette className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                <CardTitle>Display Theme</CardTitle>
              </div>
              <CardDescription>
                Customize your visual environment. Preferences persist across browser sessions.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
                {THEME_OPTIONS.map((option) => {
                  const isSelected = theme === option.value;
                  const Icon =
                    option.value === 'light'
                      ? Sun
                      : option.value === 'dark'
                      ? Moon
                      : Laptop;

                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setTheme(option.value)}
                      className={`p-4 rounded-xl border text-left transition-all relative ${
                        isSelected
                          ? 'border-brand-600 dark:border-brand-500 bg-blue-50/70 dark:bg-blue-950/40 ring-2 ring-brand-500/20 shadow-sm'
                          : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className="p-1.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200">
                            <Icon className="w-4 h-4" />
                          </div>
                          <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                            {option.label}
                          </span>
                        </div>
                        {isSelected && (
                          <Check className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                        )}
                      </div>

                      <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                        {option.description}
                      </p>

                      <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[10px] font-mono text-slate-400">
                        <span>Active Mode:</span>
                        <span className="font-semibold capitalize text-slate-700 dark:text-slate-300">
                          {option.value === 'system' ? `System (${resolvedTheme})` : option.value}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                <CardTitle>Workstation Grid Density</CardTitle>
              </div>
              <CardDescription>
                Configure layout density for financial tables and portfolio position grids.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-slate-900 dark:text-slate-100 block">
                      Table Vertical Density
                    </span>
                    <span className="text-[11px] text-slate-500 dark:text-slate-400">
                      Standard padding vs high-density financial compact view
                    </span>
                  </div>
                  <div className="flex items-center border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden text-xs">
                    <button
                      type="button"
                      onClick={() => setTableDensity('normal')}
                      className={`px-3 py-1.5 transition-colors ${
                        tableDensity === 'normal'
                          ? 'bg-slate-200 dark:bg-slate-700 font-semibold text-slate-900 dark:text-slate-100'
                          : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'
                      }`}
                    >
                      Normal
                    </button>
                    <button
                      type="button"
                      onClick={() => setTableDensity('compact')}
                      className={`px-3 py-1.5 transition-colors ${
                        tableDensity === 'compact'
                          ? 'bg-slate-200 dark:bg-slate-700 font-semibold text-slate-900 dark:text-slate-100'
                          : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'
                      }`}
                    >
                      Compact
                    </button>
                  </div>
                </div>

                <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-slate-900 dark:text-slate-100 block">
                      Unit Price Precision
                    </span>
                    <span className="text-[11px] text-slate-500 dark:text-slate-400">
                      Fixed institutional precision for securities
                    </span>
                  </div>
                  <Badge variant="brand" size="sm" className="font-mono">
                    4 DECIMAL PLACES
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 2: Profile */}
      {activeTab === 'profile' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                <CardTitle>Account &amp; Institutional Identity</CardTitle>
              </div>
              <CardDescription>
                Identity and role details authenticated via your enterprise credentials.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400 block mb-1">
                    Reviewer Identifier
                  </span>
                  <span className="text-sm font-mono font-bold text-slate-900 dark:text-slate-100">
                    {reviewer?.reviewer_id || 'institutional-user'}
                  </span>
                </div>

                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400 block mb-1">
                    Institutional Email
                  </span>
                  <span className="text-sm font-mono text-slate-900 dark:text-slate-100">
                    {reviewer?.email || 'user@yottaflex.institutional'}
                  </span>
                </div>

                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400 block mb-1">
                    Assigned Governance Role
                  </span>
                  <div className="flex items-center gap-2 mt-0.5">
                    <Badge variant={reviewer?.role === 'ADMIN' ? 'danger' : reviewer?.role === 'VIEWER' ? 'neutral' : 'brand'}>
                      {reviewer?.role || 'ANONYMOUS'}
                    </Badge>
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                      {reviewer?.role === 'ADMIN'
                        ? 'Full administrative and override authority'
                        : reviewer?.role === 'REVIEWER'
                        ? 'Authorized for proposal approval & rejection workflows'
                        : reviewer?.role === 'PORTFOLIO_MANAGER'
                        ? 'Authorized for proposal generation & execution'
                        : 'Read-only fiduciary monitoring access'}
                    </span>
                  </div>
                </div>

                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400 block mb-1">
                    Organization Unit
                  </span>
                  <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    Institutional Wealth &amp; Asset Management
                  </span>
                </div>
              </div>

              <div className="p-3.5 rounded-lg border border-blue-200 dark:border-blue-900/60 bg-blue-50/60 dark:bg-blue-950/20 text-xs text-blue-900 dark:text-blue-300">
                <span className="font-semibold block mb-0.5">Enterprise Directory Notice:</span>
                Your user profile attributes and role assignments are governed centrally by corporate Single Sign-On (SSO) and Directory Services. To request role adjustments or update personnel information, contact your compliance compliance administrator.
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 3: Notifications */}
      {activeTab === 'notifications' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Bell className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                <CardTitle>Notification Channels &amp; Governance Alerts</CardTitle>
              </div>
              <CardDescription>
                Fiduciary event dispatching and compliance monitoring policies.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 flex items-start justify-between gap-4">
                  <div>
                    <span className="text-xs font-semibold text-slate-900 dark:text-slate-100 block">
                      Rebalancing Approval Requests
                    </span>
                    <span className="text-[11px] text-slate-500 dark:text-slate-400">
                      Dispatched when proposals exceed threshold drift or breach cash constraints.
                    </span>
                  </div>
                  <Badge variant="success" size="sm">
                    ALWAYS ACTIVE (AUDIT)
                  </Badge>
                </div>

                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 flex items-start justify-between gap-4">
                  <div>
                    <span className="text-xs font-semibold text-slate-900 dark:text-slate-100 block">
                      Compliance Policy Violations
                    </span>
                    <span className="text-[11px] text-slate-500 dark:text-slate-400">
                      Immediate alert on trade rule violations, restricted list matches, or max asset allocation breaches.
                    </span>
                  </div>
                  <Badge variant="success" size="sm">
                    ALWAYS ACTIVE (AUDIT)
                  </Badge>
                </div>

                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 flex items-start justify-between gap-4">
                  <div>
                    <span className="text-xs font-semibold text-slate-900 dark:text-slate-100 block">
                      Portfolio Valuation Stale Warnings
                    </span>
                    <span className="text-[11px] text-slate-500 dark:text-slate-400">
                      Flagged when underlying security pricing exceeds max staleness tolerance (e.g. &gt; 1 trading day).
                    </span>
                  </div>
                  <Badge variant="brand" size="sm">
                    AUTOMATIC
                  </Badge>
                </div>
              </div>

              <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-100/70 dark:bg-slate-800/40 text-xs text-slate-600 dark:text-slate-400">
                <span className="font-semibold text-slate-900 dark:text-slate-100 block mb-0.5">Fiduciary Policy Enforcement:</span>
                In accordance with regulatory audit standards, compliance alerts and approval workflows cannot be disabled or muted by individual operators. Notifications are routed directly to registered compliance inboxes and recorded in immutable audit logs.
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 4: Security & Sessions */}
      {activeTab === 'security' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Lock className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                <CardTitle>Session Security &amp; Access Controls</CardTitle>
              </div>
              <CardDescription>
                Safe session verification and backend authentication status.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400 block mb-1">
                    Session Status
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500" />
                    <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                      Active Authenticated Session
                    </span>
                  </div>
                </div>

                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400 block mb-1">
                    Authentication Protocol
                  </span>
                  <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                    HTTP Authorization Bearer Token
                  </span>
                </div>

                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400 block mb-1">
                    Credential Protection
                  </span>
                  <span className="text-xs font-mono text-slate-600 dark:text-slate-400">
                    Bearer •••••••••••••••• (Protected Session)
                  </span>
                </div>

                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400 block mb-1">
                    Backend Token Verification
                  </span>
                  <div className="flex items-center gap-1.5 text-xs text-slate-700 dark:text-slate-300">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                    <span>Backend Verified (FastAPI Security Dependencies)</span>
                  </div>
                </div>
              </div>

              <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-100/70 dark:bg-slate-800/40 text-xs text-slate-600 dark:text-slate-400">
                <span className="font-semibold text-slate-900 dark:text-slate-100 block mb-0.5">Password &amp; MFA Management:</span>
                Institutional credentials, multi-factor hardware keys (FIDO2/WebAuthn), and session timeouts are managed through your enterprise identity provider. To revoke active sessions or report security anomalies, contact Information Security Operations.
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 5: About & Support */}
      {activeTab === 'about' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                <CardTitle>About YottaFlex Portfolio Rebalancing System</CardTitle>
              </div>
              <CardDescription>
                Architecture specifications, regulatory compliance, and support channels.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400 block mb-1">
                    Application Release
                  </span>
                  <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    YottaFlex Workstation v0.1.0
                  </span>
                </div>

                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400 block mb-1">
                    Rebalancing Engine
                  </span>
                  <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    Deterministic Constraint Solver
                  </span>
                </div>

                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400 block mb-1">
                    Governance Standard
                  </span>
                  <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    Mandatory Dual-Key Human-in-the-Loop
                  </span>
                </div>

                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400 block mb-1">
                    Policy Intelligence
                  </span>
                  <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    FastEmbed Vector Retrieval (ONNX)
                  </span>
                </div>
              </div>

              <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                <span className="font-semibold text-slate-900 dark:text-slate-100 block mb-1">
                  Regulatory Compliance &amp; Fiduciary Responsibility:
                </span>
                The YottaFlex Portfolio Rebalancing System is an institutional-grade portfolio optimization platform. Automated trade proposals are subject to rigorous constraint verification (cash floor, turnover caps, single-asset concentration limits). Every executed trade order is permanently immutably logged in accordance with fiduciary compliance policies.
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 text-xs text-slate-500 dark:text-slate-400 border-t border-slate-200 dark:border-slate-800">
                <span>&copy; {new Date().getFullYear()} YottaFlex Systems Inc. All rights reserved.</span>
                <div className="flex items-center gap-4">
                  <span className="inline-flex items-center gap-1 hover:text-slate-900 dark:hover:text-slate-200 cursor-pointer">
                    <span>Documentation</span>
                    <ExternalLink className="w-3 h-3" />
                  </span>
                  <span className="inline-flex items-center gap-1 hover:text-slate-900 dark:hover:text-slate-200 cursor-pointer">
                    <span>Institutional Support</span>
                    <ExternalLink className="w-3 h-3" />
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 6: System Diagnostics (Admin / Development Authorized Only) */}
      {activeTab === 'diagnostics' && (
        <>
          {isDiagnosticsAuthorized ? (
            <div className="space-y-6">
              {/* Security Banner: Confidential Area */}
              <div className="p-4 rounded-xl border border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/70 dark:bg-indigo-950/30 flex items-start gap-3">
                <Terminal className="w-5 h-5 text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-bold text-indigo-950 dark:text-indigo-200">
                    Administrative Technical Diagnostics Area
                  </h4>
                  <p className="text-[11px] text-indigo-800 dark:text-indigo-300 mt-0.5">
                    This console is reserved strictly for development verification and authorized administrative oversight. Raw credentials remain encrypted and masked at all times.
                  </p>
                </div>
              </div>

              {/* Two Column Grid: API Health & Masked Identity */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <RotateCw className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                        <CardTitle>FastAPI Service Connectivity</CardTitle>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => refetchHealth()}
                        isLoading={isHealthLoading}
                        leftIcon={<RotateCw className="w-3.5 h-3.5" />}
                      >
                        Ping Health
                      </Button>
                    </div>
                    <CardDescription>
                      Real-time backend probe to GET /health
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
                      <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Operational Status</span>
                      {isHealthLoading ? (
                        <Badge variant="neutral">CHECKING...</Badge>
                      ) : isHealthError || healthData?.status !== 'healthy' ? (
                        <Badge variant="warning" className="gap-1">
                          <AlertTriangle className="w-3 h-3 text-amber-600 dark:text-amber-400" />
                          <span>OFFLINE / UNREACHABLE</span>
                        </Badge>
                      ) : (
                        <Badge variant="success" className="gap-1">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                          <span>HEALTHY (200 OK)</span>
                        </Badge>
                      )}
                    </div>

                    <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
                      <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Configured Base URL</span>
                      <span className="text-xs font-mono text-slate-800 dark:text-slate-200 bg-white dark:bg-slate-900 px-2 py-0.5 rounded border border-slate-200 dark:border-slate-700">
                        {apiBaseUrl}
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
                      <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Runtime Environment</span>
                      <Badge variant="brand">{import.meta.env.MODE.toUpperCase()}</Badge>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                      <CardTitle>Active Authorization Context</CardTitle>
                    </div>
                    <CardDescription>
                      Reviewer verification and credential security parameters
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
                      <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Reviewer ID</span>
                      <span className="text-xs font-mono font-semibold text-slate-900 dark:text-slate-100">
                        {reviewer?.reviewer_id || 'None'}
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
                      <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Assigned Role</span>
                      <Badge variant={reviewer?.role === 'ADMIN' ? 'danger' : reviewer?.role === 'VIEWER' ? 'neutral' : 'brand'}>
                        {reviewer?.role || 'ANONYMOUS'}
                      </Badge>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
                      <span className="text-xs font-medium text-slate-600 dark:text-slate-400 block mb-1">
                        Credential Status (Protected Masking)
                      </span>
                      <div className="text-[11px] font-mono text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-900 p-2 rounded border border-slate-200 dark:border-slate-700">
                        Bearer •••••••••••••••• (Protected Session)
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Development Persona Switcher */}
              {isDevelopment && (
                <Card>
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <Sliders className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                      <CardTitle>Development Persona Switcher</CardTitle>
                    </div>
                    <CardDescription>
                      Switch roles to simulate different authorization levels against local backend endpoints.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {DEV_MOCK_TOKENS.map((mock) => {
                        const isSelected = activeMockToken?.token === mock.token;
                        return (
                          <button
                            key={mock.token}
                            type="button"
                            onClick={() => selectMockToken(mock.token)}
                            className={`p-4 rounded-lg border text-left transition-all ${
                              isSelected
                                ? 'border-indigo-600 dark:border-indigo-500 bg-indigo-50/60 dark:bg-indigo-950/40 ring-2 ring-indigo-500/20'
                                : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                                {mock.label}
                              </span>
                              <Badge variant={mock.role === 'ADMIN' ? 'danger' : mock.role === 'VIEWER' ? 'neutral' : 'brand'}>
                                {mock.role}
                              </Badge>
                            </div>
                            <div className="text-[11px] font-mono text-slate-600 dark:text-slate-400 mt-1">
                              ID: {mock.reviewerId}
                            </div>
                            <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-2">
                              {mock.description}
                            </p>
                            <div className="mt-3 pt-2 border-t border-slate-100 dark:border-slate-800 text-[10px] font-mono text-slate-400">
                              Credential: Bearer ••••••••
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <Card>
              <CardContent className="py-12 text-center space-y-3">
                <ShieldAlert className="w-10 h-10 text-amber-500 mx-auto" />
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  Access Restricted
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                  System Diagnostics is restricted to authorized platform administrators and development environments. Your current role ({reviewer?.role || 'VIEWER'}) does not permit viewing internal diagnostic telemetry.
                </p>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
