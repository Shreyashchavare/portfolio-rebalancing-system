import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from '@/app/layouts/AppLayout';
import { DashboardPage } from '@/features/dashboard/DashboardPage';
import { PortfoliosPage } from '@/features/portfolios/PortfoliosPage';
import { RebalancingPage } from '@/features/rebalancing/RebalancingPage';
import { ApprovalsPage } from '@/features/approvals/ApprovalsPage';
import { PoliciesPage } from '@/features/policies/PoliciesPage';
import { WorkflowsPage } from '@/features/workflows/WorkflowsPage';
import { SettingsPage } from '@/features/settings/SettingsPage';
import { NotFoundPage } from '@/features/common/NotFoundPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: <DashboardPage />,
      },
      {
        path: 'portfolios',
        element: <PortfoliosPage />,
      },
      {
        path: 'rebalancing',
        element: <RebalancingPage />,
      },
      {
        path: 'approvals',
        element: <ApprovalsPage />,
      },
      {
        path: 'policies',
        element: <PoliciesPage />,
      },
      {
        path: 'workflows',
        element: <WorkflowsPage />,
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
], {
  future: {
    v7_relativeSplatPath: true,
  },
});
