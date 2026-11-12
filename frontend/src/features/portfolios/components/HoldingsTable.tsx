import { useState, useMemo } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { SearchInput } from '@/components/ui/SearchInput';
import { DataTable, type Column } from '@/components/ui/DataTable';
import { formatCurrency, formatPercent } from '@/lib/utils';
import type { PositionValuation } from '../types/portfolio';
import { AlertTriangle, CheckCircle2, Filter, Layers } from 'lucide-react';

interface HoldingsTableProps {
  positions: PositionValuation[];
  totalMarketValue: string;
}

export function HoldingsTable({ positions, totalMarketValue }: HoldingsTableProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [assetClassFilter, setAssetClassFilter] = useState('ALL');

  const totalValNum = parseFloat(totalMarketValue) || 0;

  // Extract unique asset classes for filtering
  const assetClasses = useMemo(() => {
    const set = new Set<string>();
    positions.forEach((p) => set.add(p.asset_class));
    return ['ALL', ...Array.from(set)];
  }, [positions]);

  // Filter positions by search query and asset class
  const filteredPositions = useMemo(() => {
    return positions.filter((p) => {
      const matchesSearch =
        searchTerm === '' ||
        (p.symbol && p.symbol.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (p.instrument_name && p.instrument_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
        p.instrument_id.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesClass = assetClassFilter === 'ALL' || p.asset_class === assetClassFilter;

      return matchesSearch && matchesClass;
    });
  }, [positions, searchTerm, assetClassFilter]);

  const columns: Column<PositionValuation>[] = [
    {
      key: 'symbol',
      header: 'Security / Asset',
      render: (item) => (
        <div>
          <div className="font-semibold text-xs text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
            <span>{item.symbol || item.instrument_id}</span>
          </div>
          <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate max-w-xs">
            {item.instrument_name || item.instrument_id}
          </div>
        </div>
      ),
    },
    {
      key: 'asset_class',
      header: 'Asset Class',
      render: (item) => (
        <Badge
          variant={
            item.asset_class === 'EQUITY'
              ? 'brand'
              : item.asset_class === 'FIXED_INCOME'
              ? 'success'
              : item.asset_class === 'CASH'
              ? 'navy'
              : 'neutral'
          }
          size="sm"
        >
          {item.asset_class}
        </Badge>
      ),
    },
    {
      key: 'quantity',
      header: 'Quantity (Lots)',
      align: 'right',
      render: (item) => (
        <span className="font-mono text-xs text-slate-800 dark:text-slate-200">
          {parseFloat(item.quantity).toLocaleString('en-US', {
            minimumFractionDigits: 4,
            maximumFractionDigits: 4,
          })}
        </span>
      ),
    },
    {
      key: 'unit_price',
      header: 'Unit Price',
      align: 'right',
      render: (item) => (
        <span className="font-mono text-xs text-slate-700 dark:text-slate-300">
          {formatCurrency(parseFloat(item.unit_price) || 0)}
        </span>
      ),
    },
    {
      key: 'market_value',
      header: 'Market Value',
      align: 'right',
      render: (item) => (
        <span className="font-mono text-xs font-bold text-slate-900 dark:text-slate-100">
          {formatCurrency(parseFloat(item.market_value) || 0)}
        </span>
      ),
    },
    {
      key: 'weight',
      header: 'Portfolio Weight',
      align: 'right',
      render: (item) => {
        const itemVal = parseFloat(item.market_value) || 0;
        const weight = totalValNum > 0 ? (itemVal / totalValNum) * 100 : 0;
        return (
          <span className="font-mono text-xs font-semibold text-brand-600 dark:text-brand-400">
            {formatPercent(weight)}
          </span>
        );
      },
    },
    {
      key: 'price_date',
      header: 'Price Date',
      align: 'center',
      render: (item) => (
        <span className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
          {item.price_date || '—'}
        </span>
      ),
    },
    {
      key: 'diagnostic',
      header: 'Price Freshness & Diagnostics',
      align: 'left',
      render: (item) => {
        const isStale = item.price_age_days > 0;
        return (
          <div className="flex items-center gap-1.5" title={item.diagnostic || 'Price is current'}>
            {isStale ? (
              <Badge variant="warning" size="sm" className="gap-1 text-[10px]">
                <AlertTriangle className="w-3 h-3 text-amber-600 dark:text-amber-400 shrink-0" />
                <span>{item.price_age_days}d STALE</span>
              </Badge>
            ) : (
              <Badge variant="success" size="sm" className="gap-1 text-[10px]">
                <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span>CURRENT</span>
              </Badge>
            )}
            {item.diagnostic && (
              <span className="text-[10px] text-slate-400 truncate max-w-[180px] hidden lg:inline">
                {item.diagnostic}
              </span>
            )}
          </div>
        );
      },
    },
  ];

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <CardTitle>Position Breakdown &amp; Valuation Diagnostics</CardTitle>
            <CardDescription>
              Holding positions valued against actual market prices with staleness age indicators
            </CardDescription>
          </div>

          {/* Search & Filter Toolbar */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="w-48">
              <SearchInput
                value={searchTerm}
                onChange={setSearchTerm}
                placeholder="Search symbol, name..."
              />
            </div>

            <div className="flex items-center gap-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs shadow-sm">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <select
                aria-label="Filter by Asset Class"
                value={assetClassFilter}
                onChange={(e) => setAssetClassFilter(e.target.value)}
                className="bg-transparent text-xs text-slate-700 dark:text-slate-200 focus:outline-none cursor-pointer"
              >
                {assetClasses.map((ac) => (
                  <option key={ac} value={ac} className="dark:bg-slate-900">
                    {ac === 'ALL' ? 'All Asset Classes' : ac}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {positions.length === 0 ? (
          <div className="h-40 flex flex-col items-center justify-center text-slate-400">
            <Layers className="w-10 h-10 mb-2 opacity-30" />
            <p className="text-xs">No active holdings positions found for this portfolio.</p>
          </div>
        ) : filteredPositions.length === 0 ? (
          <div className="h-32 flex flex-col items-center justify-center text-slate-400 text-xs">
            No holdings match the search filter "{searchTerm}" in asset class {assetClassFilter}.
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={filteredPositions}
            keyExtractor={(item) => item.holding_id}
          />
        )}
      </CardContent>
    </Card>
  );
}

