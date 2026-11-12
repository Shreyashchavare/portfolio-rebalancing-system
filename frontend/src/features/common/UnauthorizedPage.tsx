import { ShieldAlert, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';

interface UnauthorizedPageProps {
  requiredRole?: string;
  requiredPersona?: string;
}

export function UnauthorizedPage({ requiredRole, requiredPersona }: UnauthorizedPageProps) {
  const { reviewer, persona } = useAuth();

  return (
    <div className="min-h-[70vh] flex items-center justify-center p-4">
      <Card className="max-w-md w-full border-rose-200 dark:border-rose-900/60 shadow-lg">
        <CardContent className="pt-8 pb-8 text-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 flex items-center justify-center mx-auto border border-rose-200 dark:border-rose-800">
            <ShieldAlert className="w-7 h-7" />
          </div>

          <div>
            <div className="flex items-center justify-center gap-2 mb-1">
              <Badge variant="danger" size="sm">
                HTTP 403 FORBIDDEN
              </Badge>
              <Badge variant="neutral" size="sm">
                RBAC RESTRICTION
              </Badge>
            </div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
              Access Restricted
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">
              Your current authenticated identity does not have permission to access this financial workspace or perform this action.
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-left text-xs space-y-1.5">
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Current Persona:</span>
              <span className="font-semibold text-slate-900 dark:text-slate-100">{persona}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Assigned Role:</span>
              <span className="font-mono text-slate-900 dark:text-slate-100">{reviewer?.role || 'ANONYMOUS'}</span>
            </div>
            {requiredRole && (
              <div className="flex justify-between pt-1 border-t border-slate-200 dark:border-slate-700">
                <span className="text-slate-500 dark:text-slate-400">Required Role:</span>
                <span className="font-mono text-rose-600 dark:text-rose-400">{requiredRole}</span>
              </div>
            )}
            {requiredPersona && (
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Required Persona:</span>
                <span className="font-semibold text-rose-600 dark:text-rose-400">{requiredPersona}</span>
              </div>
            )}
          </div>

          <div className="pt-2">
            <Link to="/dashboard">
              <Button variant="primary" size="sm" leftIcon={<ArrowLeft className="w-4 h-4" />}>
                Return to Authorized Dashboard
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
