import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Alert } from '@/components/ui/Alert';
import { DataTable, type Column } from '@/components/ui/DataTable';
import { formatCurrency, formatPercent } from '@/lib/utils';
import type { PortfolioDriftResult, AssetClassDrift } from '../types/portfolio';
import { AlertTriangle, CheckCircle2, Info, Compass } from 'lucide-react';

interface DriftAnalysisProps {
  driftData?: PortfolioDriftResult;
}

export function DriftAnalysis({ driftData }: DriftAnalysisProps) {
  if (!driftData || driftData.drifts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Allocation Drift &amp; Rebalance Corridor Evaluation</CardTitle>
          <CardDescription>Target corridor threshold analysis</CardDescription>
        </CardHeader>
        <CardContent className="h-32 flex flex-col items-center justify-center text-slate-400">
          <Compass className="w-8 h-8 mb-2 opacity-30" />
          <p className="text-xs">No drift metrics available for this portfolio</p>
        </CardContent>
      </Card>
    );
  }

  const { drifts, rebalance_trigger: trigger } = driftData;
  const isTriggered = trigger?.status === 'TRIGGERED';
  const triggeredClassesSet = new Set(trigger?.triggered_asset_classes || []);

  const columns: Column<AssetClassDrift>[] = [
    {
      key: 'asset_class',
      header: 'Asset Class',
      render: (item) => (
        <div className="flex items-center gap-2">
          <span className="font-semibold text-xs text-slate-900 dark:text-slate-100">
            {item.asset_class}
          </span>
          {triggeredClassesSet.has(item.asset_class) && (
            <Badge variant="warning" size="sm" className="text-[10px] px-1 py-0">
              CORRIDOR
            </Badge>
          )}
        </div>
      ),
    },
    {
      key: 'current_market_value',
      header: 'Current Value',
      render: (item) => (
        <span className="font-mono text-xs text-slate-800 dark:text-slate-200">
          {formatCurrency(parseFloat(item.current_market_value) || 0)}
        </span>
      ),
    },
    {
      key: 'target_market_value',
      header: 'Target Value',
      render: (item) => (
        <span className="font-mono text-xs text-slate-600 dark:text-slate-400">
          {formatCurrency(parseFloat(item.target_market_value) || 0)}
        </span>
      ),
    },
    {
      key: 'current_weight',
      header: 'Actual Weight',
      render: (item) => (
        <span className="font-mono text-xs text-slate-900 dark:text-slate-100 font-semibold">
          {formatPercent(parseFloat(item.current_weight) || 0)}
        </span>
      ),
    },
    {
      key: 'target_weight',
      header: 'Target Weight',
      render: (item) => (
        <span className="font-mono text-xs text-slate-500 dark:text-slate-400">
          {formatPercent(parseFloat(item.target_weight) || 0)}
        </span>
      ),
    },
    {
      key: 'percentage_drift',
      header: 'Weight Drift (pp)',
      render: (item) => {
        const drift = parseFloat(item.percentage_drift) || 0;
        const isPositive = drift > 0;
        const isZero = drift === 0;
        return (
          <span
            className={`font-mono text-xs font-bold ${
              isPositive
                ? 'text-rose-600 dark:text-rose-400'
                : !isZero
                ? 'text-brand-600 dark:text-brand-400'
                : 'text-slate-500'
            }`}
          >
            {isPositive ? `+${drift.toFixed(2)}` : drift.toFixed(2)} pp
          </span>
        );
      },
    },
    {
      key: 'monetary_drift',
      header: 'Dollar Drift',
      render: (item) => {
        const val = parseFloat(item.monetary_drift) || 0;
        const isPositive = val > 0;
        return (
          <span
            className={`font-mono text-xs ${
              isPositive
                ? 'text-rose-600 dark:text-rose-400'
                : val < 0
                ? 'text-emerald-600 dark:text-emerald-400'
                : 'text-slate-500'
            }`}
          >
            {isPositive ? `+${formatCurrency(val)}` : formatCurrency(val)}
          </span>
        );
      },
    },
    {
      key: 'action_signal',
      header: 'Action Signal',
      render: (item) => (
        <Badge
          variant={
            item.action_signal === 'SELL'
              ? 'danger'
              : item.action_signal === 'BUY'
              ? 'brand'
              : 'neutral'
          }
          size="sm"
        >
          {item.action_signal || 'HOLD'}
        </Badge>
      ),
    },
  ];

  return (
    <Card className="space-y-4">
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <CardTitle>Asset Class Allocation Drift Analysis</CardTitle>
            <CardDescription>
              Deterministic drift calculations against mandate corridor thresholds
            </CardDescription>
          </div>
          <Badge variant={isTriggered ? 'warning' : 'success'} size="sm">
            {trigger?.status || 'STATUS PENDING'}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Rebalance Corridor Alert */}
        {trigger && (
          <div>
            {isTriggered ? (
              <Alert variant="warning" title="Rebalance Corridor Triggered">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <div className="text-xs">
                    <div>{trigger.policy_description || 'Corridor threshold breached.'}</div>
                    {trigger.triggered_asset_classes.length > 0 && (
                      <div className="mt-1 font-mono text-[11px] text-amber-700 dark:text-amber-300">
                        Breaching asset classes: {trigger.triggered_asset_classes.join(', ')}
                      </div>
                    )}
                  </div>
                </div>
              </Alert>
            ) : trigger.status === 'NOT_TRIGGERED' ? (
              <Alert variant="success" title="Within Policy Corridors">
                <div className="flex items-center gap-2 text-xs">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>
                    All asset-class weight deviations remain within permitted mandate thresholds.
                    No rebalance action required.
                  </span>
                </div>
              </Alert>
            ) : (
              <Alert variant="info" title="Rebalance Policy Status">
                <div className="flex items-center gap-2 text-xs">
                  <Info className="w-4 h-4 text-blue-600 shrink-0" />
                  <span>{trigger.policy_description || 'No corridor policy configured.'}</span>
                </div>
              </Alert>
            )}
          </div>
        )}

        {/* Drift Table */}
        <DataTable
          columns={columns}
          data={drifts}
          keyExtractor={(item) => item.asset_class}
        />
      </CardContent>
    </Card>
  );
}

