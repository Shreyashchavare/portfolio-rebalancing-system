import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { SettingsPage } from '@/features/settings/SettingsPage';
import { QueryProvider } from '@/app/providers/QueryProvider';
import { ThemeProvider } from '@/app/providers/ThemeProvider';
import { AuthProvider } from '@/app/providers/AuthProvider';

function renderSettings() {
  return render(
    <QueryProvider>
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <SettingsPage />
          </BrowserRouter>
        </AuthProvider>
      </ThemeProvider>
    </QueryProvider>
  );
}

describe('Settings Experience — User-Facing Abstraction', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders the Settings workstation header and navigation tabs', () => {
    renderSettings();

    expect(screen.getByRole('heading', { level: 2, name: /System Settings & Configuration/i })).toBeInTheDocument();
    expect(screen.getByText(/INSTITUTIONAL PREFERENCES/i)).toBeInTheDocument();

    // Verify all primary user-facing tabs are present
    expect(screen.getByRole('tab', { name: /^Appearance$/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /^Profile$/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /^Notifications$/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /^Security & Sessions$/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /^About & Support$/i })).toBeInTheDocument();
  });

  it('renders Appearance settings with theme selection and workstation grid density', () => {
    renderSettings();

    // Default tab is Appearance
    expect(screen.getByText(/Display Theme/i)).toBeInTheDocument();
    expect(screen.getByText('Light')).toBeInTheDocument();
    expect(screen.getByText('Dark')).toBeInTheDocument();
    expect(screen.getByText('System')).toBeInTheDocument();

    // Table density controls
    expect(screen.getByText(/Workstation Grid Density/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Normal$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Compact$/i })).toBeInTheDocument();
    expect(screen.getByText(/4 DECIMAL PLACES/i)).toBeInTheDocument();
  });

  it('navigates to Profile tab and displays institutional identity without fake editable inputs', () => {
    renderSettings();

    const profileTab = screen.getByRole('tab', { name: /^Profile$/i });
    fireEvent.click(profileTab);

    expect(screen.getByText(/Account & Institutional Identity/i)).toBeInTheDocument();
    expect(screen.getByText(/Reviewer Identifier/i)).toBeInTheDocument();
    expect(screen.getByText(/Institutional Email/i)).toBeInTheDocument();
    expect(screen.getByText(/Assigned Governance Role/i)).toBeInTheDocument();
    expect(screen.getByText(/Institutional Wealth & Asset Management/i)).toBeInTheDocument();
    expect(screen.getByText(/Enterprise Directory Notice:/i)).toBeInTheDocument();

    // Invariant: zero fake nonfunctional input fields
    expect(screen.queryByPlaceholderText(/enter name/i)).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/edit email/i)).not.toBeInTheDocument();
  });

  it('navigates to Notifications tab and displays compliance audit enforcement', () => {
    renderSettings();

    const notifTab = screen.getByRole('tab', { name: /^Notifications$/i });
    fireEvent.click(notifTab);

    expect(screen.getByText(/Notification Channels & Governance Alerts/i)).toBeInTheDocument();
    expect(screen.getByText(/Rebalancing Approval Requests/i)).toBeInTheDocument();
    expect(screen.getByText(/Compliance Policy Violations/i)).toBeInTheDocument();
    expect(screen.getByText(/Portfolio Valuation Stale Warnings/i)).toBeInTheDocument();
    expect(screen.getByText(/Fiduciary Policy Enforcement:/i)).toBeInTheDocument();

    // Invariant: no fake toggles or disabled dummy switches
    expect(screen.queryByRole('switch')).not.toBeInTheDocument();
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  });

  it('navigates to Security & Sessions tab and verifies safe session data without raw token disclosure', () => {
    renderSettings();

    const securityTab = screen.getByRole('tab', { name: /^Security & Sessions$/i });
    fireEvent.click(securityTab);

    expect(screen.getByText(/Session Security & Access Controls/i)).toBeInTheDocument();
    expect(screen.getByText(/Active Authenticated Session/i)).toBeInTheDocument();
    expect(screen.getByText(/HTTP Authorization Bearer Token/i)).toBeInTheDocument();
    expect(screen.getByText(/Bearer •••••••••••••••• \(Protected Session\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Backend Verified \(FastAPI Security Dependencies\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Password & MFA Management:/i)).toBeInTheDocument();

    // Invariant: no raw secret exposure
    expect(screen.queryByText('dev-reviewer-token')).not.toBeInTheDocument();
    expect(screen.queryByText('dev-admin-token')).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/new password/i)).not.toBeInTheDocument();
  });

  it('navigates to About & Support tab and renders platform release specifications', () => {
    renderSettings();

    const aboutTab = screen.getByRole('tab', { name: /^About & Support$/i });
    fireEvent.click(aboutTab);

    expect(screen.getByText(/About YottaFlex Portfolio Rebalancing System/i)).toBeInTheDocument();
    expect(screen.getByText(/YottaFlex Workstation v0.1.0/i)).toBeInTheDocument();
    expect(screen.getByText(/Deterministic Constraint Solver/i)).toBeInTheDocument();
    expect(screen.getByText(/Mandatory Dual-Key Human-in-the-Loop/i)).toBeInTheDocument();
    expect(screen.getByText(/FastEmbed Vector Retrieval \(ONNX\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Regulatory Compliance & Fiduciary Responsibility:/i)).toBeInTheDocument();
  });

  it('strictly protects raw bearer tokens in System Diagnostics tab', () => {
    renderSettings();

    const diagTab = screen.getByRole('tab', { name: /System Diagnostics/i });
    fireEvent.click(diagTab);

    expect(screen.getByText(/Administrative Technical Diagnostics Area/i)).toBeInTheDocument();
    expect(screen.getByText(/FastAPI Service Connectivity/i)).toBeInTheDocument();
    expect(screen.getByText(/Active Authorization Context/i)).toBeInTheDocument();

    // Verify token masking in diagnostics
    expect(screen.getByText(/Bearer •••••••••••••••• \(Protected Session\)/i)).toBeInTheDocument();

    // Verify that raw bearer tokens are nowhere in the DOM
    expect(screen.queryByText('dev-reviewer-token')).not.toBeInTheDocument();
    expect(screen.queryByText('dev-admin-token')).not.toBeInTheDocument();
    expect(screen.queryByText('dev-viewer-token')).not.toBeInTheDocument();
  });
});
