import { type ReactNode } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/utils';

export interface FinancialMetricCardProps {
  title: string;
  value: string;
  subtitle?: string;
  badgeText?: string;
  badgeVariant?: 'neutral' | 'brand' | 'success' | 'warning' | 'danger' | 'navy';
  icon?: ReactNode;
  accentBorder?: 'brand' | 'neutral' | 'warning' | 'success' | 'danger';
  className?: string;
}

export function FinancialMetricCard({
  title,
  value,
  subtitle,
  badgeText,
  badgeVariant = 'neutral',
  icon,
  accentBorder = 'brand',
  className,
}: FinancialMetricCardProps) {
  const accentStyles = {
    brand: 'border-l-4 border-l-brand-600 dark:border-l-brand-500',
    neutral: 'border-l-4 border-l-slate-400 dark:border-l-slate-600',
    warning: 'border-l-4 border-l-amber-500 dark:border-l-amber-500',
    success: 'border-l-4 border-l-emerald-600 dark:border-l-emerald-500',
    danger: 'border-l-4 border-l-rose-600 dark:border-l-rose-500',
  };

  return (
    <Card className={cn(accentStyles[accentBorder], className)}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            {title}
          </span>
          {icon && (
            <div className="p-1.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              {icon}
            </div>
          )}
        </div>

        <div className="mt-2 text-2xl font-bold font-mono tracking-tight text-slate-900 dark:text-slate-100">
          {value}
        </div>

        <div className="mt-2 flex items-center justify-between gap-2">
          {badgeText && (
            <Badge variant={badgeVariant} size="sm" className="text-[10px]">
              {badgeText}
            </Badge>
          )}
          {subtitle && (
            <span className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
              {subtitle}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
