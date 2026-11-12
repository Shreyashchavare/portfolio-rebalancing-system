import { apiRequest } from './client';
import { API_ENDPOINTS } from './endpoints';
import type {
  ApprovalDecisionResponse,
  ApproveProposalRequest,
  RejectProposalRequest,
  AuditListResponse,
} from '@/types/approvals';
import type { RebalanceProposalResponse } from '@/types/rebalancing';

export const approvalService = {
  /**
   * List all rebalancing proposals with optional filtering.
   * Calls GET /api/v1/proposals
   */
  async listProposals(params?: { portfolio_id?: string; status?: string }): Promise<RebalanceProposalResponse[]> {
    return apiRequest<RebalanceProposalResponse[]>({
      method: 'GET',
      url: API_ENDPOINTS.PROPOSALS,
      params,
    });
  },

  /**
   * Retrieve a proposal by ID.
   * Calls GET /api/v1/proposals/{proposal_id}
   */
  async getProposal(proposalId: string): Promise<RebalanceProposalResponse> {
    return apiRequest<RebalanceProposalResponse>({
      method: 'GET',
      url: API_ENDPOINTS.PROPOSAL_BY_ID(encodeURIComponent(proposalId)),
    });
  },

  /**
   * Approve an eligible proposal.
   * Calls POST /api/v1/proposals/{proposal_id}/approve
   */
  async approveProposal(
    proposalId: string,
    payload?: ApproveProposalRequest
  ): Promise<ApprovalDecisionResponse> {
    return apiRequest<ApprovalDecisionResponse>({
      method: 'POST',
      url: API_ENDPOINTS.APPROVE_PROPOSAL(encodeURIComponent(proposalId)),
      data: payload || {},
    });
  },

  /**
   * Reject a proposal with mandatory non-empty reason.
   * Calls POST /api/v1/proposals/{proposal_id}/reject
   */
  async rejectProposal(
    proposalId: string,
    payload: RejectProposalRequest
  ): Promise<ApprovalDecisionResponse> {
    return apiRequest<ApprovalDecisionResponse>({
      method: 'POST',
      url: API_ENDPOINTS.REJECT_PROPOSAL(encodeURIComponent(proposalId)),
      data: payload,
    });
  },

  /**
   * Query the chronological audit event trail for a proposal.
   * Calls GET /api/v1/proposals/{proposal_id}/audit
   */
  async getProposalAudit(proposalId: string): Promise<AuditListResponse> {
    return apiRequest<AuditListResponse>({
      method: 'GET',
      url: API_ENDPOINTS.PROPOSAL_AUDIT(encodeURIComponent(proposalId)),
    });
  },
};
