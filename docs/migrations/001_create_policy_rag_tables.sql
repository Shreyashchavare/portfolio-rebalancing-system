-- Migration 001: Create Policy RAG Tables
-- Database: PostgreSQL
-- Description: Provision policy_documents and policy_chunks tables with indexes and cascade delete.

BEGIN;

CREATE TABLE IF NOT EXISTS policy_documents (
    id VARCHAR(50) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    document_type VARCHAR(50) NOT NULL DEFAULT 'INVESTMENT_POLICY',
    version VARCHAR(20) NOT NULL DEFAULT '1.0',
    effective_from DATE NOT NULL,
    effective_to DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    file_path VARCHAR(500) NOT NULL,
    sha256_checksum VARCHAR(64) NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_policy_doc_type CHECK (document_type IN ('INVESTMENT_POLICY', 'MANDATE', 'ESG_EXCLUSION', 'REGULATORY')),
    CONSTRAINT chk_policy_status CHECK (status IN ('ACTIVE', 'SUPERSEDED', 'DRAFT', 'ARCHIVED')),
    CONSTRAINT chk_policy_effective_dates CHECK (effective_to IS NULL OR effective_from <= effective_to)
);

CREATE INDEX IF NOT EXISTS idx_policy_documents_status ON policy_documents(status);
CREATE INDEX IF NOT EXISTS idx_policy_documents_doc_type ON policy_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_policy_documents_effective ON policy_documents(effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_policy_documents_sha256 ON policy_documents(sha256_checksum);

CREATE TABLE IF NOT EXISTS policy_chunks (
    id VARCHAR(60) PRIMARY KEY,
    document_id VARCHAR(50) NOT NULL REFERENCES policy_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    section_title VARCHAR(255),
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    embedding_json TEXT NOT NULL,
    embedding_model VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_chunk_index_nonnegative CHECK (chunk_index >= 0),
    CONSTRAINT chk_token_count_positive CHECK (token_count > 0)
);

CREATE INDEX IF NOT EXISTS idx_policy_chunks_doc_id ON policy_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_policy_chunks_model ON policy_chunks(embedding_model);

COMMIT;

