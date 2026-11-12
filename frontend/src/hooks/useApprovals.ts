import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { approvalService } from '@/services/api/approvalService';
import type {
  ApprovalDecisionResponse,
  ApproveProposalRequest,
  RejectProposalRequest,
  AuditListResponse,
} from '@/types/approvals';

export function useApproveProposal() {
  const queryClient = useQueryClient();

  return useMutation<
    ApprovalDecisionResponse,
    Error,
    { proposalId: string; payload?: ApproveProposalRequest }
  >({
    mutationFn: ({ proposalId, payload }) =>
      approvalService.approveProposal(proposalId, payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['proposal', data.proposal_id] });
      queryClient.invalidateQueries({ queryKey: ['audit', data.proposal_id] });
    },
  });
}

export function useRejectProposal() {
  const queryClient = useQueryClient();

  return useMutation<
    ApprovalDecisionResponse,
    Error,
    { proposalId: string; payload: RejectProposalRequest }
  >({
    mutationFn: ({ proposalId, payload }) =>
      approvalService.rejectProposal(proposalId, payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['proposal', data.proposal_id] });
      queryClient.invalidateQueries({ queryKey: ['audit', data.proposal_id] });
    },
  });
}

export function useProposalAudit(proposalId?: string) {
  return useQuery<AuditListResponse, Error>({
    queryKey: ['audit', proposalId],
    queryFn: () => approvalService.getProposalAudit(proposalId!),
    enabled: Boolean(proposalId),
    staleTime: 10_000,
  });
}

export function useProposal(proposalId?: string) {
  return useQuery({
    queryKey: ['proposal', proposalId],
    queryFn: () => approvalService.getProposal(proposalId!),
    enabled: Boolean(proposalId && !proposalId.startsWith('PROP-DEMO')),
    staleTime: 10_000,
    retry: false,
  });
}

export function useProposals(params?: { portfolio_id?: string; status?: string }) {
  return useQuery({
    queryKey: ['proposals', params?.portfolio_id || 'all', params?.status || 'all'],
    queryFn: () => approvalService.listProposals(params),
    staleTime: 10_000,
  });
}
