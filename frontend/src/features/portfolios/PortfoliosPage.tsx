import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { DataTable, type Column } from '@/components/ui/DataTable';
import { FinancialMetricCard } from '@/components/ui/FinancialMetricCard';
import {
  Briefcase,
  Layers,
  Compass,
  AlertTriangle,
  RotateCw,
  Search,
  CheckCircle2,
  Calendar,
} from 'lucide-react';

interface HoldingRow {
  symbol: string;
  name: string;
  assetClass: 'EQUITY' | 'FIXED_INCOME' | 'CASH' | 'COMMODITIES';
  quantity: string;
  unitPrice: string;
  marketValue: string;
  priceAgeDays: number;
  diagnostic: string | null;
}

// Starter reference portfolio holdings representation for interface architecture
const SAMPLE_HOLDINGS: HoldingRow[] = [
  {
    symbol: 'AAPL',
    name: 'Apple Inc.',
    assetClass: 'EQUITY',
    quantity: '2,500.0000',
    unitPrice: '$180.0000',
    marketValue: '$450,000.0000',
    priceAgeDays: 0,
    diagnostic: null,
  },
  {
    symbol: 'MSFT',
    name: 'Microsoft Corporation',
    assetClass: 'EQUITY',
    quantity: '750.0000',
    unitPrice: '$400.0000',
    marketValue: '$300,000.0000',
    priceAgeDays: 0,
    diagnostic: null,
  },
  {
    symbol: 'BND',
    name: 'Vanguard Total Bond Market ETF',
    assetClass: 'FIXED_INCOME',
    quantity: '2,000.0000',
    unitPrice: '$75.0000',
    marketValue: '$150,000.0000',
    priceAgeDays: 1,
    diagnostic: null,
  },
  {
    symbol: 'USD_CASH',
    name: 'US Dollar Settlement Cash',
    assetClass: 'CASH',
    quantity: '150,000.0000',
    unitPrice: '$1.0000',
    marketValue: '$150,000.0000',
    priceAgeDays: 0,
    diagnostic: null,
  },
  {
    symbol: 'GLD',
    name: 'SPDR Gold Shares',
    assetClass: 'COMMODITIES',
    quantity: '250.0000',
    unitPrice: '$200.0000',
    marketValue: '$50,000.0000',
    priceAgeDays: 4,
    diagnostic: 'STALE PRICE (>3 DAYS)',
  },
];

export function PortfoliosPage() {
  const [selectedPortfolio, setSelectedPortfolio] = useState('PORT-INV-000001-01');
  const [searchQuery, setSearchQuery] = useState('');
  const [density, setDensity] = useState<'normal' | 'compact'>('normal');

  const filteredHoldings = SAMPLE_HOLDINGS.filter(
    (h) =>
      h.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      h.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const columns: Column<HoldingRow>[] = [
    {
      key: 'symbol',
      header: 'Symbol / Security',
      render: (item) => (
        <div>
          <div className="font-semibold font-mono text-slate-900 dark:text-slate-100">{item.symbol}</div>
          <div className="text-[11px] text-slate-500 dark:text-slate-400">{item.name}</div>
        </div>
      ),
    },
    {
      key: 'assetClass',
      header: 'Asset Class',
      render: (item) => {
        const variants = {
          EQUITY: 'brand',
          FIXED_INCOME: 'success',
          CASH: 'neutral',
          COMMODITIES: 'warning',
        } as const;
        return (
          <Badge variant={variants[item.assetClass]} size="sm">
            {item.assetClass}
          </Badge>
        );
      },
    },
    {
      key: 'quantity',
      header: 'Quantity',
      align: 'right',
      render: (item) => <span className="font-mono">{item.quantity}</span>,
    },
    {
      key: 'unitPrice',
      header: 'Unit Price',
      align: 'right',
      render: (item) => <span className="font-mono">{item.unitPrice}</span>,
    },
    {
      key: 'marketValue',
      header: 'Market Value',
      align: 'right',
      render: (item) => (
        <span className="font-mono font-semibold text-slate-900 dark:text-slate-100">
          {item.marketValue}
        </span>
      ),
    },
    {
      key: 'priceAgeDays',
      header: 'Price Age',
      align: 'center',
      render: (item) => (
        <span
          className={`font-mono text-xs ${
            item.priceAgeDays > 3
              ? 'text-amber-600 dark:text-amber-400 font-semibold'
              : 'text-slate-600 dark:text-slate-400'
          }`}
        >
          {item.priceAgeDays}d
        </span>
      ),
    },
    {
      key: 'diagnostic',
      header: 'Diagnostic Status',
      render: (item) =>
        item.diagnostic ? (
          <Badge variant="warning" size="sm" className="gap-1 text-[10px]">
            <AlertTriangle className="w-3 h-3 text-amber-600 dark:text-amber-400" />
            <span>{item.diagnostic}</span>
          </Badge>
        ) : (
          <Badge variant="success" size="sm" className="gap-1 text-[10px]">
            <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
            <span>CURRENT</span>
          </Badge>
        ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Portfolio Management
            </h2>
            <Badge variant="brand" size="sm">
              ANALYTICAL WORKSPACE
            </Badge>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Multi-asset valuation, position age diagnostics, and corridor drift analysis.
          </p>
        </div>

        {/* Portfolio Selector & Valuation Date Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 shadow-sm">
            <Briefcase className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedPortfolio}
              onChange={(e) => setSelectedPortfolio(e.target.value)}
              className="bg-transparent text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="PORT-INV-000001-01" className="dark:bg-slate-900">
                PORT-INV-000001-01 (Aggressive Growth)
              </option>
              <option value="PORT-INV-000001-02" className="dark:bg-slate-900">
                PORT-INV-000001-02 (Balanced Income)
              </option>
              <option value="PORT-INV-000001-03" className="dark:bg-slate-900">
                PORT-INV-000001-03 (Conservative Wealth)
              </option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-600 dark:text-slate-300 shadow-sm">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-mono">2026-01-15</span>
          </div>

          <Button variant="outline" size="sm" leftIcon={<RotateCw className="w-3.5 h-3.5" />}>
            Revalue
          </Button>
        </div>
      </div>

      {/* Corridor Alert Warning Banner */}
      <Alert variant="warning" title="Rebalance Corridor Breach Detected">
        Portfolio drift exceeds the absolute 5.0% rebalance corridor threshold on Equity (+11.43%) and Cash (-11.43%).
        Automated rebalance signal: <strong>SELL EQUITIES &rarr; BUY CASH</strong>.
      </Alert>

      {/* Analytical Valuation Summary Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <FinancialMetricCard
          title="Total Market Value"
          value="$1,100,000.00"
          badgeText="Verified As-Of Date"
          badgeVariant="success"
          subtitle="4 Asset Classes"
          icon={<Compass className="w-4 h-4 text-brand-600 dark:text-brand-400" />}
          accentBorder="brand"
        />

        <FinancialMetricCard
          title="Total Position Count"
          value="5 Holdings"
          badgeText="Single-Currency USD"
          badgeVariant="neutral"
          subtitle="Equities, Bonds, Cash, Gold"
          icon={<Layers className="w-4 h-4 text-slate-600 dark:text-slate-400" />}
          accentBorder="neutral"
        />

        <FinancialMetricCard
          title="Maximum Asset Drift"
          value="+11.43%"
          badgeText="CORRIDOR TRIGGERED"
          badgeVariant="warning"
          subtitle="Target: 60.0% | Actual: 71.43%"
          icon={<AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />}
          accentBorder="warning"
        />

        <FinancialMetricCard
          title="Available Cash Buffer"
          value="$150,000.00"
          badgeText="Solvent &bull; 13.64%"
          badgeVariant="success"
          subtitle="Minimum 5.0% enforced"
          icon={<CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />}
          accentBorder="success"
        />
      </div>

      {/* Target vs Actual Allocation Visual Comparison Matrix */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Asset Class Allocation &amp; Drift Comparison</CardTitle>
              <CardDescription>
                Comparison between current market weight and target mandate allocation
              </CardDescription>
            </div>
            <Badge variant="brand" size="sm">
              5.0% Rebalance Threshold
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Equity Drift */}
            <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-800 dark:text-slate-200">Equity Allocation</span>
                <Badge variant="danger" size="sm">DRIFT: +11.43% (SELL)</Badge>
              </div>
              <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 dark:text-slate-400">
                <span>Target: 60.00% ($660,000)</span>
                <span>Current: 71.43% ($785,714)</span>
              </div>
              <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden flex">
                <div className="bg-brand-600 w-[71.43%]" />
              </div>
            </div>

            {/* Cash Drift */}
            <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-800 dark:text-slate-200">Cash Allocation</span>
                <Badge variant="brand" size="sm">DRIFT: -11.43% (BUY)</Badge>
              </div>
              <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 dark:text-slate-400">
                <span>Target: 40.00% ($440,000)</span>
                <span>Current: 28.57% ($314,286)</span>
              </div>
              <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden flex">
                <div className="bg-emerald-600 w-[28.57%]" />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Holdings Table Section */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <CardTitle>Position Breakdown &amp; Valuation Diagnostics</CardTitle>
              <CardDescription>
                Detailed holdings valuation with market-price staleness detection
              </CardDescription>
            </div>

            <div className="flex items-center gap-2">
              <div className="relative w-48 sm:w-64">
                <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Filter by symbol..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                />
              </div>

              <div className="flex items-center border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden text-xs">
                <button
                  type="button"
                  onClick={() => setDensity('normal')}
                  className={`px-2.5 py-1.5 transition-colors ${
                    density === 'normal'
                      ? 'bg-slate-100 dark:bg-slate-800 font-semibold text-slate-900 dark:text-slate-100'
                      : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800'
                  }`}
                >
                  Normal
                </button>
                <button
                  type="button"
                  onClick={() => setDensity('compact')}
                  className={`px-2.5 py-1.5 transition-colors ${
                    density === 'compact'
                      ? 'bg-slate-100 dark:bg-slate-800 font-semibold text-slate-900 dark:text-slate-100'
                      : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800'
                  }`}
                >
                  Compact
                </button>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={filteredHoldings}
            keyExtractor={(item) => item.symbol}
            density={density}
          />
        </CardContent>
      </Card>
    </div>
  );
}
