-- Migration 002: Add policy_family_id to policy_documents
-- Database: PostgreSQL
-- Description: Add policy_family_id column and index for stable policy family identity and conflict detection.

BEGIN;

-- 1. Add policy_family_id column (nullable to safely preserve existing legacy records)
ALTER TABLE policy_documents 
ADD COLUMN IF NOT EXISTS policy_family_id VARCHAR(50);

-- 2. Create index on policy_family_id for fast family lookups and conflict detection
CREATE INDEX IF NOT EXISTS idx_policy_documents_family_id 
ON policy_documents(policy_family_id);

COMMIT;

