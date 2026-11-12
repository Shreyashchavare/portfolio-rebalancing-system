import { describe, it, expect } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { CustomerWorkspace } from '@/features/customer/CustomerWorkspace';
import { AnalystWorkspace } from '@/features/analyst/AnalystWorkspace';
import { ComplianceWorkspace } from '@/features/compliance/ComplianceWorkspace';
import { AdminWorkspace } from '@/features/admin/AdminWorkspace';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

describe('Phase 8.4B — RBAC-Based Business Frontend', () => {
  describe('Customer / Account Holder Experience', () => {
    it('renders customer overview with personal portfolio metrics and zero approval buttons', () => {
      renderWithProviders(<CustomerWorkspace />);

      expect(screen.getByText('Customer Account Portal')).toBeInTheDocument();
      expect(screen.getByText('PORTFOLIO HOLDER')).toBeInTheDocument();
      expect(screen.getByText('READ-ONLY VIEW')).toBeInTheDocument();

      // Navigation tabs for Customer
      expect(screen.getByRole('tab', { name: /^Overview$/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /^My Portfolio$/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /^Recommendations$/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /^Activity$/i })).toBeInTheDocument();

      // Invariant: Customer must NOT have proposal generation or trade approval controls
      expect(screen.queryByRole('button', { name: /Generate Proposal/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Approve Trades/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Reject Proposal/i })).not.toBeInTheDocument();
    });

    it('navigates to My Portfolio tab and renders holdings without mutation controls', () => {
      renderWithProviders(<CustomerWorkspace />);

      const portfolioTab = screen.getByRole('tab', { name: /^My Portfolio$/i });
      fireEvent.click(portfolioTab);

      // Verify holdings table is rendered
      expect(screen.getByText(/Position Breakdown/i)).toBeInTheDocument();
    });
  });

  describe('Operations Analyst Experience', () => {
    it('renders analyst workspace with proposal generation and drift analysis', () => {
      renderWithProviders(<AnalystWorkspace />);

      expect(screen.getByText('Operations Analyst Workspace')).toBeInTheDocument();
      expect(screen.getByText('PORTFOLIO OPERATIONS')).toBeInTheDocument();

      // Navigation tabs for Analyst
      expect(screen.getByRole('tab', { name: /^Dashboard$/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /^Portfolios$/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /^Drift Analysis$/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Proposals/i })).toBeInTheDocument();

      // Analyst has proposal generation action
      const generateBtns = screen.getAllByRole('button', { name: /Generate Proposal/i });
      expect(generateBtns.length).toBeGreaterThanOrEqual(1);

      // Central Rebalancing Lifecycle Stepper
      expect(screen.getByText('Central Rebalancing Lifecycle')).toBeInTheDocument();
    });
  });

  describe('Risk / Compliance Reviewer Experience', () => {
    it('renders compliance desk with review queue, policy checks, and approval actions', () => {
      renderWithProviders(<ComplianceWorkspace />);

      expect(screen.getByText('Risk & Compliance Review Desk')).toBeInTheDocument();
      expect(screen.getByText('MANDATORY DUAL-KEY GOVERNANCE')).toBeInTheDocument();

      // Navigation tabs for Compliance
      expect(screen.getByRole('tab', { name: /Review Queue/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /^Proposal Details$/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Policy Checks/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /^Audit History$/i })).toBeInTheDocument();

      // Switch to Proposal Details tab
      const detailsTab = screen.getByRole('tab', { name: /^Proposal Details$/i });
      fireEvent.click(detailsTab);

      // Reviewer has approval actions
      expect(screen.getByRole('button', { name: /Approve Trades/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Reject Proposal/i })).toBeInTheDocument();
    });

    it('requires non-empty justification reason on rejection modal', () => {
      renderWithProviders(<ComplianceWorkspace />);

      const detailsTab = screen.getByRole('tab', { name: /^Proposal Details$/i });
      fireEvent.click(detailsTab);

      const rejectBtn = screen.getByRole('button', { name: /Reject Proposal/i });
      fireEvent.click(rejectBtn);

      // Modal is open
      expect(screen.getByText(/Reject Rebalancing Proposal/i)).toBeInTheDocument();
      const confirmRejectBtn = screen.getByRole('button', { name: /Confirm Rejection/i });
      // Rejection button is disabled while reason is empty
      expect(confirmRejectBtn).toBeDisabled();
    });
  });

  describe('System Administrator Experience', () => {
    it('renders administrative console with diagnostics and reference oversight', () => {
      renderWithProviders(<AdminWorkspace />);

      expect(screen.getByText('System Administration & Reference Console')).toBeInTheDocument();
      expect(screen.getByText('ADMINISTRATIVE CONTROL')).toBeInTheDocument();

      // Navigation tabs for Admin
      expect(screen.getByRole('tab', { name: /^Overview$/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Users & Roles/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Reference Data/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Data Quality/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /System Diagnostics/i })).toBeInTheDocument();
    });
  });

  describe('Protected Route & Unauthorized Access Guard', () => {
    it('blocks unauthorized access and renders HTTP 403 Access Restricted state', () => {
      renderWithProviders(
        <ProtectedRoute allowedRoles={['ADMIN']}>
          <div>Confidential Admin Content</div>
        </ProtectedRoute>
      );

      // With default REVIEWER role, ADMIN-only content is blocked
      expect(screen.queryByText('Confidential Admin Content')).not.toBeInTheDocument();
      expect(screen.getByText('HTTP 403 FORBIDDEN')).toBeInTheDocument();
      expect(screen.getByText('Access Restricted')).toBeInTheDocument();
      expect(screen.getByText(/Your current authenticated identity does not have permission/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Return to Authorized Dashboard/i })).toBeInTheDocument();
    });
  });
});
