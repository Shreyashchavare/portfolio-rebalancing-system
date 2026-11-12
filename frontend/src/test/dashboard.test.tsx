import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { DashboardPage } from '@/features/dashboard/DashboardPage';

describe('Dashboard Foundation & Placeholder Integrity', () => {
  it('renders welcome area, title, and architecture disclaimer banner', () => {
    renderWithProviders(<DashboardPage />);

    expect(screen.getByText('Operations Dashboard')).toBeInTheDocument();
    expect(screen.getByText('PHASE 8.2 DUAL THEME')).toBeInTheDocument();
    expect(
      screen.getByText(/Dual Theme Enterprise Architecture Active/i)
    ).toBeInTheDocument();
  });

  it('renders clearly labeled placeholder KPI cards without fabricated financial figures', () => {
    renderWithProviders(<DashboardPage />);

    // Check KPI titles
    expect(screen.getByText('Total Managed AUM')).toBeInTheDocument();
    expect(screen.getByText('Active Portfolios')).toBeInTheDocument();
    expect(screen.getByText('Corridor Drift Alerts')).toBeInTheDocument();
    expect(screen.getByText('Pending Approvals')).toBeInTheDocument();

    // Check placeholder values ($—.— and —)
    expect(screen.getByText('$—.—')).toBeInTheDocument();
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThanOrEqual(3);

    // Check explicit placeholder badges
    expect(screen.getByText('Awaiting Valuation Feed')).toBeInTheDocument();
    expect(screen.getByText('Awaiting Portfolio Store')).toBeInTheDocument();
    expect(screen.getByText('Drift Engine Inactive')).toBeInTheDocument();
    expect(screen.getByText('Governance Queue Idle')).toBeInTheDocument();

    // Invariant: Verify NO fake financial figures are rendered as live data
    expect(screen.queryByText('$1,050,000.00')).not.toBeInTheDocument();
    expect(screen.queryByText('$450,000.00')).not.toBeInTheDocument();
    expect(screen.queryByText('71.4286%')).not.toBeInTheDocument();
  });

  it('renders recent activity and portfolio distribution empty state placeholders', () => {
    renderWithProviders(<DashboardPage />);

    expect(
      screen.getByText('Portfolio Valuation Module Pending')
    ).toBeInTheDocument();
    expect(
      screen.getByText('No Recent Audit Activity Recorded')
    ).toBeInTheDocument();
  });
});
