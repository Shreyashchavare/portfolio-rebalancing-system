export type ThemePreference = 'light' | 'dark' | 'system';

export type ResolvedTheme = 'light' | 'dark';

export interface ThemeOption {
  value: ThemePreference;
  label: string;
  description: string;
}

export const THEME_OPTIONS: ThemeOption[] = [
  {
    value: 'light',
    label: 'Light',
    description: 'Crisp off-white surfaces and high contrast financial tables.',
  },
  {
    value: 'dark',
    label: 'Dark',
    description: 'Deep navy/charcoal backgrounds with subdued elevation.',
  },
  {
    value: 'system',
    label: 'System',
    description: 'Automatically synchronizes with your OS appearance.',
  },
];
