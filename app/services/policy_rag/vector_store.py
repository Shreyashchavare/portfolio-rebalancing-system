"""Vector storage and similarity search engine using relational persistence and NumPy."""

from dataclasses import dataclass
from datetime import date
import json
from typing import List, Optional, Sequence, Union
import numpy as np
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.policy_document import PolicyChunk, PolicyDocument, PolicyStatus
from app.services.policy_rag.embedding_service import BaseEmbeddingService
from app.services.policy_rag.text_chunker import Chunk


@dataclass(frozen=True)
class PolicySearchResult:
    """Retrieved policy chunk result with citation metadata and similarity score."""

    chunk_id: str
    document_id: str
    document_title: str
    document_version: str
    section_title: Optional[str]
    content: str
    similarity_score: float
    token_count: int
    chunk_index: int
    policy_family_id: Optional[str] = None


class VectorStore:
    """Manages document chunk persistence and vectorized similarity retrieval."""

    def __init__(self, session: Session, embedding_service: BaseEmbeddingService) -> None:
        self.session = session
        self.embedding_service = embedding_service

    def store_document_chunks(
        self,
        document: PolicyDocument,
        chunks: List[Chunk],
    ) -> List[PolicyChunk]:
        """Generate embeddings and persist chunks for an ingested policy document.

        Args:
            document: Target PolicyDocument model instance.
            chunks: List of Chunk dataclasses from TextChunker.

        Returns:
            List of persisted PolicyChunk models.
        """
        if not chunks:
            return []

        # Batch generate embeddings
        contents = [c.content for c in chunks]
        embeddings = self.embedding_service.generate_embeddings(contents)

        persisted_chunks: List[PolicyChunk] = []
        for chunk_data, emb in zip(chunks, embeddings):
            chunk_id = f"CHK-{document.id}-{chunk_data.chunk_index:03d}"
            policy_chunk = PolicyChunk(
                id=chunk_id,
                document_id=document.id,
                chunk_index=chunk_data.chunk_index,
                section_title=chunk_data.section_title,
                content=chunk_data.content,
                token_count=chunk_data.token_count,
                embedding_json=json.dumps(emb),
                embedding_model=self.embedding_service.model_name,
            )
            self.session.add(policy_chunk)
            persisted_chunks.append(policy_chunk)

        self.session.flush()
        return persisted_chunks

    def search(
        self,
        query: str,
        as_of_date: Optional[date] = None,
        document_id: Optional[str] = None,
        document_type: Optional[str] = None,
        status: Optional[Union[str, Sequence[str]]] = PolicyStatus.ACTIVE.value,
        top_k: int = 5,
        similarity_threshold: Optional[float] = None,
    ) -> List[PolicySearchResult]:
        """Perform semantic similarity search with temporal and document filtering.

        Args:
            query: Search query text.
            as_of_date: Evaluation date for active policy validity.
            document_id: Optional document ID constraint.
            document_type: Optional document type constraint.
            status: Document lifecycle status (single status or sequence of allowed statuses; None to disable).
            top_k: Maximum number of matches to return.
            similarity_threshold: Optional minimum cosine similarity cutoff.

        Returns:
            Ranked list of PolicySearchResult ordered by similarity descending.
        """
        if not query or not query.strip():
            return []

        # 1. Generate normalized query embedding
        query_vec = np.asarray(
            self.embedding_service.generate_embedding(query.strip()),
            dtype=np.float32,
        )
        q_norm = np.linalg.norm(query_vec)
        if q_norm > 0:
            query_vec = query_vec / q_norm

        # 2. Database query with compliance, status, and embedding model pre-filters
        db_query = (
            self.session.query(PolicyChunk, PolicyDocument)
            .join(PolicyDocument, PolicyChunk.document_id == PolicyDocument.id)
            .filter(PolicyChunk.embedding_model == self.embedding_service.model_name)
        )

        if status is not None:
            if isinstance(status, (list, tuple, set)):
                db_query = db_query.filter(PolicyDocument.status.in_(list(status)))
            else:
                db_query = db_query.filter(PolicyDocument.status == status)

        if document_id is not None:
            db_query = db_query.filter(PolicyDocument.id == document_id)

        if document_type is not None:
            db_query = db_query.filter(PolicyDocument.document_type == document_type)

        if as_of_date is not None:
            db_query = db_query.filter(
                PolicyDocument.effective_from <= as_of_date,
                or_(
                    PolicyDocument.effective_to.is_(None),
                    PolicyDocument.effective_to >= as_of_date,
                ),
            )

        rows = db_query.all()
        if not rows:
            return []

        # 3. Vectorized cosine similarity computation with vector validation
        scored_candidates: List[tuple[float, PolicyChunk, PolicyDocument]] = []
        for chunk, doc in rows:
            try:
                emb = np.asarray(chunk.embedding, dtype=np.float32)
            except Exception:
                # Safely skip chunks with unparseable or malformed embeddings
                continue

            # Reject incompatible dimensions
            if emb.shape != query_vec.shape:
                continue

            # Reject non-finite values (NaN / Inf)
            if np.isnan(emb).any() or np.isinf(emb).any():
                continue

            e_norm = np.linalg.norm(emb)
            if e_norm > 0:
                emb = emb / e_norm
            score = float(np.dot(emb, query_vec))

            if similarity_threshold is not None and score < similarity_threshold:
                continue

            scored_candidates.append((score, chunk, doc))

        # 4. Deterministic sorting: highest score first, chunk.id ascending as tiebreaker
        scored_candidates.sort(key=lambda item: (-item[0], item[1].id))

        # 5. Format top_k results
        results: List[PolicySearchResult] = []
        for score, chunk, doc in scored_candidates[:top_k]:
            results.append(
                PolicySearchResult(
                    chunk_id=chunk.id,
                    document_id=doc.id,
                    document_title=doc.title,
                    document_version=doc.version,
                    section_title=chunk.section_title,
                    content=chunk.content,
                    similarity_score=score,
                    token_count=chunk.token_count,
                    chunk_index=chunk.chunk_index,
                    policy_family_id=doc.policy_family_id,
                )
            )

        return results
