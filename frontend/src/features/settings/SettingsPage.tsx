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
  Server,
  KeyRound,
  RotateCw,
  CheckCircle2,
  AlertTriangle,
  Sliders,
  Sun,
  Moon,
  Laptop,
  Check,
  Palette,
  Layers,
} from 'lucide-react';

export function SettingsPage() {
  const { theme, resolvedTheme, setTheme } = useTheme();
  const { token, reviewer, activeMockToken, selectMockToken, isDevelopment } = useAuth();
  const { data: healthData, isLoading: isHealthLoading, refetch: refetchHealth, isError: isHealthError } = useHealth();
  const [tableDensity, setTableDensity] = useState<'normal' | 'compact'>('normal');

  const apiBaseUrl = getApiBaseUrl() || '(Vite Reverse Proxy: /api & /health)';

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
              PREFERENCES &amp; DIAGNOSTICS
            </Badge>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Appearance themes, backend connectivity, reviewer identity, and application workstation preferences.
          </p>
        </div>
      </div>

      {/* Configuration Group 1: Appearance & Dual Theme System */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Palette className="w-4 h-4 text-brand-600 dark:text-brand-400" />
            <CardTitle>Appearance &amp; Dual Theme Design System</CardTitle>
          </div>
          <CardDescription>
            Choose between Light, Dark, or automatic System theme synchronization. Preference persists across browser sessions.
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
                    <span>Active Theme:</span>
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

      {/* Two Column Grid: API Connectivity & Reviewer RBAC */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Configuration Group 2: Backend API Connectivity */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                <CardTitle>Backend Service Connection</CardTitle>
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
              FastAPI status check via GET /health
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
              <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Environment Tier</span>
              <Badge variant="brand">{import.meta.env.MODE.toUpperCase()}</Badge>
            </div>
          </CardContent>
        </Card>

        {/* Configuration Group 3: Account & Reviewer RBAC Information */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <KeyRound className="w-4 h-4 text-brand-600 dark:text-brand-400" />
              <CardTitle>Governance Reviewer Identity</CardTitle>
            </div>
            <CardDescription>
              Bearer token attached to governance and workflow endpoints
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
              <span className="text-xs font-medium text-slate-600 dark:text-slate-400 block mb-1">Raw Token</span>
              <div className="text-[11px] font-mono text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-900 p-2 rounded border border-slate-200 dark:border-slate-700 break-all select-all">
                {token || '(No token configured)'}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Dev Mock Auth Switcher Card */}
      {isDevelopment ? (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <CardTitle>Development Mock Authentication Selector</CardTitle>
            </div>
            <CardDescription>
              Switch between preconfigured mock tokens matching backend ENABLE_DEV_MOCK_AUTH=true
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
                        ? 'border-brand-600 dark:border-brand-500 bg-blue-50/60 dark:bg-blue-950/40 ring-2 ring-brand-500/20'
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
                  </button>
                );
              })}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {/* Configuration Group 4: Application Workstation Preferences */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-brand-600 dark:text-brand-400" />
            <CardTitle>Application Workstation Preferences</CardTitle>
          </div>
          <CardDescription>
            Financial table display density and workstation parameters
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-900 dark:text-slate-100 block">Table Display Density</span>
                <span className="text-[11px] text-slate-500 dark:text-slate-400">Controls vertical padding in financial grids</span>
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

            <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-900 dark:text-slate-100 block">Currency Precision</span>
                <span className="text-[11px] text-slate-500 dark:text-slate-400">Strict 4-decimal precision on unit prices</span>
              </div>
              <Badge variant="brand" size="sm" className="font-mono">
                4 DECIMALS
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
