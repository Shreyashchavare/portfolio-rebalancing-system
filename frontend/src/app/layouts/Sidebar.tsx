import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import type { NavItem } from '@/types/navigation';
import { useAuth } from '@/hooks/useAuth';
import {
  LayoutDashboard,
  Briefcase,
  Scale,
  ShieldCheck,
  FileText,
  Workflow,
  Settings,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  X,
  Compass,
  History,
  FileCheck,
} from 'lucide-react';

interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

export function Sidebar({
  isCollapsed,
  onToggleCollapse,
  isMobileOpen,
  onCloseMobile,
}: SidebarProps) {
  const { persona, reviewer } = useAuth();

  // Role-tailored navigation items
  const navItems: NavItem[] = (() => {
    switch (persona) {
      case 'CUSTOMER':
        return [
          { name: 'Overview', href: '/dashboard?tab=overview', icon: LayoutDashboard },
          { name: 'My Portfolio', href: '/portfolios', icon: Briefcase },
          { name: 'Recommendations', href: '/dashboard?tab=recommendations', icon: Scale },
          { name: 'Activity', href: '/dashboard?tab=activity', icon: History },
          { name: 'Settings', href: '/settings', icon: Settings },
        ];
      case 'ANALYST':
        return [
          { name: 'Dashboard', href: '/dashboard?tab=dashboard', icon: LayoutDashboard },
          { name: 'Portfolios', href: '/portfolios', icon: Briefcase },
          { name: 'Drift Analysis', href: '/dashboard?tab=drift', icon: Compass },
          { name: 'Rebalancing Engine', href: '/rebalancing', icon: Scale },
          { name: 'Workflows', href: '/workflows', icon: Workflow },
          { name: 'Settings', href: '/settings', icon: Settings },
        ];
      case 'COMPLIANCE':
        return [
          { name: 'Review Queue', href: '/dashboard?tab=queue', icon: ShieldCheck },
          { name: 'Proposal Details', href: '/dashboard?tab=details', icon: FileCheck },
          { name: 'Policy Checks', href: '/policies', icon: FileText },
          { name: 'Audit History', href: '/dashboard?tab=audit', icon: History },
          { name: 'Settings', href: '/settings', icon: Settings },
        ];
      case 'ADMIN':
      default:
        return [
          { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
          { name: 'Portfolios', href: '/portfolios', icon: Briefcase },
          { name: 'Rebalancing', href: '/rebalancing', icon: Scale },
          { name: 'Approvals', href: '/approvals', icon: ShieldCheck },
          { name: 'Policies', href: '/policies', icon: FileText },
          { name: 'Workflows', href: '/workflows', icon: Workflow },
          { name: 'Settings', href: '/settings', icon: Settings },
        ];
    }
  })();

  const personaLabel =
    persona === 'CUSTOMER'
      ? 'Customer Portal'
      : persona === 'ANALYST'
      ? 'Analyst Desk'
      : persona === 'COMPLIANCE'
      ? 'Compliance Desk'
      : 'Admin Console';

  const location = useLocation();

  const isItemActive = (item: NavItem): boolean => {
    const [itemPath, itemQuery] = item.href.split('?');

    // On /approvals page, Review Queue represents the review desk
    if (location.pathname === '/approvals') {
      return item.name === 'Review Queue';
    }

    if (location.pathname !== itemPath) {
      return false;
    }

    if (itemQuery) {
      const itemParams = new URLSearchParams(itemQuery);
      const currentParams = new URLSearchParams(location.search);
      const itemTab = itemParams.get('tab');
      const currentTab = currentParams.get('tab');

      if (currentTab) {
        return currentTab === itemTab;
      }

      if (persona === 'CUSTOMER') {
        return itemTab === 'overview';
      }
      if (persona === 'ANALYST') {
        return itemTab === 'dashboard';
      }
      if (persona === 'COMPLIANCE') {
        return itemTab === 'queue';
      }

      return false;
    }

    if (location.search && location.pathname === '/dashboard') {
      return false;
    }

    return true;
  };

  return (
    <>
      {/* Mobile backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/60 dark:bg-black/70 backdrop-blur-sm lg:hidden transition-opacity"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      {/* Sidebar container */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex flex-col bg-navy-950 dark:bg-[#060d19] text-slate-300 transition-all duration-300 ease-in-out border-r border-navy-900 dark:border-slate-800/80 shadow-lg lg:shadow-none',
          isCollapsed ? 'w-20' : 'w-64',
          isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* Branding header */}
        <div className="flex h-16 items-center justify-between px-4 border-b border-navy-900/80 dark:border-slate-800/60">
          <NavLink
            to="/dashboard"
            onClick={onCloseMobile}
            className="flex items-center gap-3 overflow-hidden focus:outline-none"
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-md shadow-brand-500/20">
              <TrendingUp className="h-5 w-5" />
            </div>
            {!isCollapsed && (
              <div className="flex flex-col">
                <span className="font-bold text-sm tracking-wider text-white">
                  YOTTAFLEX
                </span>
                <span className="text-[10px] uppercase font-mono tracking-widest text-slate-400">
                  Rebalancing Core
                </span>
              </div>
            )}
          </NavLink>

          {/* Close button on mobile */}
          <button
            type="button"
            onClick={onCloseMobile}
            className="lg:hidden p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-navy-900 dark:hover:bg-slate-800"
            aria-label="Close navigation"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation items */}
        <nav className="flex-1 space-y-1.5 px-3 py-4 overflow-y-auto" aria-label="Main Navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isItemActive(item);
            return (
              <NavLink
                key={`${item.name}-${item.href}`}
                to={item.href}
                onClick={onCloseMobile}
                className={cn(
                  'group flex items-center gap-3 rounded-md px-3 py-2.5 text-xs font-medium transition-colors relative select-none',
                  active
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'text-slate-400 hover:bg-navy-900 dark:hover:bg-slate-800/80 hover:text-white',
                  isCollapsed && 'justify-center px-0'
                )}
                title={isCollapsed ? item.name : undefined}
                aria-current={active ? 'page' : undefined}
              >
                <Icon
                  className={cn(
                    'h-4 w-4 shrink-0 transition-colors',
                    active ? 'text-white' : 'text-slate-400 group-hover:text-white'
                  )}
                />
                {!isCollapsed && (
                  <span className="truncate tracking-wide">{item.name}</span>
                )}
                {item.badge && !isCollapsed && (
                  <span className="ml-auto rounded bg-navy-800 dark:bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-300">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* User-facing Workstation info & collapse toggle */}
        <div className="border-t border-navy-900/80 dark:border-slate-800/60 p-3">
          {!isCollapsed && (
            <div className="rounded bg-navy-900/60 dark:bg-slate-900/80 p-2.5 text-[11px] text-slate-400 border border-navy-800/40 dark:border-slate-800">
              <div className="flex items-center justify-between">
                <span className="font-medium text-slate-300">{personaLabel}</span>
                <span className="font-mono text-[10px] text-slate-500">v0.1.0</span>
              </div>
              <p className="text-[10px] text-slate-500 mt-0.5">
                Role: <span className="font-mono text-slate-400">{reviewer?.role || 'VIEWER'}</span>
              </p>
            </div>
          )}

          {/* Collapse toggle (desktop only) */}
          <div className="hidden lg:flex items-center justify-end pt-2">
            <button
              type="button"
              onClick={onToggleCollapse}
              className="flex items-center justify-center w-full py-1.5 text-xs text-slate-400 hover:text-white rounded hover:bg-navy-900 dark:hover:bg-slate-800 transition-colors"
              aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isCollapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <div className="flex items-center gap-2">
                  <ChevronLeft className="h-4 w-4" />
                  <span className="text-[11px]">Collapse</span>
                </div>
              )}
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
