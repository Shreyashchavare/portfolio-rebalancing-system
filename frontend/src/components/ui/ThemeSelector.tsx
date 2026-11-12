import { useState, useRef, useEffect } from 'react';
import { useTheme } from '@/hooks/useTheme';
import { THEME_OPTIONS } from '@/types/theme';
import { Sun, Moon, Laptop, Check, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export function ThemeSelector({ className }: { className?: string }) {
  const { theme, resolvedTheme, setTheme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getThemeIcon = () => {
    if (theme === 'system') return Laptop;
    if (resolvedTheme === 'dark') return Moon;
    return Sun;
  };

  const ActiveIcon = getThemeIcon();

  return (
    <div className={cn('relative', className)} ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1.5 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700/80 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 shadow-sm"
        aria-label={`Theme: ${theme}. Click to switch theme`}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <ActiveIcon className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
        <span className="capitalize hidden sm:inline text-[11px] font-medium">
          {theme}
        </span>
        <ChevronDown className="w-3 h-3 text-slate-400 dark:text-slate-500" />
      </button>

      {isOpen && (
        <div
          role="menu"
          aria-label="Theme options"
          className="absolute right-0 mt-2 w-56 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-1.5 shadow-lg ring-1 ring-black/5 dark:ring-white/10 z-50 animate-in fade-in-50 duration-100"
        >
          <div className="px-2 py-1 border-b border-slate-100 dark:border-slate-700/60 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Appearance Theme
            </span>
          </div>

          <div className="space-y-0.5">
            {THEME_OPTIONS.map((option) => {
              const isSelected = theme === option.value;
              const Icon =
                option.value === 'light'
                  ? Sun
                  : option.value === 'dark'
                  ? Moon
                  : Laptop;

              return (
                <button
                  key={option.value}
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setTheme(option.value);
                    setIsOpen(false);
                  }}
                  className={cn(
                    'w-full flex items-center justify-between rounded px-2.5 py-2 text-left text-xs transition-colors',
                    isSelected
                      ? 'bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 font-medium'
                      : 'text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700/60'
                  )}
                >
                  <div className="flex items-center gap-2">
                    <Icon
                      className={cn(
                        'w-4 h-4',
                        isSelected
                          ? 'text-brand-600 dark:text-brand-400'
                          : 'text-slate-400 dark:text-slate-500'
                      )}
                    />
                    <div>
                      <div className="leading-none">{option.label}</div>
                      <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 font-normal">
                        {option.value === 'system'
                          ? `Auto (${resolvedTheme})`
                          : option.label}
                      </div>
                    </div>
                  </div>
                  {isSelected && (
                    <Check className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
