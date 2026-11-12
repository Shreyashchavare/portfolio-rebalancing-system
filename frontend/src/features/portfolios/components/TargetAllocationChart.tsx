import { useMemo } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { portfolioService } from '../services/portfolioService';
import type { PortfolioDriftResult } from '../types/portfolio';
import { Sliders } from 'lucide-react';

interface TargetAllocationChartProps {
  drifts: PortfolioDriftResult['drifts'];
  rebalanceTrigger?: PortfolioDriftResult['rebalance_trigger'];
}

export function TargetAllocationChart({ drifts, rebalanceTrigger }: TargetAllocationChartProps) {
  const chartData = useMemo(() => {
    return portfolioService.formatTargetComparisonData(drifts);
  }, [drifts]);

  if (chartData.length === 0) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle>Target vs Actual Allocation</CardTitle>
          <CardDescription>Mandate target weights compared against current market allocation</CardDescription>
        </CardHeader>
        <CardContent className="h-64 flex flex-col items-center justify-center text-slate-400">
          <Sliders className="w-10 h-10 mb-2 opacity-30" />
          <p className="text-xs">No target allocation mandate configured for this portfolio</p>
        </CardContent>
      </Card>
    );
  }

  const isTriggered = rebalanceTrigger?.status === 'TRIGGERED';

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Target vs Actual Allocation</CardTitle>
            <CardDescription>
              Mandate target weights compared against actual weights
            </CardDescription>
          </div>
          <Badge variant={isTriggered ? 'warning' : 'success'} size="sm">
            {isTriggered ? 'CORRIDOR BREACH' : 'IN TOLERANCE'}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col justify-between space-y-4">
        {/* Horizontal Grouped Bar Chart */}
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%" minWidth={100} minHeight={200}>
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 5, right: 20, left: 55, bottom: 5 }}
            >
              <XAxis
                type="number"
                domain={[0, 100]}
                unit="%"
                tick={{ fontSize: 11, fill: '#94A3B8' }}
                stroke="#64748B"
              />
              <YAxis
                type="category"
                dataKey="assetClass"
                tick={{ fontSize: 11, fill: '#94A3B8' }}
                stroke="#64748B"
              />
              <Tooltip
                content={({ active, payload }) => {
                  const actualItem = payload?.[0];
                  const targetItem = payload?.[1];
                  if (active && actualItem && targetItem && actualItem.payload) {
                    const actual = actualItem.value as number;
                    const target = targetItem.value as number;
                    const diff = (actual - target).toFixed(2);
                    const item = actualItem.payload;
                    return (
                      <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 p-2.5 shadow-lg backdrop-blur text-xs">
                        <div className="font-semibold text-slate-900 dark:text-slate-100 mb-1">
                          {item.assetClass}
                        </div>
                        <div className="text-brand-600 dark:text-brand-400 font-mono">
                          Actual: {actual.toFixed(2)}%
                        </div>
                        <div className="text-slate-500 dark:text-slate-400 font-mono">
                          Target: {target.toFixed(2)}%
                        </div>
                        <div
                          className={`font-mono font-semibold text-[11px] mt-1 pt-1 border-t border-slate-200 dark:border-slate-800 ${
                            Number(diff) > 0
                              ? 'text-rose-600 dark:text-rose-400'
                              : Number(diff) < 0
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-slate-600'
                          }`}
                        >
                          Drift: {Number(diff) > 0 ? `+${diff}` : diff} pp ({item.actionSignal})
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, paddingTop: 10 }}
                iconType="circle"
              />
              <Bar
                dataKey="actualWeight"
                name="Actual Weight %"
                fill="#2563EB"
                radius={[0, 4, 4, 0]}
              />
              <Bar
                dataKey="targetWeight"
                name="Target Weight %"
                fill="#94A3B8"
                radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Drift Summary Pills */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
          {chartData.map((item) => {
            const isOverweight = item.driftPp > 0;
            const isZero = item.driftPp === 0;
            return (
              <div
                key={item.assetClass}
                className="p-2 rounded border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-900/40 text-xs"
              >
                <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono truncate">
                  {item.assetClass}
                </div>
                <div className="flex items-center justify-between mt-1">
                  <span
                    className={`font-mono font-bold text-xs ${
                      isOverweight
                        ? 'text-rose-600 dark:text-rose-400'
                        : !isZero
                        ? 'text-brand-600 dark:text-brand-400'
                        : 'text-slate-600 dark:text-slate-300'
                    }`}
                  >
                    {item.driftPp > 0 ? `+${item.driftPp.toFixed(2)}` : item.driftPp.toFixed(2)} pp
                  </span>
                  <Badge
                    variant={
                      item.actionSignal === 'SELL'
                        ? 'danger'
                        : item.actionSignal === 'BUY'
                        ? 'brand'
                        : 'neutral'
                    }
                    size="sm"
                    className="text-[9px] px-1 py-0"
                  >
                    {item.actionSignal}
                  </Badge>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
