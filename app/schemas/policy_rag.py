"""Pydantic schemas for Policy RAG ingestion, documents, chunks, retrieval, and Q&A."""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PolicyDocumentMetadata(BaseModel):
    """Metadata supplied or extracted during policy document ingestion."""

    policy_family_id: Optional[str] = Field(None, max_length=50, description="Stable identifier for the policy family (e.g. FAM-EQUITY-GLOBAL)")
    title: str = Field(..., min_length=1, max_length=255, description="Document display title")
    document_type: str = Field("INVESTMENT_POLICY", description="Document classification (e.g. INVESTMENT_POLICY, MANDATE)")
    version: str = Field("1.0", max_length=20, description="Semantic or numeric document version")
    effective_from: date = Field(..., description="Date from which the policy becomes active")
    effective_to: Optional[date] = Field(None, description="Date on which the policy expires, or None if ongoing")
    status: str = Field("ACTIVE", description="Lifecycle status (ACTIVE, SUPERSEDED, DRAFT, ARCHIVED)")

    model_config = ConfigDict(from_attributes=True)


class PolicyIngestRequest(BaseModel):
    """Request payload for ingesting a policy document."""

    policy_family_id: Optional[str] = Field(None, max_length=50, description="Optional stable identifier for the policy family")
    title: str = Field(..., min_length=1, max_length=255, description="Display title of the policy")
    document_type: str = Field("INVESTMENT_POLICY", description="Classification of the document")
    version: str = Field("1.0", max_length=20, description="Document version number")
    effective_from: date = Field(..., description="Active start date")
    effective_to: Optional[date] = Field(None, description="Expiry date, or None if ongoing")
    status: str = Field("ACTIVE", description="Lifecycle status")
    file_path: str = Field(..., min_length=1, description="Path to the document file")


class PolicyIngestResponse(BaseModel):
    """Response returned upon successful document ingestion."""

    id: str
    policy_family_id: Optional[str] = None
    title: str
    filename: str
    document_type: str
    version: str
    chunk_count: int
    sha256_checksum: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolicyChunkResponse(BaseModel):
    """Schema representing an individual retrieved or persisted chunk."""

    id: str
    document_id: str
    chunk_index: int
    section_title: Optional[str] = None
    content: str
    token_count: int
    embedding_model: str

    model_config = ConfigDict(from_attributes=True)


class PolicyChunkSummary(BaseModel):
    """Safe chunk summary without raw embedding vectors."""

    id: str
    chunk_index: int
    section_title: Optional[str] = None
    token_count: int
    content_preview: str

    model_config = ConfigDict(from_attributes=True)


class PolicyDocumentResponse(BaseModel):
    """Schema representing a registered policy document with chunk count."""

    id: str
    policy_family_id: Optional[str] = None
    filename: str
    title: str
    document_type: str
    version: str
    effective_from: date
    effective_to: Optional[date] = None
    status: str
    sha256_checksum: str
    uploaded_at: datetime
    chunk_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class PolicyDocumentDetailResponse(BaseModel):
    """Detailed policy document representation with chunk list (no raw embeddings or sensitive paths)."""

    id: str
    policy_family_id: Optional[str] = None
    title: str
    filename: str
    document_type: str
    version: str
    effective_from: date
    effective_to: Optional[date] = None
    status: str
    sha256_checksum: str
    uploaded_at: datetime
    chunk_count: int
    chunks: List[PolicyChunkSummary] = []

    model_config = ConfigDict(from_attributes=True)


class PolicySearchResult(BaseModel):
    """Grounded semantic search result item with citation details."""

    chunk_id: str
    document_id: str
    policy_family_id: Optional[str] = None
    document_title: str
    document_version: str
    section_title: Optional[str] = None
    content: str
    similarity_score: float
    token_count: int
    chunk_index: int = 0

    model_config = ConfigDict(from_attributes=True)


class PolicySearchRequest(BaseModel):
    """Semantic search query request with compliance filters."""

    query: str = Field(..., min_length=1, description="Natural language search query")
    as_of_date: Optional[date] = Field(None, description="As-of evaluation date for temporal policy filtering")
    document_type: Optional[str] = Field(None, description="Optional document type filter")
    document_id: Optional[str] = Field(None, description="Optional document ID filter")
    top_k: int = Field(5, ge=1, le=50, description="Maximum number of chunks to return")
    similarity_threshold: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Minimum cosine similarity cutoff")


class PolicySearchResponse(BaseModel):
    """Response returned from semantic policy search."""

    query: str
    as_of_date: Optional[date] = None
    results: List[PolicySearchResult]
    total_results: int

    model_config = ConfigDict(from_attributes=True)


class PolicyCitation(BaseModel):
    """Validated citation referencing an actual retrieved document chunk."""

    document_id: str
    policy_family_id: Optional[str] = None
    document_title: str
    version: str
    section_title: Optional[str] = None
    chunk_id: str
    excerpt: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PolicyAskRequest(BaseModel):
    """Natural language question request grounded in active policy documents."""

    query: str = Field(..., min_length=1, description="Policy question to evaluate")
    as_of_date: Optional[date] = Field(None, description="Compliance date for policy validity (defaults to today)")
    document_type: Optional[str] = Field(None, description="Optional document type filter")
    top_k: int = Field(5, ge=1, le=20, description="Maximum number of chunks to retrieve for context")
    similarity_threshold: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Similarity threshold cutoff")


class PolicyAskResponse(BaseModel):
    """Structured response to a policy question with grounded citations."""

    query: str
    as_of_date: date
    answer: str
    has_sufficient_evidence: bool
    retrieval_status: str = Field(..., description="ANSWERED, INSUFFICIENT_EVIDENCE, LLM_UNAVAILABLE, or CONFLICT_DETECTED")
    citations: List[PolicyCitation] = []
    retrieved_chunks: List[PolicySearchResult] = []
    warnings: List[str] = []
    requires_human_review: bool = False

    model_config = ConfigDict(from_attributes=True)


# Backwards compatibility alias
PolicyQueryRequest = PolicySearchRequest
