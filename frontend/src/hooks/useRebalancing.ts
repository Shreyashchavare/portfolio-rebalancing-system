import { useMutation, useQueryClient } from '@tanstack/react-query';
import { rebalancingService } from '@/services/api/rebalancingService';
import type { RebalanceProposalResponse, CreateProposalRequest } from '@/types/rebalancing';

export function useCreateProposal() {
  const queryClient = useQueryClient();

  return useMutation<
    RebalanceProposalResponse,
    Error,
    { portfolioId: string; payload?: CreateProposalRequest; asOfDate?: string }
  >({
    mutationFn: ({ portfolioId, payload, asOfDate }) =>
      rebalancingService.createProposal(portfolioId, payload, asOfDate),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['portfolio', data.portfolio_id] });
      queryClient.setQueryData(['proposal', data.proposal_id], data);
    },
  });
}
