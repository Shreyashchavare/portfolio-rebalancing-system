import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { render } from '@testing-library/react';
import { QueryProvider } from '@/app/providers/QueryProvider';
import { ThemeProvider } from '@/app/providers/ThemeProvider';
import { AuthProvider } from '@/app/providers/AuthProvider';
import { AppLayout } from '@/app/layouts/AppLayout';
import { DashboardPage } from '@/features/dashboard/DashboardPage';
import { PortfoliosPage } from '@/features/portfolios/PortfoliosPage';
import { RebalancingPage } from '@/features/rebalancing/RebalancingPage';
import { ApprovalsPage } from '@/features/approvals/ApprovalsPage';
import { PoliciesPage } from '@/features/policies/PoliciesPage';
import { WorkflowsPage } from '@/features/workflows/WorkflowsPage';
import { SettingsPage } from '@/features/settings/SettingsPage';
import { NotFoundPage } from '@/features/common/NotFoundPage';

function renderRoute(path: string) {
  const router = createMemoryRouter(
    [
      {
        path: '/',
        element: <AppLayout />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: 'dashboard', element: <DashboardPage /> },
          { path: 'portfolios', element: <PortfoliosPage /> },
          { path: 'rebalancing', element: <RebalancingPage /> },
          { path: 'approvals', element: <ApprovalsPage /> },
          { path: 'policies', element: <PoliciesPage /> },
          { path: 'workflows', element: <WorkflowsPage /> },
          { path: 'settings', element: <SettingsPage /> },
          { path: '*', element: <NotFoundPage /> },
        ],
      },
    ],
    {
      initialEntries: [path],
      future: {
        v7_relativeSplatPath: true,
      },
    }
  );

  return render(
    <QueryProvider>
      <ThemeProvider>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </ThemeProvider>
    </QueryProvider>
  );
}

describe('Navigation Router Routes', () => {
  it('renders DashboardPage at /dashboard', () => {
    renderRoute('/dashboard');
    expect(screen.getByRole('heading', { level: 2, name: /Operations Dashboard/i })).toBeInTheDocument();
  });

  it('renders PortfoliosPage at /portfolios', () => {
    renderRoute('/portfolios');
    expect(screen.getByRole('heading', { level: 2, name: /Portfolio Management/i })).toBeInTheDocument();
    expect(screen.getByText(/Asset Class Allocation & Drift Comparison/i)).toBeInTheDocument();
  });

  it('renders RebalancingPage at /rebalancing', () => {
    renderRoute('/rebalancing');
    expect(screen.getByRole('heading', { level: 2, name: /Rebalancing Engine/i })).toBeInTheDocument();
    expect(screen.getByText(/Deterministic Proposed Trade Tickets/i)).toBeInTheDocument();
  });

  it('renders ApprovalsPage at /approvals', () => {
    renderRoute('/approvals');
    expect(screen.getByRole('heading', { level: 2, name: /Governance & Approvals/i })).toBeInTheDocument();
    expect(screen.getByText(/Proposal Verification & Authorization Action/i)).toBeInTheDocument();
  });

  it('renders PoliciesPage at /policies', () => {
    renderRoute('/policies');
    expect(screen.getByRole('heading', { level: 2, name: /Compliance Policy RAG/i })).toBeInTheDocument();
    expect(screen.getByText(/Grounded Compliance Question Answering/i)).toBeInTheDocument();
  });

  it('renders WorkflowsPage at /workflows', () => {
    renderRoute('/workflows');
    expect(screen.getByRole('heading', { level: 2, name: /Workflow Orchestration/i })).toBeInTheDocument();
    expect(screen.getByText(/Execution State Machine Transition Pipeline/i)).toBeInTheDocument();
  });

  it('renders SettingsPage at /settings', () => {
    renderRoute('/settings');
    expect(screen.getByRole('heading', { level: 2, name: /System Settings & Configuration/i })).toBeInTheDocument();
  });

  it('renders NotFoundPage on unknown route /unknown-route-xyz', () => {
    renderRoute('/unknown-route-xyz');
    expect(screen.getByText('404')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /Page Not Found/i })).toBeInTheDocument();
    expect(screen.getByText(/The requested URL path does not correspond/i)).toBeInTheDocument();
  });
});
