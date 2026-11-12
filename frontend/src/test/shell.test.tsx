import { describe, it, expect } from 'vitest';
import { screen, fireEvent, within } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { AppLayout } from '@/app/layouts/AppLayout';

describe('Application Shell & Responsive Navigation', () => {
  it('renders enterprise brand header and all sidebar navigation items', () => {
    renderWithProviders(<AppLayout />, { initialEntries: ['/dashboard'] });

    expect(screen.getByText('YOTTAFLEX')).toBeInTheDocument();
    expect(screen.getByText('Rebalancing Core')).toBeInTheDocument();

    const mainNav = screen.getByRole('navigation', { name: /Main Navigation/i });
    expect(within(mainNav).getByRole('link', { name: /^Dashboard$/i })).toBeInTheDocument();
    expect(within(mainNav).getByRole('link', { name: /^Portfolios$/i })).toBeInTheDocument();
    expect(within(mainNav).getByRole('link', { name: /^Rebalancing$/i })).toBeInTheDocument();
    expect(within(mainNav).getByRole('link', { name: /^Approvals$/i })).toBeInTheDocument();
    expect(within(mainNav).getByRole('link', { name: /^Policy RAG$/i })).toBeInTheDocument();
    expect(within(mainNav).getByRole('link', { name: /^Workflows$/i })).toBeInTheDocument();
    expect(within(mainNav).getByRole('link', { name: /^Settings$/i })).toBeInTheDocument();
  });

  it('toggles sidebar collapse state on desktop', () => {
    renderWithProviders(<AppLayout />, { initialEntries: ['/dashboard'] });

    const collapseBtn = screen.getByRole('button', { name: /Collapse sidebar/i });
    expect(collapseBtn).toBeInTheDocument();

    fireEvent.click(collapseBtn);
    expect(screen.getByRole('button', { name: /Expand sidebar/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Expand sidebar/i }));
    expect(screen.getByRole('button', { name: /Collapse sidebar/i })).toBeInTheDocument();
  });

  it('toggles mobile sidebar drawer via hamburger menu', () => {
    const { container } = renderWithProviders(<AppLayout />, { initialEntries: ['/dashboard'] });

    // Initially mobile backdrop is not present
    expect(container.querySelector('.fixed.inset-0.z-40')).toBeNull();

    const mobileMenuBtn = screen.getByRole('button', { name: /Open sidebar navigation/i });
    expect(mobileMenuBtn).toBeInTheDocument();

    // Open mobile sidebar
    fireEvent.click(mobileMenuBtn);
    expect(container.querySelector('.fixed.inset-0.z-40')).not.toBeNull();

    // Close via close button
    const closeBtn = screen.getByRole('button', { name: /Close navigation/i });
    fireEvent.click(closeBtn);
    expect(container.querySelector('.fixed.inset-0.z-40')).toBeNull();
  });

  it('displays the active reviewer identity and role in the top header', () => {
    renderWithProviders(<AppLayout />, { initialEntries: ['/dashboard'] });

    // In dev / test mode, default reviewer REV-DEV-01 and role REVIEWER are rendered
    expect(screen.getByText(/REV-DEV-01/i)).toBeInTheDocument();
    expect(screen.getByText(/REVIEWER/i)).toBeInTheDocument();
  });
});
