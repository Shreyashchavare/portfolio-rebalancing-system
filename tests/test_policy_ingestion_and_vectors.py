"""Tests for Policy RAG Ingestion, Chunking, Local Embeddings, and Vector Storage.

Following strict TDD, these tests define and verify:
1. Document text extraction (PDF, TXT, Markdown) with security and validation.
2. Deterministic heading-aware text chunking.
3. Local and fake embedding services with normalization and dimension validation.
4. PolicyDocument and PolicyChunk database models and cascade persistence.
5. VectorStore with NumPy cosine similarity search and temporal/status pre-filtering.
"""

from datetime import date, datetime, timezone
import json
from pathlib import Path
import tempfile
import numpy as np
import pytest
from pypdf import PdfWriter
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.policy_document import (
    PolicyChunk,
    PolicyDocument,
    PolicyDocumentType,
    PolicyStatus,
)
from app.services.policy_rag.document_extractor import (
    CorruptDocumentError,
    DocumentExtractionError,
    DocumentExtractor,
    DocumentNotFoundError,
    DocumentSizeLimitExceededError,
    EmptyDocumentError,
    ExtractedDocument,
    PathTraversalError,
    UnsupportedFileTypeError,
)
from app.services.policy_rag.embedding_service import (
    BaseEmbeddingService,
    EmbeddingModelError,
    EmbeddingService,
    FakeEmbeddingService,
)
from app.services.policy_rag.text_chunker import Chunk, TextChunker
from app.services.policy_rag.vector_store import PolicySearchResult, VectorStore


# ============================================================================
# Helpers & Database Fixture
# ============================================================================

def _create_sqlite_session() -> Session:
    """Create an in-memory SQLite database session with foreign keys enabled."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return Session(engine)


def _create_sample_pdf(file_path: Path, text_content: str) -> None:
    """Create a minimal valid PDF file with text content using pypdf."""
    # pypdf's PdfWriter can write a blank page or we can use basic PDF structure
    # Alternatively write basic raw PDF stream
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    # To include extractable text, write text annotation or standard PDF text stream
    # A standard raw minimal PDF with text:
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length 55 >> stream\n"
        b"BT /F1 12 Tf 72 712 Td (" + text_content.encode("ascii", errors="replace") + b") Tj ET\n"
        b"endstream\nendobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000372 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\n"
        b"startxref\n452\n%%EOF\n"
    )
    with open(file_path, "wb") as f:
        f.write(pdf_content)


# ============================================================================
# 1. Document Extractor Tests
# ============================================================================

class TestDocumentExtractor:
    """Test suite for DocumentExtractor."""

    def test_extract_txt_file(self, tmp_path: Path):
        file_path = tmp_path / "policy.txt"
        file_path.write_text("Equity exposure must not exceed 75% for balanced profiles.", encoding="utf-8")

        extractor = DocumentExtractor(allowed_root=tmp_path)
        doc = extractor.extract(file_path)

        assert isinstance(doc, ExtractedDocument)
        assert "Equity exposure must not exceed 75%" in doc.text
        assert doc.filename == "policy.txt"
        assert doc.file_type == "txt"
        assert len(doc.sha256_checksum) == 64

    def test_extract_markdown_file_preserves_structure(self, tmp_path: Path):
        content = (
            "# ESG Exclusion Policy\n\n"
            "## Tobacco and Weapons\n"
            "Portfolios flagged with ESG mandate must exclude tobacco manufacturing companies.\n\n"
            "## Thermal Coal\n"
            "Thermal coal mining revenue must be under 5%."
        )
        file_path = tmp_path / "esg_policy.md"
        file_path.write_text(content, encoding="utf-8")

        extractor = DocumentExtractor(allowed_root=tmp_path)
        doc = extractor.extract(file_path)

        assert doc.file_type == "md"
        assert "# ESG Exclusion Policy" in doc.text
        assert "## Tobacco and Weapons" in doc.text
        assert "Thermal coal mining" in doc.text

    def test_extract_pdf_file(self, tmp_path: Path):
        file_path = tmp_path / "sample.pdf"
        _create_sample_pdf(file_path, "Max position weight is 10 percent.")

        extractor = DocumentExtractor(allowed_root=tmp_path)
        doc = extractor.extract(file_path)

        assert doc.file_type == "pdf"
        assert "Max position weight is 10 percent" in doc.text

    def test_rejects_non_existent_file(self, tmp_path: Path):
        extractor = DocumentExtractor(allowed_root=tmp_path)
        with pytest.raises(DocumentNotFoundError):
            extractor.extract(tmp_path / "non_existent.txt")

    def test_defends_against_path_traversal(self, tmp_path: Path):
        safe_dir = tmp_path / "safe"
        safe_dir.mkdir()
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("confidential", encoding="utf-8")

        extractor = DocumentExtractor(allowed_root=safe_dir)
        traversal_path = safe_dir / "../secret.txt"

        with pytest.raises(PathTraversalError):
            extractor.extract(traversal_path)

    def test_rejects_unsupported_extension(self, tmp_path: Path):
        file_path = tmp_path / "script.py"
        file_path.write_text("print('hello')", encoding="utf-8")

        extractor = DocumentExtractor(allowed_root=tmp_path)
        with pytest.raises(UnsupportedFileTypeError):
            extractor.extract(file_path)

    def test_rejects_empty_file(self, tmp_path: Path):
        file_path = tmp_path / "empty.txt"
        file_path.write_text("   \n\n  ", encoding="utf-8")

        extractor = DocumentExtractor(allowed_root=tmp_path)
        with pytest.raises(EmptyDocumentError):
            extractor.extract(file_path)

    def test_rejects_oversized_file(self, tmp_path: Path):
        file_path = tmp_path / "large.txt"
        file_path.write_text("A" * 1024, encoding="utf-8")

        extractor = DocumentExtractor(allowed_root=tmp_path, max_bytes=512)
        with pytest.raises(DocumentSizeLimitExceededError):
            extractor.extract(file_path)

    def test_extract_uppercase_extension(self, tmp_path: Path):
        file_path = tmp_path / "POLICY.MD"
        file_path.write_text("# Uppercase Policy\nContent here.", encoding="utf-8")

        extractor = DocumentExtractor(allowed_root=tmp_path)
        doc = extractor.extract(file_path)
        assert doc.file_type == "md"
        assert "Uppercase Policy" in doc.text

    def test_rejects_corrupt_pdf(self, tmp_path: Path):
        file_path = tmp_path / "corrupt.pdf"
        file_path.write_bytes(b"%PDF-1.4 corrupt junk not valid pdf data")

        extractor = DocumentExtractor(allowed_root=tmp_path)
        with pytest.raises(CorruptDocumentError):
            extractor.extract(file_path)


# ============================================================================
# 2. Text Chunker Tests
# ============================================================================

class TestTextChunker:
    """Test suite for TextChunker."""

    def test_rejects_invalid_chunk_config(self):
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            TextChunker(chunk_size=0, chunk_overlap=0)

        with pytest.raises(ValueError, match="chunk_overlap must be less than chunk_size"):
            TextChunker(chunk_size=100, chunk_overlap=100)

        with pytest.raises(ValueError, match="chunk_overlap cannot be negative"):
            TextChunker(chunk_size=100, chunk_overlap=-10)

    def test_chunking_short_text(self):
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        chunks = chunker.chunk_text("Short policy text.", title="General Policy")

        assert len(chunks) == 1
        assert chunks[0].chunk_index == 0
        assert chunks[0].content == "Short policy text."
        assert chunks[0].section_title == "General Policy"
        assert chunks[0].token_count > 0

    def test_heading_aware_chunking_preserves_sections(self):
        markdown_text = (
            "# Section 1: Asset Allocation\n"
            "Equities must remain between 40% and 60% of total portfolio value.\n"
            "Fixed income must remain between 30% and 50%.\n\n"
            "# Section 2: Rebalancing Triggers\n"
            "Portfolios are reviewed monthly on the last business day.\n"
            "Absolute drift greater than 5% triggers immediate rebalance."
        )
        chunker = TextChunker(chunk_size=120, chunk_overlap=20)
        chunks = chunker.chunk_text(markdown_text)

        assert len(chunks) >= 2
        # Section titles should be inferred from markdown headings
        section_titles = [c.section_title for c in chunks]
        assert any("Section 1" in (t or "") for t in section_titles)
        assert any("Section 2" in (t or "") for t in section_titles)

    def test_zero_empty_chunks_produced(self):
        sparse_text = "   \n\n# Header\n\n\n\nParagraph 1.\n\n\n\n\n\nParagraph 2.   \n\n"
        chunker = TextChunker(chunk_size=100, chunk_overlap=10)
        chunks = chunker.chunk_text(sparse_text)

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.content.strip() != ""
            assert chunk.token_count > 0

    def test_chunk_ordering_is_monotonic(self):
        long_text = "\n\n".join([f"Paragraph {i}: Detailed policy rule number {i} covering portfolio drift." for i in range(15)])
        chunker = TextChunker(chunk_size=150, chunk_overlap=30)
        chunks = chunker.chunk_text(long_text)

        assert len(chunks) > 3
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))


# ============================================================================
# 3. Embedding Service Tests
# ============================================================================

class TestEmbeddingService:
    """Test suite for FakeEmbeddingService and real EmbeddingService."""

    def test_fake_embedding_deterministic_dimension_and_norm(self):
        service = FakeEmbeddingService(dimension=384)
        assert service.dimension == 384

        vec1 = service.generate_embedding("Maximum position weight is 10%.")
        vec2 = service.generate_embedding("Maximum position weight is 10%.")

        assert len(vec1) == 384
        assert vec1 == vec2  # 100% deterministic

        # Verify unit L2 norm
        norm = np.linalg.norm(vec1)
        assert np.isclose(norm, 1.0, atol=1e-5)

        # Verify no NaN or Inf
        arr = np.array(vec1)
        assert not np.isnan(arr).any()
        assert not np.isinf(arr).any()

    def test_fake_embedding_batch_generation(self):
        service = FakeEmbeddingService(dimension=384)
        texts = ["Text one", "Text two", "Text three"]
        batch = service.generate_embeddings(texts)

        assert len(batch) == 3
        for i, text in enumerate(texts):
            single = service.generate_embedding(text)
            assert np.allclose(batch[i], single)

    def test_fastembed_service_lazy_loading_and_norm(self):
        """Test real local EmbeddingService using fastembed."""
        service = EmbeddingService(model_name="BAAI/bge-small-en-v1.5")
        assert service._model is None  # Lazy loading check: not loaded at init!

        vec = service.generate_embedding("Portfolio rebalancing policy test.")
        assert len(vec) == 384
        assert service._model is not None

        # Verify L2 normalization
        norm = np.linalg.norm(vec)
        assert np.isclose(norm, 1.0, atol=1e-4)

    def test_embedding_service_invalid_input(self):
        service = FakeEmbeddingService()
        with pytest.raises(ValueError, match="Text cannot be empty"):
            service.generate_embedding("   ")


# ============================================================================
# 4. Database Models & Persistence Tests
# ============================================================================

class TestPolicyDatabaseModels:
    """Test suite for PolicyDocument and PolicyChunk SQLAlchemy models."""

    def test_create_policy_document_and_chunks(self):
        session = _create_sqlite_session()

        doc = PolicyDocument(
            id="DOC-POL-001",
            title="Global Equity Investment Policy",
            filename="global_equity.pdf",
            document_type=PolicyDocumentType.INVESTMENT_POLICY.value,
            version="1.0",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
            status=PolicyStatus.ACTIVE.value,
            file_path="policy_documents/global_equity.pdf",
            sha256_checksum="a" * 64,
        )
        session.add(doc)
        session.flush()

        chunk = PolicyChunk(
            id="CHK-001-000",
            document_id="DOC-POL-001",
            chunk_index=0,
            section_title="Max Exposure",
            content="Single stock max exposure is 10%.",
            token_count=7,
            embedding_json=json.dumps([0.1] * 384),
            embedding_model="BAAI/bge-small-en-v1.5",
        )
        session.add(chunk)
        session.commit()

        # Query and verify relationships
        saved_doc = session.query(PolicyDocument).filter_by(id="DOC-POL-001").one()
        assert len(saved_doc.chunks) == 1
        assert saved_doc.chunks[0].id == "CHK-001-000"
        assert saved_doc.chunks[0].document.title == "Global Equity Investment Policy"
        assert len(saved_doc.chunks[0].embedding) == 384
        # Verify fallback for unassigned family_id
        assert saved_doc.policy_family_id is None
        assert saved_doc.effective_policy_family_id == "LEGACY-DOC-DOC-POL-001"
        session.close()

    def test_policy_document_with_explicit_family_id(self):
        session = _create_sqlite_session()

        doc = PolicyDocument(
            id="DOC-POL-FAM-001",
            policy_family_id="FAM-GLOBAL-EQUITY",
            title="Global Equity Investment Policy",
            filename="global_equity.pdf",
            document_type=PolicyDocumentType.INVESTMENT_POLICY.value,
            version="1.0",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
            status=PolicyStatus.ACTIVE.value,
            file_path="policy_documents/global_equity.pdf",
            sha256_checksum="c" * 64,
        )
        session.add(doc)
        session.commit()

        saved_doc = session.query(PolicyDocument).filter_by(id="DOC-POL-FAM-001").one()
        assert saved_doc.policy_family_id == "FAM-GLOBAL-EQUITY"
        assert saved_doc.effective_policy_family_id == "FAM-GLOBAL-EQUITY"
        session.close()

    def test_cascade_deletion(self):
        session = _create_sqlite_session()

        doc = PolicyDocument(
            id="DOC-POL-CASCADE",
            title="Cascade Test Policy",
            filename="cascade.txt",
            document_type=PolicyDocumentType.MANDATE.value,
            version="1.0",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            status=PolicyStatus.ACTIVE.value,
            file_path="policy_documents/cascade.txt",
            sha256_checksum="b" * 64,
        )
        session.add(doc)
        session.flush()

        for i in range(3):
            chunk = PolicyChunk(
                id=f"CHK-CAS-{i}",
                document_id="DOC-POL-CASCADE",
                chunk_index=i,
                section_title=f"Section {i}",
                content=f"Content {i}",
                token_count=5,
                embedding_json=json.dumps([0.0] * 384),
                embedding_model="fake-model",
            )
            session.add(chunk)
        session.commit()

        assert session.query(PolicyChunk).filter_by(document_id="DOC-POL-CASCADE").count() == 3

        # Delete document -> chunks must be deleted via cascade
        session.delete(doc)
        session.commit()

        assert session.query(PolicyChunk).filter_by(document_id="DOC-POL-CASCADE").count() == 0
        session.close()


# ============================================================================
# 5. Vector Store & Similarity Search Tests
# ============================================================================

class TestVectorStore:
    """Test suite for VectorStore and Cosine Similarity Search."""

    def test_store_and_search_top_k(self):
        session = _create_sqlite_session()
        embedding_service = FakeEmbeddingService(dimension=384)
        store = VectorStore(session=session, embedding_service=embedding_service)

        doc = PolicyDocument(
            id="DOC-ESG-01",
            title="ESG Exclusion Rules",
            filename="esg.md",
            document_type=PolicyDocumentType.ESG_EXCLUSION.value,
            version="1.0",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            status=PolicyStatus.ACTIVE.value,
            file_path="policy_documents/esg.md",
            sha256_checksum="c" * 64,
        )
        session.add(doc)
        session.commit()

        chunks = [
            Chunk(chunk_index=0, section_title="Tobacco", content="Tobacco exclusion mandates zero exposure.", token_count=6),
            Chunk(chunk_index=1, section_title="Weapons", content="Controversial weapons are strictly barred.", token_count=6),
            Chunk(chunk_index=2, section_title="Fossil", content="Thermal coal mining revenue threshold is 5%.", token_count=7),
        ]

        stored_chunks = store.store_document_chunks(doc, chunks)
        assert len(stored_chunks) == 3

        # Search for exact match
        results = store.search(query="Tobacco exclusion mandates zero exposure.", top_k=2)
        assert len(results) == 2
        assert results[0].document_id == "DOC-ESG-01"
        assert results[0].section_title == "Tobacco"
        assert np.isclose(results[0].similarity_score, 1.0, atol=1e-4)

        session.close()

    def test_temporal_filtering_with_as_of_date(self):
        session = _create_sqlite_session()
        embedding_service = FakeEmbeddingService(dimension=384)
        store = VectorStore(session=session, embedding_service=embedding_service)

        # Policy 1: Expired (2025-01-01 to 2025-12-31)
        doc_past = PolicyDocument(
            id="DOC-PAST",
            title="Old Policy 2025",
            filename="past.txt",
            document_type=PolicyDocumentType.INVESTMENT_POLICY.value,
            version="1.0",
            effective_from=date(2025, 1, 1),
            effective_to=date(2025, 12, 31),
            status=PolicyStatus.ACTIVE.value,
            file_path="past.txt",
            sha256_checksum="1" * 64,
        )
        # Policy 2: Active currently (2026-01-01 to None)
        doc_curr = PolicyDocument(
            id="DOC-CURR",
            title="Current Policy 2026",
            filename="curr.txt",
            document_type=PolicyDocumentType.INVESTMENT_POLICY.value,
            version="2.0",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            status=PolicyStatus.ACTIVE.value,
            file_path="curr.txt",
            sha256_checksum="2" * 64,
        )
        # Policy 3: Future policy (2027-01-01 to None)
        doc_future = PolicyDocument(
            id="DOC-FUTURE",
            title="Future Policy 2027",
            filename="future.txt",
            document_type=PolicyDocumentType.INVESTMENT_POLICY.value,
            version="3.0",
            effective_from=date(2027, 1, 1),
            effective_to=None,
            status=PolicyStatus.ACTIVE.value,
            file_path="future.txt",
            sha256_checksum="3" * 64,
        )
        session.add_all([doc_past, doc_curr, doc_future])
        session.commit()

        store.store_document_chunks(doc_past, [Chunk(0, "Past Section", "Past rule content", 4)])
        store.store_document_chunks(doc_curr, [Chunk(0, "Current Section", "Current rule content", 4)])
        store.store_document_chunks(doc_future, [Chunk(0, "Future Section", "Future rule content", 4)])

        # Search as of 2026-06-15 -> MUST only return doc_curr!
        results = store.search(query="rule content", as_of_date=date(2026, 6, 15), top_k=5)
        doc_ids = [r.document_id for r in results]
        assert "DOC-CURR" in doc_ids
        assert "DOC-PAST" not in doc_ids
        assert "DOC-FUTURE" not in doc_ids

        session.close()

    def test_status_filtering(self):
        session = _create_sqlite_session()
        embedding_service = FakeEmbeddingService(dimension=384)
        store = VectorStore(session=session, embedding_service=embedding_service)

        doc_active = PolicyDocument(
            id="DOC-ACTIVE",
            title="Active Policy",
            filename="active.txt",
            document_type=PolicyDocumentType.MANDATE.value,
            version="1.0",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            status=PolicyStatus.ACTIVE.value,
            file_path="active.txt",
            sha256_checksum="4" * 64,
        )
        doc_superseded = PolicyDocument(
            id="DOC-SUPERSEDED",
            title="Superseded Policy",
            filename="superseded.txt",
            document_type=PolicyDocumentType.MANDATE.value,
            version="0.9",
            effective_from=date(2025, 1, 1),
            effective_to=None,
            status=PolicyStatus.SUPERSEDED.value,
            file_path="superseded.txt",
            sha256_checksum="5" * 64,
        )
        session.add_all([doc_active, doc_superseded])
        session.commit()

        store.store_document_chunks(doc_active, [Chunk(0, "Active", "Active guidance", 3)])
        store.store_document_chunks(doc_superseded, [Chunk(0, "Superseded", "Old guidance", 3)])

        # Default search searches ACTIVE only
        results = store.search(query="guidance")
        doc_ids = [r.document_id for r in results]
        assert "DOC-ACTIVE" in doc_ids
        assert "DOC-SUPERSEDED" not in doc_ids

        session.close()

    def test_similarity_threshold_filtering(self):
        session = _create_sqlite_session()
        embedding_service = FakeEmbeddingService(dimension=384)
        store = VectorStore(session=session, embedding_service=embedding_service)

        doc = PolicyDocument(
            id="DOC-THRESH",
            title="Threshold Policy",
            filename="thresh.txt",
            document_type=PolicyDocumentType.MANDATE.value,
            version="1.0",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            status=PolicyStatus.ACTIVE.value,
            file_path="thresh.txt",
            sha256_checksum="6" * 64,
        )
        session.add(doc)
        session.commit()

        store.store_document_chunks(doc, [
            Chunk(0, "A", "Specific text matching query query query", 6),
            Chunk(1, "B", "Completely unrelated text about trees and rivers", 7),
        ])

        # Require high similarity threshold
        results = store.search(query="Specific text matching query query query", similarity_threshold=0.95)
        assert len(results) == 1
        assert results[0].chunk_index == 0

        session.close()

    def test_empty_vector_store_returns_empty_list(self):
        session = _create_sqlite_session()
        embedding_service = FakeEmbeddingService(dimension=384)
        store = VectorStore(session=session, embedding_service=embedding_service)

        results = store.search(query="any search term")
        assert results == []
        session.close()

    def test_deterministic_tie_breaking(self):
        session = _create_sqlite_session()
        embedding_service = FakeEmbeddingService(dimension=384)
        store = VectorStore(session=session, embedding_service=embedding_service)

        doc = PolicyDocument(
            id="DOC-TIE",
            title="Tie Breaking Doc",
            filename="tie.txt",
            document_type=PolicyDocumentType.INVESTMENT_POLICY.value,
            version="1.0",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            status=PolicyStatus.ACTIVE.value,
            file_path="tie.txt",
            sha256_checksum="7" * 64,
        )
        session.add(doc)
        session.commit()

        # Two chunks with identical content -> identical similarity score
        chunks = [
            Chunk(chunk_index=1, section_title="Tie B", content="Identical content", token_count=2),
            Chunk(chunk_index=0, section_title="Tie A", content="Identical content", token_count=2),
        ]
        store.store_document_chunks(doc, chunks)

        results = store.search(query="Identical content", top_k=2)
        assert len(results) == 2
        # Deterministic tie-breaking by chunk ID ensures stable sort order
        assert results[0].chunk_id < results[1].chunk_id
        session.close()

    def test_document_type_and_id_filtering(self):
        session = _create_sqlite_session()
        embedding_service = FakeEmbeddingService(dimension=384)
        store = VectorStore(session=session, embedding_service=embedding_service)

        doc1 = PolicyDocument(
            id="DOC-TYPE-1",
            title="ESG Policy",
            filename="esg.txt",
            document_type=PolicyDocumentType.ESG_EXCLUSION.value,
            version="1.0",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            status=PolicyStatus.ACTIVE.value,
            file_path="esg.txt",
            sha256_checksum="8" * 64,
        )
        doc2 = PolicyDocument(
            id="DOC-TYPE-2",
            title="General Policy",
            filename="gen.txt",
            document_type=PolicyDocumentType.INVESTMENT_POLICY.value,
            version="1.0",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            status=PolicyStatus.ACTIVE.value,
            file_path="gen.txt",
            sha256_checksum="9" * 64,
        )
        session.add_all([doc1, doc2])
        session.commit()

        store.store_document_chunks(doc1, [Chunk(0, "ESG", "Coal exclusion rule", 3)])
        store.store_document_chunks(doc2, [Chunk(0, "General", "Coal exclusion rule", 3)])

        # Search filtered by document_type ESG_EXCLUSION
        res_type = store.search(query="Coal exclusion rule", document_type=PolicyDocumentType.ESG_EXCLUSION.value)
        assert len(res_type) == 1
        assert res_type[0].document_id == "DOC-TYPE-1"

        # Search filtered by document_id DOC-TYPE-2
        res_id = store.search(query="Coal exclusion rule", document_id="DOC-TYPE-2")
        assert len(res_id) == 1
        assert res_id[0].document_id == "DOC-TYPE-2"

        session.close()

    def test_search_all_statuses_when_status_is_none(self):
        session = _create_sqlite_session()
        embedding_service = FakeEmbeddingService(dimension=384)
        store = VectorStore(session=session, embedding_service=embedding_service)

        doc = PolicyDocument(
            id="DOC-DRAFT",
            title="Draft Policy",
            filename="draft.txt",
            document_type=PolicyDocumentType.MANDATE.value,
            version="0.1",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            status=PolicyStatus.DRAFT.value,
            file_path="draft.txt",
            sha256_checksum="d" * 64,
        )
        session.add(doc)
        session.commit()

        store.store_document_chunks(doc, [Chunk(0, "Draft", "Unapproved draft rule", 3)])

        # Default search (status=ACTIVE) -> 0 results
        assert len(store.search(query="Unapproved draft rule")) == 0

        # Searching with status=None or status=DRAFT returns it
        res_all = store.search(query="Unapproved draft rule", status=None)
        assert len(res_all) == 1
        assert res_all[0].document_id == "DOC-DRAFT"

        session.close()

    def test_reject_mixed_embedding_models_and_incompatible_dimensions(self):
        """Safety Test: VectorStore must ignore or reject chunks embedded with a different model or dimension."""
        session = _create_sqlite_session()
        embedding_service = FakeEmbeddingService(dimension=384, model_name="fake-embedding-model")
        store = VectorStore(session=session, embedding_service=embedding_service)

        doc = PolicyDocument(
            id="DOC-MIXED-MODELS",
            title="Mixed Models Doc",
            filename="mixed.txt",
            document_type=PolicyDocumentType.INVESTMENT_POLICY.value,
            version="1.0",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            status=PolicyStatus.ACTIVE.value,
            file_path="policy_documents/mixed.txt",
            sha256_checksum="e" * 64,
        )
        session.add(doc)
        session.flush()

        # Chunk 1: Embedded with incompatible 768-dim model "text-embedding-large"
        chunk_incompatible = PolicyChunk(
            id="CHK-INCOMPAT-768",
            document_id="DOC-MIXED-MODELS",
            chunk_index=0,
            section_title="Incompatible Section",
            content="768 dimensional chunk text",
            token_count=4,
            embedding_json=json.dumps([0.05] * 768),
            embedding_model="other-model-768",
        )
        # Chunk 2: Embedded with compatible 384-dim model "fake-embedding-model"
        chunk_compatible = PolicyChunk(
            id="CHK-COMPAT-384",
            document_id="DOC-MIXED-MODELS",
            chunk_index=1,
            section_title="Compatible Section",
            content="Target query text to match",
            token_count=5,
            embedding_json=json.dumps(embedding_service.generate_embedding("Target query text to match")),
            embedding_model="fake-embedding-model",
        )
        session.add_all([chunk_incompatible, chunk_compatible])
        session.commit()

        # Search must NOT crash on 768-dim vector; must only return chunk_compatible!
        results = store.search(query="Target query text to match", top_k=5)
        assert len(results) == 1
        assert results[0].chunk_id == "CHK-COMPAT-384"
        assert np.isclose(results[0].similarity_score, 1.0, atol=1e-4)

        session.close()

    def test_invalid_and_corrupt_persisted_vectors_handled_safely(self):
        """Safety Test: Corrupted JSON or invalid vector dimensions in DB must not crash search."""
        session = _create_sqlite_session()
        embedding_service = FakeEmbeddingService(dimension=384, model_name="fake-embedding-model")
        store = VectorStore(session=session, embedding_service=embedding_service)

        doc = PolicyDocument(
            id="DOC-CORRUPT",
            title="Corrupt Vector Doc",
            filename="corrupt.txt",
            document_type=PolicyDocumentType.INVESTMENT_POLICY.value,
            version="1.0",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            status=PolicyStatus.ACTIVE.value,
            file_path="policy_documents/corrupt.txt",
            sha256_checksum="f" * 64,
        )
        session.add(doc)
        session.flush()

        # Chunk with corrupt non-JSON embedding
        chunk_malformed_json = PolicyChunk(
            id="CHK-BAD-JSON",
            document_id="DOC-CORRUPT",
            chunk_index=0,
            section_title="Bad JSON",
            content="Malformed json vector",
            token_count=3,
            embedding_json="{corrupted: not a list}",
            embedding_model="fake-embedding-model",
        )
        # Chunk with invalid list containing strings
        chunk_non_floats = PolicyChunk(
            id="CHK-BAD-TYPES",
            document_id="DOC-CORRUPT",
            chunk_index=1,
            section_title="Bad Types",
            content="Non-float elements",
            token_count=2,
            embedding_json='["a", "b", "c"]',
            embedding_model="fake-embedding-model",
        )
        # Valid chunk
        valid_chunk = PolicyChunk(
            id="CHK-VALID",
            document_id="DOC-CORRUPT",
            chunk_index=2,
            section_title="Valid Chunk",
            content="Valid query target",
            token_count=3,
            embedding_json=json.dumps(embedding_service.generate_embedding("Valid query target")),
            embedding_model="fake-embedding-model",
        )
        session.add_all([chunk_malformed_json, chunk_non_floats, valid_chunk])
        session.commit()

        # Search must gracefully ignore corrupt chunks and return the valid chunk
        results = store.search(query="Valid query target", top_k=5)
        assert len(results) == 1
        assert results[0].chunk_id == "CHK-VALID"

        session.close()

    def test_known_cosine_similarity_geometric_vectors(self):
        """Safety Test: Validate exact mathematical cosine similarities for known vectors."""
        session = _create_sqlite_session()

        # We construct a mock embedding service with exact controlled vectors
        class ControlledEmbeddingService(BaseEmbeddingService):
            def __init__(self, current_vector: list[float]):
                self.current_vector = current_vector
            @property
            def dimension(self) -> int:
                return len(self.current_vector)
            @property
            def model_name(self) -> str:
                return "controlled-model"
            def generate_embeddings(self, texts):
                return [self.current_vector for _ in texts]

        # 3-dimensional unit vectors
        v_target = [1.0, 0.0, 0.0]      # Target query vector
        v_identical = [1.0, 0.0, 0.0]   # Cosine = 1.0
        v_orthogonal = [0.0, 1.0, 0.0]  # Cosine = 0.0
        v_opposite = [-1.0, 0.0, 0.0]   # Cosine = -1.0
        v_45deg = [1.0 / np.sqrt(2), 1.0 / np.sqrt(2), 0.0]  # Cosine = 0.7071

        ctrl_service = ControlledEmbeddingService(v_target)
        store = VectorStore(session=session, embedding_service=ctrl_service)

        doc = PolicyDocument(
            id="DOC-GEOM",
            title="Geometry Test",
            filename="geom.txt",
            document_type=PolicyDocumentType.INVESTMENT_POLICY.value,
            version="1.0",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            status=PolicyStatus.ACTIVE.value,
            file_path="policy_documents/geom.txt",
            sha256_checksum="0" * 64,
        )
        session.add(doc)
        session.flush()

        chunks_data = [
            ("CHK-IDENTICAL", v_identical),
            ("CHK-45DEG", v_45deg),
            ("CHK-ORTHOGONAL", v_orthogonal),
            ("CHK-OPPOSITE", v_opposite),
        ]
        for cid, vec in chunks_data:
            c = PolicyChunk(
                id=cid,
                document_id="DOC-GEOM",
                chunk_index=len(chunks_data),
                section_title="Geom",
                content=f"Content for {cid}",
                token_count=3,
                embedding_json=json.dumps(vec),
                embedding_model="controlled-model",
            )
            session.add(c)
        session.commit()

        results = store.search(query="target", top_k=10)
        assert len(results) == 4

        # Rank order must be: CHK-IDENTICAL (1.0), CHK-45DEG (~0.7071), CHK-ORTHOGONAL (0.0), CHK-OPPOSITE (-1.0)
        assert results[0].chunk_id == "CHK-IDENTICAL"
        assert np.isclose(results[0].similarity_score, 1.0, atol=1e-5)

        assert results[1].chunk_id == "CHK-45DEG"
        assert np.isclose(results[1].similarity_score, 1.0 / np.sqrt(2), atol=1e-5)

        assert results[2].chunk_id == "CHK-ORTHOGONAL"
        assert np.isclose(results[2].similarity_score, 0.0, atol=1e-5)

        assert results[3].chunk_id == "CHK-OPPOSITE"
        assert np.isclose(results[3].similarity_score, -1.0, atol=1e-5)

        session.close()

    def test_embeddings_retrievable_across_closed_sessions(self):
        """Safety Test: Embeddings stored in one session must remain fully retrievable across new sessions."""
        engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
        Base.metadata.create_all(engine)
        embedding_service = FakeEmbeddingService(dimension=384, model_name="fake-embedding-model")

        # Session 1: Store document and chunks
        with Session(engine) as session1:
            doc = PolicyDocument(
                id="DOC-SESS-01",
                title="Session Test Doc",
                filename="session.txt",
                document_type=PolicyDocumentType.INVESTMENT_POLICY.value,
                version="1.0",
                effective_from=date(2026, 1, 1),
                effective_to=None,
                status=PolicyStatus.ACTIVE.value,
                file_path="policy_documents/session.txt",
                sha256_checksum="1" * 64,
            )
            session1.add(doc)
            session1.commit()

            store1 = VectorStore(session=session1, embedding_service=embedding_service)
            store1.store_document_chunks(doc, [
                Chunk(0, "Sec 1", "Session persistence verification text", 4)
            ])
            session1.commit()

        # Session 2: Read back from fresh session
        with Session(engine) as session2:
            store2 = VectorStore(session=session2, embedding_service=embedding_service)
            chunk = session2.query(PolicyChunk).filter_by(id="CHK-DOC-SESS-01-000").one()
            assert len(chunk.embedding) == 384
            assert all(isinstance(x, float) for x in chunk.embedding)

            results = store2.search(query="Session persistence verification text", top_k=1)
            assert len(results) == 1
            assert results[0].chunk_id == "CHK-DOC-SESS-01-000"
            assert np.isclose(results[0].similarity_score, 1.0, atol=1e-4)

    def test_inclusive_effective_date_boundaries(self):
        """Safety Test: Verify exact inclusive boundaries for effective_from and effective_to."""
        session = _create_sqlite_session()
        embedding_service = FakeEmbeddingService(dimension=384)
        store = VectorStore(session=session, embedding_service=embedding_service)

        doc = PolicyDocument(
            id="DOC-BOUNDS",
            title="Boundaries Test Doc",
            filename="bounds.txt",
            document_type=PolicyDocumentType.INVESTMENT_POLICY.value,
            version="1.0",
            effective_from=date(2026, 3, 1),
            effective_to=date(2026, 3, 31),
            status=PolicyStatus.ACTIVE.value,
            file_path="policy_documents/bounds.txt",
            sha256_checksum="2" * 64,
        )
        session.add(doc)
        session.commit()
        store.store_document_chunks(doc, [Chunk(0, "Bounds", "Active in March 2026 only", 5)])

        # 1 day before effective_from -> NOT active
        assert len(store.search(query="Active in March 2026 only", as_of_date=date(2026, 2, 28))) == 0

        # Exact day of effective_from -> ACTIVE (inclusive)
        res_from = store.search(query="Active in March 2026 only", as_of_date=date(2026, 3, 1))
        assert len(res_from) == 1
        assert res_from[0].document_id == "DOC-BOUNDS"

        # Mid-month -> ACTIVE
        res_mid = store.search(query="Active in March 2026 only", as_of_date=date(2026, 3, 15))
        assert len(res_mid) == 1

        # Exact day of effective_to -> ACTIVE (inclusive)
        res_to = store.search(query="Active in March 2026 only", as_of_date=date(2026, 3, 31))
        assert len(res_to) == 1
        assert res_to[0].document_id == "DOC-BOUNDS"

        # 1 day after effective_to -> EXPIRED
        assert len(store.search(query="Active in March 2026 only", as_of_date=date(2026, 4, 1))) == 0

        session.close()

    def test_failed_ingestion_rolls_back_cleanly(self):
        """Safety Test: Ingestion failure in a transaction leaves zero orphaned chunks or documents."""
        session = _create_sqlite_session()

        class FailingEmbeddingService(BaseEmbeddingService):
            @property
            def dimension(self) -> int:
                return 384
            @property
            def model_name(self) -> str:
                return "failing-model"
            def generate_embeddings(self, texts):
                raise EmbeddingModelError("Simulated ONNX model failure during ingestion")

        failing_service = FailingEmbeddingService()
        store = VectorStore(session=session, embedding_service=failing_service)

        doc = PolicyDocument(
            id="DOC-FAIL",
            title="Failed Doc",
            filename="fail.txt",
            document_type=PolicyDocumentType.INVESTMENT_POLICY.value,
            version="1.0",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            status=PolicyStatus.ACTIVE.value,
            file_path="policy_documents/fail.txt",
            sha256_checksum="3" * 64,
        )

        try:
            with session.begin_nested():
                session.add(doc)
                chunks = [Chunk(0, "Sec", "Text to embed", 3)]
                store.store_document_chunks(doc, chunks)
        except EmbeddingModelError:
            session.rollback()

        # Verify nothing was persisted
        assert session.query(PolicyDocument).filter_by(id="DOC-FAIL").count() == 0
        assert session.query(PolicyChunk).filter_by(document_id="DOC-FAIL").count() == 0
        session.close()

    def test_policy_document_rejects_path_traversal_in_file_path(self):
        """Safety Test: PolicyDocument model rejects path traversal sequences in file_path."""
        with pytest.raises(ValueError, match="path traversal '..' is prohibited"):
            PolicyDocument(
                id="DOC-TRAVERSAL",
                title="Traversal Doc",
                filename="traversal.txt",
                document_type=PolicyDocumentType.INVESTMENT_POLICY.value,
                version="1.0",
                effective_from=date(2026, 1, 1),
                effective_to=None,
                status=PolicyStatus.ACTIVE.value,
                file_path="../../etc/passwd",
                sha256_checksum="4" * 64,
            )

    def test_multiple_policy_versions_coexist_with_identical_or_distinct_checksums(self):
        """Safety Test: Multiple versions of the same policy must coexist in the DB without overwriting."""
        session = _create_sqlite_session()

        v1 = PolicyDocument(
            id="DOC-ESG-v1.0",
            title="ESG Exclusion Policy",
            filename="esg_v1.md",
            document_type=PolicyDocumentType.ESG_EXCLUSION.value,
            version="1.0",
            effective_from=date(2025, 1, 1),
            effective_to=date(2025, 12, 31),
            status=PolicyStatus.SUPERSEDED.value,
            file_path="policy_documents/esg_v1.md",
            sha256_checksum="same_hash_checksum" + "0" * 46,
        )
        v2 = PolicyDocument(
            id="DOC-ESG-v2.0",
            title="ESG Exclusion Policy",
            filename="esg_v2.md",
            document_type=PolicyDocumentType.ESG_EXCLUSION.value,
            version="2.0",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            status=PolicyStatus.ACTIVE.value,
            file_path="policy_documents/esg_v2.md",
            sha256_checksum="same_hash_checksum" + "0" * 46,  # same checksum or new checksum
        )
        session.add_all([v1, v2])
        session.commit()

        # Both records must coexist without primary key or unique collision
        all_esg = session.query(PolicyDocument).filter_by(title="ESG Exclusion Policy").order_by(PolicyDocument.version).all()
        assert len(all_esg) == 2
        assert all_esg[0].version == "1.0"
        assert all_esg[0].status == PolicyStatus.SUPERSEDED.value
        assert all_esg[1].version == "2.0"
        assert all_esg[1].status == PolicyStatus.ACTIVE.value
        session.close()

    def test_document_extractor_symlink_defense(self, tmp_path: Path):
        """Safety Test: DocumentExtractor prevents reading targets outside allowed_root via symlinks."""
        safe_dir = tmp_path / "safe_dir"
        safe_dir.mkdir()
        outside_secret = tmp_path / "outside_secret.txt"
        outside_secret.write_text("classified data", encoding="utf-8")

        symlink_file = safe_dir / "symlink_to_outside.txt"
        try:
            symlink_file.symlink_to(outside_secret)
        except (OSError, NotImplementedError):
            # If OS does not permit symlinks without administrator privileges, skip symlink creation
            pytest.skip("Symlink creation not permitted by OS in current security context")

        extractor = DocumentExtractor(allowed_root=safe_dir)
        with pytest.raises(PathTraversalError):
            extractor.extract(symlink_file)



