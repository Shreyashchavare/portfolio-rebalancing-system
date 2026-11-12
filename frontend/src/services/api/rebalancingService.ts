import { apiRequest } from './client';
import { API_ENDPOINTS } from './endpoints';
import type { RebalanceProposalResponse, CreateProposalRequest } from '@/types/rebalancing';

export const rebalancingService = {
  /**
   * Generate, simulate, and persist a policy-constrained rebalancing proposal.
   * Calls POST /api/v1/portfolios/{portfolio_id}/rebalance/proposals
   */
  async createProposal(
    portfolioId: string,
    payload?: CreateProposalRequest,
    asOfDate?: string
  ): Promise<RebalanceProposalResponse> {
    const params = asOfDate ? { as_of_date: asOfDate } : undefined;
    return apiRequest<RebalanceProposalResponse>({
      method: 'POST',
      url: API_ENDPOINTS.CREATE_PROPOSAL(encodeURIComponent(portfolioId)),
      params,
      data: payload || {},
    });
  },
};
