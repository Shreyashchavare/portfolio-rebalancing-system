/**
 * TypeScript types matching backend schemas in app/schemas/rebalancing.py
 */

export interface ProposedTrade {
  instrument_id: string;
  symbol: string | null;
  instrument_name: string | null;
  asset_class: string;
  trade_side: 'BUY' | 'SELL';
  quantity: string;
  unit_price: string;
  trade_value: string;
  fee_amount: string;
  fee_schedule_id: string | null;
  status: 'PROPOSED' | 'BLOCKED';
  diagnostic: string | null;
}

export interface SimulatedPosition {
  instrument_id: string;
  symbol: string | null;
  instrument_name: string | null;
  asset_class: string;
  pre_trade_quantity: string;
  post_trade_quantity: string;
  unit_price: string;
  post_trade_market_value: string;
  post_trade_weight: string;
}

export interface SimulatedAllocation {
  asset_class: string;
  post_trade_market_value: string;
  post_trade_weight: string;
  target_weight: string;
  post_trade_drift: string;
}

export interface PostTradeSimulationResult {
  pre_trade_portfolio_value: string;
  post_trade_portfolio_value: string;
  pre_trade_cash: string;
  post_trade_cash: string;
  total_executable_fees: string;
  positions: SimulatedPosition[];
  asset_classes: SimulatedAllocation[];
  residual_drifts: Record<string, string>;
}

export interface ConstraintFinding {
  constraint_id: string;
  constraint_name: string;
  constraint_type: string;
  severity: 'HARD' | 'SOFT';
  scope_type: string;
  scope_reference_id: string;
  threshold_value: string | null;
  threshold_unit: string | null;
  is_violated: boolean;
  affected_instrument_id: string | null;
  message: string;
}

export interface TradeResponse {
  trade_id: string;
  proposal_id: string;
  instrument_id: string;
  symbol: string | null;
  instrument_name: string | null;
  asset_class: string;
  trade_side: string;
  quantity: string;
  unit_price: string;
  trade_value: string;
  fee_amount: string;
  fee_schedule_id: string | null;
  status: string;
  diagnostic: string | null;
}

export interface RebalanceProposalResponse {
  proposal_id: string;
  portfolio_id: string;
  as_of_date: string;
  status: 'PENDING_REVIEW' | 'REJECTED' | 'APPROVED' | 'DRAFT';
  review_decision: 'PENDING' | 'REJECTED' | 'APPROVED';
  review_reason: string | null;
  pre_trade_portfolio_value: string;
  post_trade_portfolio_value: string;
  created_at: string;
  trades: TradeResponse[];
  simulation: PostTradeSimulationResult;
  constraint_findings: ConstraintFinding[];
  warnings: string[];
  is_executable: boolean;
  requires_human_review: boolean;
}

export interface CreateProposalRequest {
  as_of_date?: string;
}
