/**
 * TypeScript types matching backend schemas in app/schemas/approval.py and app/schemas/audit.py
 */

export interface ApproveProposalRequest {
  notes?: string;
}

export interface RejectProposalRequest {
  reason: string;
}

export interface ApprovalDecisionResponse {
  proposal_id: string;
  status: string;
  review_decision: string;
  reviewer_id: string;
  reviewed_at: string;
  review_reason: string | null;
  approved_trade_count: number;
  rejected_trade_count: number;
  blocked_trade_count: number;
}

export interface AuditEventResponse {
  event_id: string;
  event_type: string;
  action: string;
  decision: string | null;
  actor_id: string;
  entity_type: string;
  entity_id: string;
  portfolio_id: string | null;
  proposal_id: string | null;
  workflow_id: string | null;
  timestamp: string;
  reason: string | null;
  metadata_json: Record<string, unknown> | null;
}

export interface AuditListResponse {
  events: AuditEventResponse[];
  total_count: number;
}
