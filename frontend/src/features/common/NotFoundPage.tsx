import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Home, ArrowLeft } from 'lucide-react';

export function NotFoundPage() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center p-6 transition-colors duration-200">
      <div className="w-16 h-16 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400 dark:text-slate-500 mb-4 font-mono font-bold text-xl">
        404
      </div>
      <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
        Page Not Found
      </h2>
      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400 max-w-md">
        The requested URL path does not correspond to an active operational module in the YottaFlex system.
      </p>
      <div className="mt-6 flex items-center gap-3">
        <Link to="/dashboard">
          <Button variant="primary" size="sm" leftIcon={<Home className="w-4 h-4" />}>
            Return to Dashboard
          </Button>
        </Link>
        <button
          type="button"
          onClick={() => window.history.back()}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Go back</span>
        </button>
      </div>
    </div>
  );
}
