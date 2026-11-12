/**
 * Declarative API endpoints matching the YottaFlex FastAPI backend contract.
 * Note: Core /health is at the root level, whereas business modules reside under /api/v1.
 */
export const API_ENDPOINTS = {
  // Core Health
  HEALTH: '/health',

  // Portfolio Analytics
  PORTFOLIO_VALUATION: (portfolioId: string) => `/api/v1/portfolios/${portfolioId}/valuation`,
  PORTFOLIO_DRIFT: (portfolioId: string) => `/api/v1/portfolios/${portfolioId}/drift`,

  // Deterministic Rebalancing Engine
  CREATE_PROPOSAL: (portfolioId: string) => `/api/v1/portfolios/${portfolioId}/rebalance/proposals`,

  // Policy RAG & Semantic Retrieval
  POLICY_INGEST: '/api/v1/policies/ingest',
  POLICY_SEARCH: '/api/v1/policies/search',
  POLICY_ASK: '/api/v1/policies/ask',
  POLICY_DETAIL: (documentId: string) => `/api/v1/policies/${documentId}`,

  // Workflow Orchestration
  WORKFLOWS: '/api/v1/workflows',
  WORKFLOW_BY_ID: (workflowId: string) => `/api/v1/workflows/${workflowId}`,

  // Proposal Governance & Durable Audit Trail
  APPROVE_PROPOSAL: (proposalId: string) => `/api/v1/proposals/${proposalId}/approve`,
  REJECT_PROPOSAL: (proposalId: string) => `/api/v1/proposals/${proposalId}/reject`,
  PROPOSAL_AUDIT: (proposalId: string) => `/api/v1/proposals/${proposalId}/audit`,
} as const;
