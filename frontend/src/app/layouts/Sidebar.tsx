import { NavLink } from 'react-router-dom';
import { cn } from '@/lib/utils';
import type { NavItem } from '@/types/navigation';
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
} from 'lucide-react';

const NAVIGATION_ITEMS: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Portfolios', href: '/portfolios', icon: Briefcase },
  { name: 'Rebalancing', href: '/rebalancing', icon: Scale },
  { name: 'Approvals', href: '/approvals', icon: ShieldCheck },
  { name: 'Policy RAG', href: '/policies', icon: FileText },
  { name: 'Workflows', href: '/workflows', icon: Workflow },
  { name: 'Settings', href: '/settings', icon: Settings },
];

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
          {NAVIGATION_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.href}
                to={item.href}
                onClick={onCloseMobile}
                className={({ isActive }) =>
                  cn(
                    'group flex items-center gap-3 rounded-md px-3 py-2.5 text-xs font-medium transition-colors relative select-none',
                    isActive
                      ? 'bg-brand-600 text-white shadow-sm'
                      : 'text-slate-400 hover:bg-navy-900 dark:hover:bg-slate-800/80 hover:text-white',
                    isCollapsed && 'justify-center px-0'
                  )
                }
                title={isCollapsed ? item.name : undefined}
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      className={cn(
                        'h-4 w-4 shrink-0 transition-colors',
                        isActive ? 'text-white' : 'text-slate-400 group-hover:text-white'
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
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* System architecture badge / footer */}
        <div className="border-t border-navy-900/80 dark:border-slate-800/60 p-3">
          {!isCollapsed && (
            <div className="rounded bg-navy-900/60 dark:bg-slate-900/80 p-2.5 text-[11px] font-mono text-slate-400 border border-navy-800/40 dark:border-slate-800">
              <div className="flex items-center justify-between">
                <span>Core Engine:</span>
                <span className="text-emerald-400 font-semibold">Deterministic</span>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span>Policy RAG:</span>
                <span className="text-blue-400 font-semibold">FastEmbed ONNX</span>
              </div>
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
