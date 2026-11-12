/**
 * Permitted reviewer roles recognized by the backend governance layer.
 * Mirrors PERMITTED_APPROVAL_ROLES and RoleEnum in the FastAPI application.
 */
export type ReviewerRole =
  | 'PORTFOLIO_MANAGER'
  | 'COMPLIANCE_OFFICER'
  | 'ADMIN'
  | 'REVIEWER'
  | 'VIEWER';

export type BusinessPersona =
  | 'CUSTOMER'
  | 'ANALYST'
  | 'COMPLIANCE'
  | 'ADMIN';

export interface ReviewerContext {
  reviewer_id: string;
  role: ReviewerRole;
  email: string;
  persona?: BusinessPersona;
}

export interface DevMockTokenOption {
  token: string;
  label: string;
  role: ReviewerRole;
  persona: BusinessPersona;
  reviewerId: string;
  description: string;
}

export const DEV_MOCK_TOKENS: DevMockTokenOption[] = [
  {
    token: 'dev-viewer-token',
    label: 'Customer / Account Holder',
    role: 'VIEWER',
    persona: 'CUSTOMER',
    reviewerId: 'REV-DEV-VIEWER',
    description: 'Read-only portfolio health, holdings, target allocations, and recommendation view.',
  },
  {
    token: 'dev-analyst-token',
    label: 'Operations Analyst',
    role: 'PORTFOLIO_MANAGER',
    persona: 'ANALYST',
    reviewerId: 'REV-DEV-ANALYST',
    description: 'Portfolio drift analysis, deterministic proposal generation, and trade simulation.',
  },
  {
    token: 'dev-reviewer-token',
    label: 'Risk / Compliance Reviewer',
    role: 'REVIEWER',
    persona: 'COMPLIANCE',
    reviewerId: 'REV-DEV-01',
    description: 'Fiduciary review queue, IPS policy constraint verification, approval and rejection.',
  },
  {
    token: 'dev-admin-token',
    label: 'System Administrator',
    role: 'ADMIN',
    persona: 'ADMIN',
    reviewerId: 'REV-DEV-ADMIN',
    description: 'System health diagnostics, operational oversight, and reference data validation.',
  },
];

export function getPersonaFromRole(role?: ReviewerRole): BusinessPersona {
  switch (role) {
    case 'VIEWER':
      return 'CUSTOMER';
    case 'PORTFOLIO_MANAGER':
      return 'ANALYST';
    case 'COMPLIANCE_OFFICER':
    case 'REVIEWER':
      return 'COMPLIANCE';
    case 'ADMIN':
      return 'ADMIN';
    default:
      return 'CUSTOMER';
  }
}
