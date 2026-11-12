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
import { CustomerWorkspace } from '@/features/customer/CustomerWorkspace';
import { AnalystWorkspace } from '@/features/analyst/AnalystWorkspace';
import { ComplianceWorkspace } from '@/features/compliance/ComplianceWorkspace';
import { AdminWorkspace } from '@/features/admin/AdminWorkspace';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

export const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: <Navigate to="/dashboard" replace />,
        },
        // Main Core Business Routes
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
          element: (
            <ProtectedRoute allowedRoles={['ADMIN', 'REVIEWER', 'COMPLIANCE_OFFICER']}>
              <ApprovalsPage />
            </ProtectedRoute>
          ),
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

        // Persona-Specific Workspaces
        {
          path: 'customer/*',
          element: <CustomerWorkspace />,
        },
        {
          path: 'analyst/*',
          element: (
            <ProtectedRoute allowedRoles={['ADMIN', 'REVIEWER', 'PORTFOLIO_MANAGER']} allowedPersonas={['ANALYST', 'ADMIN']}>
              <AnalystWorkspace />
            </ProtectedRoute>
          ),
        },
        {
          path: 'compliance/*',
          element: (
            <ProtectedRoute allowedRoles={['ADMIN', 'REVIEWER', 'COMPLIANCE_OFFICER']} allowedPersonas={['COMPLIANCE', 'ADMIN']}>
              <ComplianceWorkspace />
            </ProtectedRoute>
          ),
        },
        {
          path: 'admin/*',
          element: (
            <ProtectedRoute allowedRoles={['ADMIN']} allowedPersonas={['ADMIN']}>
              <AdminWorkspace />
            </ProtectedRoute>
          ),
        },

        // Catch-all 404
        {
          path: '*',
          element: <NotFoundPage />,
        },
      ],
    },
  ],
  {
    future: {
      v7_relativeSplatPath: true,
    },
  }
);
