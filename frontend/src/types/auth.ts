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

export interface ReviewerContext {
  reviewer_id: string;
  role: ReviewerRole;
  email: string;
}

export interface DevMockTokenOption {
  token: string;
  label: string;
  role: ReviewerRole;
  reviewerId: string;
  description: string;
}

export const DEV_MOCK_TOKENS: DevMockTokenOption[] = [
  {
    token: 'dev-reviewer-token',
    label: 'Standard Reviewer',
    role: 'REVIEWER',
    reviewerId: 'REV-DEV-01',
    description: 'Permitted to review, approve, and reject rebalancing proposals.',
  },
  {
    token: 'dev-admin-token',
    label: 'System Administrator',
    role: 'ADMIN',
    reviewerId: 'REV-DEV-ADMIN',
    description: 'Full administrative override and governance permissions.',
  },
  {
    token: 'dev-viewer-token',
    label: 'Read-Only Viewer',
    role: 'VIEWER',
    reviewerId: 'REV-DEV-VIEWER',
    description: 'Read-only access. Governance approval actions return HTTP 403 Forbidden.',
  },
];
