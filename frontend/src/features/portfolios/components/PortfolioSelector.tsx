import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Briefcase, Calendar, RotateCw, Edit3, Check } from 'lucide-react';
import type { PortfolioReference } from '../types/portfolio';

interface PortfolioSelectorProps {
  selectedPortfolioId: string;
  asOfDate: string;
  isFetching: boolean;
  activeReference?: PortfolioReference;
  portfolioReferences: PortfolioReference[];
  onSelectPortfolio: (id: string) => void;
  onSetAsOfDate: (date: string) => void;
  onApplyCustomId: (id: string) => void;
  onRevalue: () => void;
}

export function PortfolioSelector({
  selectedPortfolioId,
  asOfDate,
  isFetching,
  activeReference,
  portfolioReferences,
  onSelectPortfolio,
  onSetAsOfDate,
  onApplyCustomId,
  onRevalue,
}: PortfolioSelectorProps) {
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [customId, setCustomId] = useState('');

  const handleApply = (e: React.FormEvent) => {
    e.preventDefault();
    if (customId.trim()) {
      onApplyCustomId(customId.trim());
      setShowCustomInput(false);
    }
  };

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
      <div>
        <div className="flex items-center gap-2">
          <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Portfolio Management &amp; Analytics
          </h2>
          <Badge variant="brand" size="sm">
            LIVE FASTAPI VALUATION
          </Badge>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          {activeReference ? (
            <span>
              <strong>{activeReference.portfolio_name}</strong> &bull; Investor:{' '}
              <span className="font-mono">{activeReference.investor_id}</span> &bull; Currency:{' '}
              <span className="font-mono">{activeReference.base_currency}</span>
            </span>
          ) : (
            <span>
              Custom Portfolio ID: <span className="font-mono font-bold">{selectedPortfolioId}</span>
            </span>
          )}
        </p>
      </div>

      {/* Interactive Controls */}
      <div className="flex flex-wrap items-center gap-2.5">
        {!showCustomInput ? (
          <div className="flex items-center gap-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 shadow-sm">
            <Briefcase className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <select
              aria-label="Select Target Portfolio"
              value={selectedPortfolioId}
              onChange={(e) => onSelectPortfolio(e.target.value)}
              className="bg-transparent text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none cursor-pointer pr-1"
            >
              {portfolioReferences.map((ref) => (
                <option key={ref.portfolio_id} value={ref.portfolio_id} className="dark:bg-slate-900 text-slate-900 dark:text-slate-100">
                  {ref.portfolio_id} ({ref.portfolio_name.split(' ')[0]})
                </option>
              ))}
            </select>
            <button
              type="button"
              title="Enter custom portfolio ID"
              onClick={() => {
                setCustomId(selectedPortfolioId);
                setShowCustomInput(true);
              }}
              className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 rounded transition-colors"
            >
              <Edit3 className="w-3 h-3" />
            </button>
          </div>
        ) : (
          <form onSubmit={handleApply} className="flex items-center gap-1 bg-white dark:bg-slate-900 border border-brand-500 rounded-lg px-2 py-1 shadow-sm">
            <input
              type="text"
              value={customId}
              onChange={(e) => setCustomId(e.target.value)}
              placeholder="e.g. PORT-API-01"
              className="bg-transparent text-xs font-mono font-medium text-slate-900 dark:text-slate-100 focus:outline-none w-36 px-1"
              autoFocus
            />
            <button
              type="submit"
              className="p-1 rounded bg-brand-600 text-white hover:bg-brand-700"
              title="Apply ID"
            >
              <Check className="w-3 h-3" />
            </button>
            <button
              type="button"
              onClick={() => setShowCustomInput(false)}
              className="text-[11px] text-slate-400 hover:text-slate-600 px-1"
            >
              Cancel
            </button>
          </form>
        )}

        {/* Valuation Date Picker */}
        <div className="flex items-center gap-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-700 dark:text-slate-200 shadow-sm">
          <Calendar className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <input
            aria-label="Valuation As-Of Date"
            type="date"
            value={asOfDate}
            onChange={(e) => onSetAsOfDate(e.target.value)}
            className="bg-transparent font-mono text-xs focus:outline-none cursor-pointer dark:[color-scheme:dark]"
          />
        </div>

        {/* Revalue Trigger */}
        <Button
          variant="outline"
          size="sm"
          onClick={onRevalue}
          disabled={isFetching}
          leftIcon={<RotateCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin text-brand-600' : ''}`} />}
        >
          {isFetching ? 'Valuing...' : 'Revalue'}
        </Button>
      </div>
    </div>
  );
}

