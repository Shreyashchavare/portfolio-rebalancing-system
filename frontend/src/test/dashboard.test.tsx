import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { DashboardPage } from '@/features/dashboard/DashboardPage';

describe('Role-Aware Business Dashboard (Phase 8.4B)', () => {
  it('renders role-aware compliance workspace for default reviewer persona', () => {
    renderWithProviders(<DashboardPage />);

    // Header and role-specific workspace title
    expect(screen.getByText('Risk & Compliance Review Desk')).toBeInTheDocument();
    expect(screen.getByText('MANDATORY DUAL-KEY GOVERNANCE')).toBeInTheDocument();

    // Central 8-stage Rebalancing Lifecycle Stepper
    expect(screen.getByText('Central Rebalancing Lifecycle')).toBeInTheDocument();
    expect(screen.getByText(/STAGE 6 OF 8/i)).toBeInTheDocument();
  });

  it('renders pending governance proposal queue with inspection controls', () => {
    renderWithProviders(<DashboardPage />);

    expect(screen.getByText('Pending Proposal Governance Worklist')).toBeInTheDocument();
    expect(screen.getByText('PROP-DEMO-01')).toBeInTheDocument();
    expect(screen.getByText('PENDING HUMAN REVIEW')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Inspect & Decide/i })).toBeInTheDocument();
  });

  it('strictly excludes removed redundant modules and placeholder banners', () => {
    renderWithProviders(<DashboardPage />);

    // Invariant: Redundant "Core System Modules" box has been removed
    expect(screen.queryByText('Core System Modules')).not.toBeInTheDocument();

    // Invariant: Static architecture disclaimer banner has been removed
    expect(screen.queryByText(/Dual Theme Enterprise Architecture Active/i)).not.toBeInTheDocument();

    // Invariant: Unwired placeholders ($—.—) have been replaced with live records
    expect(screen.queryByText('$—.—')).not.toBeInTheDocument();
  });
});
