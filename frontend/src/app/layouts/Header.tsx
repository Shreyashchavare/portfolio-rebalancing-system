import { useState, useRef, useEffect } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { StatusBanner } from '@/components/feedback/StatusBanner';
import { ThemeSelector } from '@/components/ui/ThemeSelector';
import { Badge } from '@/components/ui/Badge';
import { DEV_MOCK_TOKENS, type BusinessPersona } from '@/types/auth';
import {
  Menu,
  UserCheck,
  ChevronDown,
  Settings,
  Terminal,
  Sliders,
  Check,
} from 'lucide-react';

interface HeaderProps {
  onOpenMobile: () => void;
}

const ROUTE_TITLES: Record<string, { title: string; subtitle: string }> = {
  '/dashboard': {
    title: 'Financial Overview',
    subtitle: 'Portfolio health, allocation surveillance & governance',
  },
  '/portfolios': {
    title: 'Portfolio Management',
    subtitle: 'Multi-asset valuation, positions & target drift',
  },
  '/rebalancing': {
    title: 'Rebalancing Recommendations',
    subtitle: 'Deterministic trade proposals & constraint simulation',
  },
  '/approvals': {
    title: 'Governance & Approvals',
    subtitle: 'Mandatory human-in-the-loop review & immutable audit log',
  },
  '/policies': {
    title: 'Compliance Policy RAG',
    subtitle: 'FastEmbed vector search & grounded IPS citations',
  },
  '/workflows': {
    title: 'Workflow Orchestration',
    subtitle: 'Lifecycle transition & state tracking',
  },
  '/settings': {
    title: 'System Settings',
    subtitle: 'Appearance, display density & reviewer identity configuration',
  },
};

export function Header({ onOpenMobile }: HeaderProps) {
  const location = useLocation();
  const { reviewer, persona, setPersona, isDevelopment } = useAuth();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const routeMeta = ROUTE_TITLES[location.pathname] || {
    title: 'YottaFlex Rebalancing',
    subtitle: 'Deterministic Portfolio Operations',
  };

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getPersonaBadgeVariant = (p?: BusinessPersona) => {
    switch (p) {
      case 'ADMIN':
        return 'danger';
      case 'COMPLIANCE':
        return 'brand';
      case 'ANALYST':
        return 'navy';
      case 'CUSTOMER':
      default:
        return 'neutral';
    }
  };

  const personaLabel =
    persona === 'CUSTOMER'
      ? 'Customer'
      : persona === 'ANALYST'
      ? 'Operations Analyst'
      : persona === 'COMPLIANCE'
      ? 'Compliance Reviewer'
      : 'System Admin';

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 px-4 sm:px-6 backdrop-blur transition-colors duration-200">
      {/* Left region: Mobile menu button & page titles */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onOpenMobile}
          className="lg:hidden p-2 rounded-md text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 focus:outline-none"
          aria-label="Open sidebar navigation"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div>
          <h1 className="text-sm font-semibold text-slate-900 dark:text-slate-100 leading-tight">
            {routeMeta.title}
          </h1>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 hidden sm:block">
            {routeMeta.subtitle}
          </p>
        </div>
      </div>

      {/* Right region: Status badge, Theme Selector and Reviewer Identity */}
      <div className="flex items-center gap-2.5 sm:gap-3">
        {/* Backend connectivity indicator */}
        <StatusBanner />

        {/* Global persistent theme selector */}
        <ThemeSelector />

        {/* Reviewer identity & role selector */}
        <div className="relative" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex items-center gap-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/80 dark:bg-slate-800/80 px-2.5 py-1.5 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700/80 transition-colors focus:outline-none"
            aria-expanded={isDropdownOpen}
            aria-haspopup="true"
          >
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-medium">
              <UserCheck className="h-3.5 w-3.5" />
            </div>
            <div className="text-left hidden md:block">
              <div className="text-[11px] font-semibold text-slate-900 dark:text-slate-100 leading-none">
                {reviewer?.reviewer_id || 'REV-DEV-01'}
              </div>
              <div className="text-[9px] text-slate-500 font-mono mt-0.5">
                {personaLabel}
              </div>
            </div>
            <Badge
              variant={getPersonaBadgeVariant(persona)}
              size="sm"
              className="font-mono text-[10px]"
            >
              {reviewer?.role || 'REVIEWER'}
            </Badge>
            <ChevronDown className="h-3 w-3 text-slate-400 dark:text-slate-500" />
          </button>

          {/* User Account Menu Dropdown */}
          {isDropdownOpen && (
            <div className="absolute right-0 mt-2 w-72 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 shadow-lg ring-1 ring-black/5 dark:ring-white/10 z-50">
              <div className="px-2 py-2 border-b border-slate-100 dark:border-slate-700/60">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                  Active Persona &amp; Role
                </span>
                <div className="font-semibold text-slate-900 dark:text-slate-100 text-xs mt-0.5">
                  {reviewer?.reviewer_id || 'User'} &bull; Role: {reviewer?.role || 'VIEWER'}
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono mt-0.5">
                  {reviewer?.email}
                </div>
              </div>

              {/* Dev Persona Switcher in dropdown */}
              {isDevelopment && (
                <div className="py-2 border-b border-slate-100 dark:border-slate-700/60">
                  <div className="flex items-center justify-between px-2 mb-1.5 text-[10px] font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                    <div className="flex items-center gap-1.5">
                      <Sliders className="w-3 h-3" />
                      <span>Switch Role Persona</span>
                    </div>
                    <span className="text-[9px] font-mono px-1 py-0.2 bg-indigo-100 dark:bg-indigo-950/80 rounded border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300">
                      DEV ONLY
                    </span>
                  </div>
                  <div className="space-y-1">
                    {DEV_MOCK_TOKENS.map((mock) => {
                      const isSelected = persona === mock.persona;
                      return (
                        <button
                          key={mock.persona}
                          type="button"
                          onClick={() => {
                            setPersona(mock.persona);
                            setIsDropdownOpen(false);
                          }}
                          className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-xs text-left transition-colors ${
                            isSelected
                              ? 'bg-indigo-50 dark:bg-indigo-950/60 font-semibold text-indigo-900 dark:text-indigo-200'
                              : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700/60'
                          }`}
                        >
                          <div>
                            <div className="text-xs">{mock.label}</div>
                            <div className="text-[10px] text-slate-400 font-mono">{mock.role}</div>
                          </div>
                          {isSelected && <Check className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="mt-1 space-y-0.5">
                <Link
                  to="/settings"
                  onClick={() => setIsDropdownOpen(false)}
                  className="w-full flex items-center gap-2 rounded px-2.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700/60 transition-colors"
                >
                  <Settings className="w-4 h-4 text-slate-400" />
                  <span>Account Settings</span>
                </Link>

                {(isDevelopment || reviewer?.role === 'ADMIN') && (
                  <Link
                    to="/settings"
                    onClick={() => setIsDropdownOpen(false)}
                    className="w-full flex items-center gap-2 rounded px-2.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700/60 transition-colors"
                  >
                    <Terminal className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                    <span>System Diagnostics</span>
                    <Badge variant="brand" size="sm" className="ml-auto text-[9px]">
                      ADMIN
                    </Badge>
                  </Link>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
