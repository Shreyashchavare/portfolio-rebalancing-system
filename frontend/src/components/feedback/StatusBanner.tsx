import { useHealth } from '@/hooks/useHealth';
import { Badge } from '@/components/ui/Badge';
import { Activity, AlertCircle, CheckCircle2 } from 'lucide-react';

export function StatusBanner() {
  const { data, isLoading, isError } = useHealth();

  if (isLoading) {
    return (
      <Badge variant="neutral" className="gap-1.5 font-mono text-[11px]">
        <Activity className="w-3 h-3 animate-spin text-slate-400 dark:text-slate-500" />
        <span>CONNECTING...</span>
      </Badge>
    );
  }

  if (isError || data?.status !== 'healthy') {
    return (
      <Badge variant="warning" className="gap-1.5 font-mono text-[11px]" title="FastAPI backend offline or unreachable">
        <AlertCircle className="w-3 h-3 text-amber-600 dark:text-amber-400" />
        <span>BACKEND OFFLINE</span>
      </Badge>
    );
  }

  return (
    <Badge variant="success" className="gap-1.5 font-mono text-[11px]" title="FastAPI backend healthy">
      <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
      <span>API HEALTHY</span>
    </Badge>
  );
}
