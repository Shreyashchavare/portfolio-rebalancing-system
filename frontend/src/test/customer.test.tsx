import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from './test-utils';
import { CustomerWorkspace } from '@/features/customer/CustomerWorkspace';

describe('CustomerWorkspace & Rebalancing Lifecycle Integrity (TDD)', () => {
  it('renders Customer Account Portal with correct header and investor badge', () => {
    renderWithProviders(<CustomerWorkspace />, { initialEntries: ['/customer?tab=overview'] });

    expect(screen.getByText('Customer Account Portal')).toBeInTheDocument();
    expect(screen.getByText('PORTFOLIO HOLDER')).toBeInTheDocument();
    expect(screen.getByText(/Personal wealth account/i)).toBeInTheDocument();
  });

  it('renders all four primary workspace tabs: overview, portfolio, recommendations, and activity', () => {
    renderWithProviders(<CustomerWorkspace />);

    expect(screen.getByRole('tab', { name: /Overview/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /My Portfolio/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Recommendations/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Activity/i })).toBeInTheDocument();
  });

  it('renders Central Rebalancing Lifecycle Stepper in activity tab', () => {
    renderWithProviders(<CustomerWorkspace />, { initialEntries: ['/customer?tab=activity'] });

    expect(screen.getByText('Central Rebalancing Lifecycle')).toBeInTheDocument();
    expect(screen.getByText(/Deterministic 8-stage pipeline/i)).toBeInTheDocument();
    expect(screen.getByText('Portfolio Selection')).toBeInTheDocument();
    expect(screen.getByText('Audit Traceability')).toBeInTheDocument();
  });

  it('allows switching customer profile via the profile dropdown', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CustomerWorkspace />);

    const select = screen.getByLabelText('Select Customer Account');
    expect(select).toBeInTheDocument();
    expect(select).toHaveValue('PORT-INV-000001-02');

    await user.selectOptions(select, 'PORT-INV-000002-01');
    expect(select).toHaveValue('PORT-INV-000002-01');
  });
});
