import type { RebalanceProposalResponse } from './rebalancing';
import type { PolicySearchResult } from './policies';

export type WorkflowStatus =
  | 'RECEIVED'
  | 'VALIDATING'
  | 'ANALYZING'
  | 'GENERATING_PROPOSAL'
  | 'RETRIEVING_POLICIES'
  | 'GENERATING_EXPLANATION'
  | 'PENDING_HUMAN_REVIEW'
  | 'APPROVED'
  | 'REJECTED'
  | 'COMPLETED'
  | 'FAILED'
  | 'REQUIRES_ATTENTION';

export interface WorkflowRequest {
  portfolio_id: string;
  as_of_date?: string;
  request_key: string;
  policy_query?: string;
}

export interface WorkflowResponse {
  workflow_id: string;
  portfolio_id: string;
  as_of_date: string;
  status: WorkflowStatus;
  request_key: string;
  proposal_id?: string | null;
  proposal?: RebalanceProposalResponse | null;
  explanation?: {
    summary: string;
    trade_rationales: Record<string, string>;
  } | null;
  policy_evidence: PolicySearchResult[];
  warnings: string[];
  errors: string[];
  requires_human_review: boolean;
  error_code?: string | null;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}
