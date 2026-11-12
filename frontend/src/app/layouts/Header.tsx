import { useState, useRef, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { StatusBanner } from '@/components/feedback/StatusBanner';
import { ThemeSelector } from '@/components/ui/ThemeSelector';
import { Badge } from '@/components/ui/Badge';
import { DEV_MOCK_TOKENS } from '@/types/auth';
import {
  Menu,
  UserCheck,
  ChevronDown,
  Shield,
  Eye,
  Check,
} from 'lucide-react';

interface HeaderProps {
  onOpenMobile: () => void;
}

const ROUTE_TITLES: Record<string, { title: string; subtitle: string }> = {
  '/dashboard': {
    title: 'Financial Overview',
    subtitle: 'Executive operations & rebalancing monitoring',
  },
  '/portfolios': {
    title: 'Portfolio Management',
    subtitle: 'Multi-asset valuation, positions & target drift',
  },
  '/rebalancing': {
    title: 'Rebalancing Engine',
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
    subtitle: 'Agentic state machine lifecycle tracking',
  },
  '/settings': {
    title: 'System Settings',
    subtitle: 'Appearance, API gateway & reviewer identity configuration',
  },
};

export function Header({ onOpenMobile }: HeaderProps) {
  const location = useLocation();
  const { reviewer, activeMockToken, selectMockToken, isDevelopment } = useAuth();
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

  const getRoleBadgeVariant = (role?: string) => {
    switch (role) {
      case 'ADMIN':
        return 'danger';
      case 'PORTFOLIO_MANAGER':
      case 'COMPLIANCE_OFFICER':
      case 'REVIEWER':
        return 'brand';
      case 'VIEWER':
        return 'neutral';
      default:
        return 'neutral';
    }
  };

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
                {reviewer?.reviewer_id || 'Unauthenticated'}
              </div>
            </div>
            <Badge
              variant={getRoleBadgeVariant(reviewer?.role)}
              size="sm"
              className="font-mono text-[10px]"
            >
              {reviewer?.role || 'ANONYMOUS'}
            </Badge>
            {isDevelopment && <ChevronDown className="h-3 w-3 text-slate-400 dark:text-slate-500" />}
          </button>

          {/* Dev Mock Token Switcher Dropdown */}
          {isDevelopment && isDropdownOpen && (
            <div className="absolute right-0 mt-2 w-72 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 shadow-lg ring-1 ring-black/5 dark:ring-white/10 z-50">
              <div className="px-2 py-1.5 border-b border-slate-100 dark:border-slate-700/60">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                  Dev Reviewer Identity (RBAC)
                </span>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                  Switches the mock bearer token sent to governance endpoints.
                </p>
              </div>

              <div className="mt-1 space-y-1">
                {DEV_MOCK_TOKENS.map((item) => {
                  const isSelected = activeMockToken?.token === item.token;
                  return (
                    <button
                      key={item.token}
                      type="button"
                      onClick={() => {
                        selectMockToken(item.token);
                        setIsDropdownOpen(false);
                      }}
                      className={`w-full flex items-start gap-2.5 rounded p-2 text-left text-xs transition-colors ${
                        isSelected
                          ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-900 dark:text-blue-200 font-medium'
                          : 'hover:bg-slate-50 dark:hover:bg-slate-700/60 text-slate-700 dark:text-slate-200'
                      }`}
                    >
                      <div className="mt-0.5 shrink-0">
                        {item.role === 'ADMIN' ? (
                          <Shield className="w-4 h-4 text-rose-600 dark:text-rose-400" />
                        ) : item.role === 'VIEWER' ? (
                          <Eye className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                        ) : (
                          <UserCheck className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-900 dark:text-slate-100 text-xs">
                            {item.reviewerId}
                          </span>
                          <Badge variant={getRoleBadgeVariant(item.role)} size="sm">
                            {item.role}
                          </Badge>
                        </div>
                        <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-1">
                          {item.description}
                        </p>
                      </div>
                      {isSelected && (
                        <Check className="w-4 h-4 text-brand-600 dark:text-brand-400 shrink-0 self-center" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
