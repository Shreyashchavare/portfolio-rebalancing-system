-- Migration 003: Add Orchestration and Audit Tables
-- Database: PostgreSQL
-- Description: Provision workflow_runs and audit_events tables with constraints, foreign keys, and indexes.

BEGIN;

-- 1. Create workflow_runs table
CREATE TABLE IF NOT EXISTS workflow_runs (
    id VARCHAR(50) PRIMARY KEY,
    portfolio_id VARCHAR(40) NOT NULL REFERENCES portfolio(portfolio_id),
    proposal_id VARCHAR(30) REFERENCES rebalance_proposal(proposal_id),
    status VARCHAR(30) NOT NULL,
    request_key VARCHAR(100) NOT NULL,
    request_payload JSONB,
    result_payload JSONB,
    error_code VARCHAR(50),
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_workflow_runs_portfolio_request_key UNIQUE (portfolio_id, request_key),
    CONSTRAINT check_workflow_run_status_valid CHECK (
        status IN (
            'RECEIVED', 'VALIDATING', 'ANALYZING', 'GENERATING_PROPOSAL',
            'RETRIEVING_POLICIES', 'GENERATING_EXPLANATION', 'PENDING_HUMAN_REVIEW',
            'APPROVED', 'REJECTED', 'COMPLETED', 'FAILED', 'REQUIRES_ATTENTION'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_workflow_runs_portfolio_id ON workflow_runs(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_proposal_id ON workflow_runs(proposal_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_request_key ON workflow_runs(request_key);

-- 2. Create audit_events table
CREATE TABLE IF NOT EXISTS audit_events (
    event_id VARCHAR(50) PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    decision VARCHAR(20),
    actor_id VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(50) NOT NULL,
    portfolio_id VARCHAR(40) REFERENCES portfolio(portfolio_id),
    proposal_id VARCHAR(30) REFERENCES rebalance_proposal(proposal_id),
    workflow_id VARCHAR(50) REFERENCES workflow_runs(id),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,
    metadata_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_audit_events_event_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_action ON audit_events(action);
CREATE INDEX IF NOT EXISTS idx_audit_events_actor_id ON audit_events(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_entity ON audit_events(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_portfolio_id ON audit_events(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_proposal_id ON audit_events(proposal_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_workflow_id ON audit_events(workflow_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(timestamp);

COMMIT;

