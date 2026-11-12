/**
 * TypeScript types matching backend schemas in app/schemas/policy_rag.py
 */

export interface PolicySearchResult {
  chunk_id: string;
  document_id: string;
  policy_family_id: string | null;
  document_title: string;
  document_version: string;
  section_title: string | null;
  content: string;
  similarity_score: number;
  token_count: number;
  chunk_index: number;
}

export interface PolicySearchRequest {
  query: string;
  as_of_date?: string;
  document_type?: string;
  document_id?: string;
  top_k?: number;
  similarity_threshold?: number;
}

export interface PolicySearchResponse {
  query: string;
  as_of_date?: string | null;
  results: PolicySearchResult[];
  total_results: number;
}

export interface PolicyCitation {
  document_id: string;
  policy_family_id: string | null;
  document_title: string;
  version: string;
  section_title: string | null;
  chunk_id: string;
  excerpt: string | null;
}

export interface PolicyAskRequest {
  query: string;
  as_of_date?: string;
  document_type?: string;
  top_k?: number;
  similarity_threshold?: number;
}

export interface PolicyAskResponse {
  query: string;
  as_of_date: string;
  answer: string;
  has_sufficient_evidence: boolean;
  retrieval_status: 'ANSWERED' | 'INSUFFICIENT_EVIDENCE' | 'LLM_UNAVAILABLE' | 'CONFLICT_DETECTED';
  citations: PolicyCitation[];
  retrieved_chunks: PolicySearchResult[];
  warnings: string[];
  requires_human_review: boolean;
}
