import { useState, useMemo } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { formatCurrency, formatPercent } from '@/lib/utils';
import { portfolioService } from '../services/portfolioService';
import type { PortfolioValuationResult } from '../types/portfolio';
import { PieChart as PieChartIcon } from 'lucide-react';

interface AssetAllocationChartProps {
  assetClasses: PortfolioValuationResult['asset_classes'];
  totalMarketValue: string;
}

export function AssetAllocationChart({ assetClasses, totalMarketValue }: AssetAllocationChartProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const chartData = useMemo(() => {
    return portfolioService.formatAllocationChartData(assetClasses);
  }, [assetClasses]);

  const totalNum = parseFloat(totalMarketValue) || 0;

  if (chartData.length === 0) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle>Asset Allocation Breakdown</CardTitle>
          <CardDescription>Current market value distribution across asset classes</CardDescription>
        </CardHeader>
        <CardContent className="h-64 flex flex-col items-center justify-center text-slate-400">
          <PieChartIcon className="w-10 h-10 mb-2 opacity-30" />
          <p className="text-xs">No active asset class allocations recorded</p>
        </CardContent>
      </Card>
    );
  }

  const selectedItem = activeIndex !== null ? chartData[activeIndex] : null;

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Asset Class Allocation</CardTitle>
            <CardDescription>Current market value distribution across asset classes</CardDescription>
          </div>
          <Badge variant="brand" size="sm">
            {chartData.length} Classes
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col justify-between">
        <div className="relative h-64 w-full flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%" minWidth={100} minHeight={200}>
            <PieChart>
              <Tooltip
                content={({ active, payload }) => {
                  const entry = payload?.[0];
                  if (active && entry?.payload) {
                    const data = entry.payload;
                    return (
                      <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 p-2.5 shadow-lg backdrop-blur text-xs">
                        <div className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 mb-1">
                          <span
                            className="w-2.5 h-2.5 rounded-full inline-block"
                            style={{ backgroundColor: data.color }}
                          />
                          <span>{data.name}</span>
                        </div>
                        <div className="text-slate-600 dark:text-slate-300 font-mono">
                          Value: {formatCurrency(data.value)}
                        </div>
                        <div className="text-slate-500 dark:text-slate-400 font-mono text-[11px]">
                          Weight: {formatPercent(data.weight)}
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Pie
                data={chartData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={65}
                outerRadius={95}
                paddingAngle={3}
                onMouseEnter={(_, index) => setActiveIndex(index)}
                onMouseLeave={() => setActiveIndex(null)}
              >
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.color}
                    stroke="transparent"
                    className="transition-all duration-200 cursor-pointer"
                    opacity={activeIndex === null || activeIndex === index ? 1 : 0.6}
                  />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>

          {/* Center Donut Label */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
            {selectedItem ? (
              <>
                <span className="text-[10px] uppercase tracking-wider text-slate-400 font-mono">
                  {selectedItem.name}
                </span>
                <span className="text-sm font-bold text-slate-900 dark:text-slate-100 font-mono">
                  {formatPercent(selectedItem.weight)}
                </span>
                <span className="text-[10px] text-slate-500 font-mono">
                  {formatCurrency(selectedItem.value)}
                </span>
              </>
            ) : (
              <>
                <span className="text-[10px] uppercase tracking-wider text-slate-400 font-mono">
                  Total Market Value
                </span>
                <span className="text-sm font-bold text-slate-900 dark:text-slate-100 font-mono">
                  {formatCurrency(totalNum)}
                </span>
                <span className="text-[10px] text-slate-500 font-mono">100.00%</span>
              </>
            )}
          </div>
        </div>

        {/* Custom Legend */}
        <div className="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-slate-100 dark:border-slate-800">
          {chartData.map((item, index) => (
            <div
              key={item.name}
              onMouseEnter={() => setActiveIndex(index)}
              onMouseLeave={() => setActiveIndex(null)}
              className={`flex items-center justify-between p-1.5 rounded cursor-pointer transition-colors text-xs ${
                activeIndex === index
                  ? 'bg-slate-100 dark:bg-slate-800'
                  : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
              }`}
            >
              <div className="flex items-center gap-1.5 min-w-0">
                <span
                  className="w-2.5 h-2.5 rounded-sm shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <span className="truncate text-slate-700 dark:text-slate-300 text-[11px] font-medium">
                  {item.name}
                </span>
              </div>
              <div className="text-right shrink-0 font-mono text-[11px] font-semibold text-slate-900 dark:text-slate-100">
                {formatPercent(item.weight)}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
