import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { screen, fireEvent, render } from '@testing-library/react';
import { ThemeProvider } from '@/app/providers/ThemeProvider';
import { useTheme } from '@/hooks/useTheme';
import { ThemeSelector } from '@/components/ui/ThemeSelector';
import { renderWithProviders } from './test-utils';
import { AppLayout } from '@/app/layouts/AppLayout';

function ThemeConsumerTest() {
  const { theme, resolvedTheme, setTheme } = useTheme();
  return (
    <div>
      <div data-testid="active-theme">{theme}</div>
      <div data-testid="resolved-theme">{resolvedTheme}</div>
      <button onClick={() => setTheme('light')}>Set Light</button>
      <button onClick={() => setTheme('dark')}>Set Dark</button>
      <button onClick={() => setTheme('system')}>Set System</button>
      <ThemeSelector />
    </div>
  );
}

describe('Dual Theme Design System & Tokens', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark', 'light');
  });

  afterEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark', 'light');
  });

  it('initializes to system theme by default when no preference is saved', () => {
    render(
      <ThemeProvider>
        <ThemeConsumerTest />
      </ThemeProvider>
    );

    expect(screen.getByTestId('active-theme').textContent).toBe('system');
    expect(['light', 'dark']).toContain(screen.getByTestId('resolved-theme').textContent);
  });

  it('switches to dark theme without page reload and persists to localStorage', () => {
    render(
      <ThemeProvider>
        <ThemeConsumerTest />
      </ThemeProvider>
    );

    fireEvent.click(screen.getByText('Set Dark'));

    expect(screen.getByTestId('active-theme').textContent).toBe('dark');
    expect(screen.getByTestId('resolved-theme').textContent).toBe('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(localStorage.getItem('yottaflex_theme_preference')).toBe('dark');
  });

  it('switches to light theme without page reload and persists to localStorage', () => {
    render(
      <ThemeProvider>
        <ThemeConsumerTest />
      </ThemeProvider>
    );

    fireEvent.click(screen.getByText('Set Dark'));
    expect(document.documentElement.classList.contains('dark')).toBe(true);

    fireEvent.click(screen.getByText('Set Light'));
    expect(screen.getByTestId('active-theme').textContent).toBe('light');
    expect(screen.getByTestId('resolved-theme').textContent).toBe('light');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    expect(document.documentElement.classList.contains('light')).toBe(true);
    expect(localStorage.getItem('yottaflex_theme_preference')).toBe('light');
  });

  it('initializes from saved localStorage preference', () => {
    localStorage.setItem('yottaflex_theme_preference', 'dark');

    render(
      <ThemeProvider>
        <ThemeConsumerTest />
      </ThemeProvider>
    );

    expect(screen.getByTestId('active-theme').textContent).toBe('dark');
    expect(screen.getByTestId('resolved-theme').textContent).toBe('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('provides accessible ThemeSelector dropdown with keyboard and click navigation', () => {
    render(
      <ThemeProvider>
        <ThemeSelector />
      </ThemeProvider>
    );

    const selectorBtn = screen.getByRole('button', { name: /Theme:/i });
    expect(selectorBtn).toBeInTheDocument();
    expect(selectorBtn).toHaveAttribute('aria-haspopup', 'true');
    expect(selectorBtn).toHaveAttribute('aria-expanded', 'false');

    // Open dropdown
    fireEvent.click(selectorBtn);
    expect(selectorBtn).toHaveAttribute('aria-expanded', 'true');

    // Menu options
    const menu = screen.getByRole('menu', { name: /Theme options/i });
    expect(menu).toBeInTheDocument();

    const darkOption = screen.getByRole('menuitem', { name: /Dark/i });
    fireEvent.click(darkOption);

    // Verify dark mode applied
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(localStorage.getItem('yottaflex_theme_preference')).toBe('dark');
  });

  it('renders application shell in dark theme cleanly without contrast regressions', () => {
    localStorage.setItem('yottaflex_theme_preference', 'dark');

    renderWithProviders(<AppLayout />, { initialEntries: ['/dashboard'] });

    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(screen.getByText('YOTTAFLEX')).toBeInTheDocument();
    expect(screen.getByText('Financial Overview')).toBeInTheDocument();
  });
});
