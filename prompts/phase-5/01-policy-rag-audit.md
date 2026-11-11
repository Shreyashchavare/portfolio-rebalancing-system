# Prompt P5-01 — Policy RAG Architecture and Implementation Audit

**AI Tool:** Antigravity  
**Phase:** 5 — Policy RAG  
**Task:** Phase 5.1 — Policy RAG Architecture and Implementation Audit

## Prompt

```markdown
# Phase 5.1 — Policy RAG Architecture and Implementation Audit

Project: `E:\Yottaflex\portfolio-rebalancing-system`

We are starting Phase 5: Policy RAG.

## Objective

Audit the existing repository and prepare a practical implementation plan for a reliable, locally runnable Policy RAG system that supports the portfolio rebalancing workflow.

This is a **READ-ONLY AUDIT**. Do not implement features or modify production code.

## 1. Verify repository state first

- Check the current branch, `git status --short`, and recent commits.
- Confirm whether Phase 4 changes are committed and whether the local branch is synchronized with `origin/main`.
- If Phase 4 changes are still uncommitted or the working tree contains unrelated changes, stop and report them. Do not mix Phase 4 and Phase 5 work.

## 2. Inspect the existing architecture

Inspect relevant files in:

- `app/models/`
- `app/schemas/`
- `app/services/`
- `app/api/`
- `app/core/`
- `app/database/`
- `tests/`
- `policy_documents/`
- `requirements.txt`
- `.env.example`
- `README.md`

Identify existing document, policy, embedding, vector-search, and RAG capabilities. Reuse existing infrastructure where appropriate.

## 3. Define the Policy RAG requirements

Evaluate the implementation needed for:

1. Policy document ingestion (PDF, TXT, Markdown).
2. Document metadata and policy identification.
3. Text extraction and normalization.
4. Chunking with configurable chunk size and overlap.
5. Embedding generation using a locally runnable embedding model.
6. Vector storage and retrieval using the existing project architecture.
7. Metadata filtering by policy, effective date, version, and status.
8. Hybrid retrieval if justified by the existing stack.
9. Source-grounded answers with citations to document, version, and chunk.
10. Handling missing, expired, conflicting, and superseded policies.
11. Retrieval failure and unavailable local model handling.

Do not assume that ChromaDB, FAISS, LangChain, or another dependency is already installed. Verify first.

## 4. Enforce financial and security boundaries

The design must guarantee:

- Policy documents are untrusted input.
- Retrieved text cannot override system instructions or application rules.
- The LLM cannot execute SQL or modify database records.
- The LLM cannot approve, reject, or execute trades.
- Financial calculations and constraint enforcement remain deterministic in Python.
- Answers must distinguish retrieved policy facts from missing information.
- Every material policy claim must be traceable to a source.
- Effective-date and version filtering must prevent retrieval of invalid policy versions.
- If retrieval or the local LLM is unavailable, the financial rebalancing engine must continue working independently.

## 5. Recommend a minimal implementation design

Provide:

- Required services and their responsibilities.
- Required schemas/models and whether migrations are necessary.
- API endpoints.
- Document ingestion and retrieval flow.
- Embedding and vector-storage strategy.
- Configuration and environment variables.
- Test strategy, including security and temporal/version-filtering tests.
- Dependencies that are genuinely necessary.
- A two-batch implementation plan, each batch within 120 minutes.

Avoid unnecessary microservices, message brokers, infrastructure, and architectural rewrites.

## 6. Deliverable

Save the audit report and proposed implementation plan in:

`prompts/phase-5/01-policy-rag-audit.md`

Include:
- Existing capabilities found.
- Missing capabilities.
- Recommended architecture.
- Security and financial risks.
- Implementation batches and acceptance criteria.
- Estimated time for each batch.

Do not modify application code, models, dependencies, migrations, datasets, or existing tests.

Do not commit or push.

At the end, report the audit findings and confirm the exact files inspected.
```

---

## 1. Repository State Verification

- **Branch**: `main`
- **Working Tree**: Completely clean (`git status --short` returned 0 modified or untracked files).
- **Remote Synchronization**: `main` is up to date with `origin/main`.
- **Recent Commits**:
  - `99b668f` `test: add Phase 4.1 rebalancing trade generation unit tests`
  - `6960069` `feat: complete portfolio rebalancing engine`
  - `7eb31f4` `feat: implement portfolio analytics and API`
- **Phase 4 Status**: Phase 4 trade generation, post-trade simulation, constraint gatekeeper, proposal persistence, and FastAPI endpoints are committed and tested (all 320 tests passing). No Phase 4 changes remain uncommitted.

---

## 2. Existing Architecture & Capability Analysis

### A. Inspected Files and Existing Capabilities

| Area / Component | Files Inspected | Findings & Existing Capabilities |
| :--- | :--- | :--- |
| **Data Models** | `app/models/base.py`<br>`app/models/constraint.py`<br>`app/models/constraint_instrument.py`<br>`app/models/fee_schedule.py`<br>`app/models/holding.py`<br>`app/models/instrument.py`<br>`app/models/investor_profile.py`<br>`app/models/market_price.py`<br>`app/models/portfolio.py`<br>`app/models/rebalance_proposal.py`<br>`app/models/target_allocation.py`<br>`app/models/trade.py` | - Declarative SQLAlchemy 2.x `Base` model.<br>- Structured relational policy constraints (`Constraint` model with 8 types, `severity`, `threshold_value`, `effective_from`, `effective_to`, `is_active`).<br>- **Gap**: Zero document, text chunk, or vector embedding models exist. |
| **Schemas** | `app/schemas/portfolio_analytics.py`<br>`app/schemas/rebalancing.py`<br>`app/schemas/__init__.py` | - Pydantic v2 schemas for valuations, drift analysis, proposed trades, simulations, and constraint findings.<br>- **Gap**: Zero schemas for policy document ingestion, chunking, citations, or RAG querying. |
| **Services** | `app/services/portfolio_analytics_service.py`<br>`app/services/rebalancing_service.py`<br>`app/services/__init__.py` | - High-precision (`Decimal('0.0001')`) analytics and rebalancing services.<br>- Policy constraint evaluation in `evaluate_constraints`.<br>- **Gap**: No document ingestion, text parsing, chunking, embedding generation, or vector retrieval services. |
| **API Endpoints** | `app/api/v1/analytics.py`<br>`app/api/v1/rebalancing.py`<br>`app/api/v1/__init__.py`<br>`app/main.py` | - FastAPI endpoints under `/api/v1/portfolios`.<br>- Standard dependency injection with `get_db`.<br>- **Gap**: No `/api/v1/policies` router. |
| **Configuration** | `app/core/config.py`<br>`.env.example` | - Pydantic `BaseSettings` reading `.env`.<br>- Configures DB URL, port, host.<br>- **Gap**: No configuration settings for policy storage paths, embedding model names, chunk size/overlap, or local LLM inference endpoints. |
| **Database** | `app/database/session.py`<br>`alembic/` | - SQLAlchemy engine and `SessionLocal` factory with lazy binding.<br>- Supports both SQLite (used in tests) and PostgreSQL (production).<br>- **Gap**: No vector database or `pgvector` extension configured. |
| **Documents** | `policy_documents/` | - Directory exists with `.gitkeep` only. No actual policy documents or ingestion pipelines present. |
| **Dependencies** | `requirements.txt`<br>`pip list` | - Standard stack: `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `psycopg2-binary`, `pydantic`, `pandas`, `numpy`, `pytest`, `httpx`.<br>- **Gap**: No PDF reader (`pypdf`), embedding library (`sentence-transformers` / `fastembed`), or vector DB (`faiss` / `chromadb`). |

---

## 3. Policy RAG Requirements Analysis

1. **Document Ingestion (PDF, TXT, Markdown)**:
   - Must support unstructured text formats (`.txt`, `.md`) using native Python I/O.
   - Must support `.pdf` files using a pure-Python, cross-platform PDF library (`pypdf>=4.0.0`) that requires zero C++ compilers or OS binaries.
2. **Metadata & Policy Identification**:
   - Every policy document requires identification attributes: `document_id`, `policy_name`, `version` (e.g., `1.0`, `2.1`), `effective_from`, `effective_to`, `status` (`DRAFT`, `ACTIVE`, `SUPERSEDED`, `ARCHIVED`), and applicable `asset_classes` / `jurisdictions`.
3. **Text Extraction & Normalization**:
   - Clean whitespace, strip non-printable characters, preserve structural Markdown headings (`#`, `##`, `###`), and normalize tabular text.
4. **Chunking with Configurable Size & Overlap**:
   - Header-aware recursive character chunking (e.g., target 500 characters, 50 characters overlap) that maintains section title context in each chunk.
5. **Embedding Generation**:
   - Must run locally without external cloud API dependencies.
   - Target model: lightweight local sentence embedding model (e.g., `sentence-transformers/all-MiniLM-L6-v2` or `fastembed` with 384 dimensions).
   - Must feature a deterministic mock embedding fallback when weights are offline or during unit testing.
6. **Vector Storage & Retrieval**:
   - To maintain 100% compatibility across both PostgreSQL and SQLite (in-memory unit test harness), vectors can be stored in the relational schema as serialized `JSON` or `BLOB`/`ARRAY`, paired with vectorized NumPy cosine similarity search (`np.dot` / cosine metric).
   - This eliminates the need for external vector database servers or specialized C extensions (`pgvector`), matching the existing lightweight architecture.
7. **Metadata Filtering (Temporal & Versioning)**:
   - Critical for financial compliance: Given an `as_of_date`, retrieval queries MUST filter:
     `effective_from <= as_of_date AND (effective_to IS NULL OR effective_to >= as_of_date) AND status == 'ACTIVE'`.
   - Prevents retrieval of expired, superseded, or draft policies during rebalance justification.
8. **Hybrid Retrieval**:
   - Dense semantic vector similarity combined with lexical keyword filtering (e.g. matching specific instrument symbols like `AAPL`, asset classes like `EQUITY`, or constraint names).
9. **Source-Grounded Answers & Citations**:
   - Every answer generated must cite: `[Doc: {policy_name}, Version: {version}, Section: {section_title}, Chunk: {chunk_id}]`.
   - If similarity score falls below threshold, output must state: *"No active policy found covering this topic as of the requested date."*
10. **Policy Lifecycle & Supercession Handling**:
    - When a new version of an existing policy is ingested (e.g. version 2.0 with `effective_from = 2026-06-01`), version 1.0 is marked `SUPERSEDED` with `effective_to = 2026-05-31`.
11. **Graceful Degradation**:
    - If the local embedding model or local LLM is unreachable, the system returns raw retrieved citations or an explicit diagnostic without failing the application or blocking the rebalancing engine.

---

## 4. Financial & Security Boundaries

| Boundary | Enforcement Mechanism |
| :--- | :--- |
| **Untrusted Input Protection** | Policy document content is sanitized and wrapped within explicit XML blocks (e.g. `<policy_citation document="...">...</policy_citation>`) in LLM context windows to prevent prompt injection and instruction overrides. |
| **Read-Only LLM Role** | The LLM operates purely as a read-only document summarizer. It has **no database write credentials**, **no SQL execution capability**, and **no tool-calling access** to the trading system. |
| **Strict Separation of Concerns** | Rebalancing calculations, constraint evaluations, and trade persistence remain 100% deterministic in Python. The LLM cannot approve, reject, or alter trade proposals. |
| **Independent Rebalancing Engine** | If the Policy RAG service is disabled, offline, or errors out, `PortfolioAnalyticsService` and `RebalancingService` continue executing without interruption. |
| **Temporal Integrity** | SQL-level date filtering guarantees that future or expired policy language cannot be returned for historical or current rebalance runs. |
| **Hallucination Prevention** | The LLM is explicitly barred from generating answers outside the provided `<policy_citation>` chunks. |

---

## 5. Recommended Architecture & Implementation Design

### A. Data Models (`app/models/policy_document.py`)

```python
class PolicyDocument(Base):
    __tablename__ = "policy_document"
    document_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # PDF, MD, TXT
    version: Mapped[str] = mapped_column(String(20), nullable=False)     # e.g. "1.0"
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)      # ACTIVE, SUPERSEDED, DRAFT
    asset_classes: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    chunks: Mapped[list["PolicyChunk"]] = relationship("PolicyChunk", back_populates="document", cascade="all, delete-orphan")


class PolicyChunk(Base):
    __tablename__ = "policy_chunk"
    chunk_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(40), ForeignKey("policy_document.document_id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_json: Mapped[str] = mapped_column(Text, nullable=False)  # Serialized 384-dim float list

    document: Mapped["PolicyDocument"] = relationship("PolicyDocument", back_populates="chunks")
```

*Note on Migrations*: Models inherit from `Base`. In SQLite test environments, `Base.metadata.create_all()` provisions them automatically. In PostgreSQL production, Alembic migration or SQL seed scripts can be emitted cleanly.

### B. Schemas (`app/schemas/policy_rag.py`)

- `PolicyDocumentIngestRequest`: Metadata fields (`title`, `version`, `effective_from`, `effective_to`, `asset_classes`).
- `PolicyDocumentResponse`: Complete document details and chunk counts.
- `PolicyChunkResponse`: Content, section title, and chunk identifier.
- `PolicyQueryRequest`: Search query string, `as_of_date`, optional `asset_class`, `top_k`, `similarity_threshold`.
- `PolicyCitation`: Document ID, title, version, section, chunk ID, text excerpt, similarity score.
- `PolicyQueryResponse`: Query, as-of date, answer summary, list of grounded `PolicyCitation`s, and execution diagnostics.

### C. Service Architecture (`app/services/policy_rag/`)

```
app/services/policy_rag/
├── __init__.py
├── document_extractor.py     # PDF (pypdf), Markdown, and TXT parsing & normalization
├── text_chunker.py           # Header-aware chunking with configurable size and overlap
├── embedding_service.py      # Local embedding generator (sentence-transformers / mock fallback)
├── vector_store.py           # In-database vector storage & vectorized NumPy cosine search
└── policy_rag_service.py     # Ingestion coordination, temporal filtering, prompt shielding, and Q&A
```

### D. API Endpoints (`app/api/v1/policies.py`)

- `POST /api/v1/policies/ingest`: Upload/ingest a policy document file (`.pdf`, `.md`, `.txt`) with metadata.
- `GET /api/v1/policies`: List all registered policies with version and date filters.
- `GET /api/v1/policies/{document_id}`: Retrieve policy document details and chunk listing.
- `POST /api/v1/policies/search`: Semantic similarity search returning ranked policy chunks filtered by `as_of_date`.
- `POST /api/v1/policies/ask`: Natural language Q&A returning grounded answers with citations.

### E. Configuration (`app/core/config.py`)

Add to `Settings`:
- `POLICY_DOCUMENTS_DIR: str = "policy_documents"`
- `EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"`
- `RAG_CHUNK_SIZE: int = 500`
- `RAG_CHUNK_OVERLAP: int = 50`
- `RAG_TOP_K: int = 4`
- `RAG_SIMILARITY_THRESHOLD: float = 0.50`
- `LOCAL_LLM_URL: Optional[str] = "http://localhost:11434"` (optional Ollama/local endpoint)

### F. Minimal Dependencies to Add

Only two lightweight dependencies are genuinely necessary:
1. `pypdf>=4.0.0` (pure Python PDF text extraction).
2. `sentence-transformers>=2.5.0` (or `fastembed>=0.2.0`) for local, offline embeddings.

*(NumPy is already installed and handles cosine vector similarity search efficiently in memory/database without requiring ChromaDB, FAISS, or pgvector).*

---

## 6. Two-Batch Implementation Plan

```
Phase 5 — Policy RAG
├── Batch 5.1: Ingestion, Chunking, Local Embeddings & Vector Storage (100 mins)
└── Batch 5.2: Retrieval, Prompt Shielding, Grounded Citations & API (90 mins)
```

### Batch 5.1 — Core Ingestion, Chunking, Local Embeddings, and Vector Store
- **Duration**: ~100 minutes.
- **Tasks**:
  1. Add `pypdf` and `sentence-transformers` (or `fastembed`) to `requirements.txt`.
  2. Implement `PolicyDocument` and `PolicyChunk` models in `app/models/policy_document.py`.
  3. Implement Pydantic schemas in `app/schemas/policy_rag.py`.
  4. Implement `DocumentExtractor` supporting PDF, Markdown, and TXT with text normalization.
  5. Implement `TextChunker` with header-aware boundary preservation and overlap.
  6. Implement `EmbeddingService` with local model loading and deterministic mock fallback.
  7. Implement `VectorStore` utilizing SQLite/PostgreSQL relational storage + NumPy cosine similarity.
  8. Write comprehensive unit tests in `tests/test_policy_ingestion_and_vectors.py`.
- **Acceptance Criteria**:
  - Ingestion of PDF, MD, and TXT documents produces verified chunks and embeddings.
  - NumPy cosine search returns top-$k$ nearest chunks.
  - SQL temporal filtering accurately enforces `effective_from` and `effective_to` against `as_of_date`.
  - All tests pass on in-memory SQLite and PostgreSQL without external services.

### Batch 5.2 — Policy RAG Query Orchestrator, Citation Generator, and FastAPI Endpoints
- **Duration**: ~90 minutes.
- **Tasks**:
  1. Implement `PolicyRAGService` orchestrating temporal query filtering, semantic vector retrieval, and prompt construction.
  2. Implement prompt-injection shielding (XML tags, strict instruction encapsulation, untrusted text demarcation).
  3. Implement grounded answer generator with chunk citations (`[Doc, Version, Section, Chunk]`).
  4. Implement graceful fallback for missing policies or unavailable local LLM inference.
  5. Create FastAPI router `app/api/v1/policies.py` and register in `app/main.py`.
  6. Add seed policy documents in `policy_documents/` covering standard investment policy guidelines.
  7. Write integration and API tests in `tests/test_policy_rag_api.py`.
  8. Run full test suite to guarantee zero regression across Phase 1–5.
- **Acceptance Criteria**:
  - `POST /api/v1/policies/ingest` successfully ingests documents and stores chunks.
  - `POST /api/v1/policies/search` and `POST /api/v1/policies/ask` return grounded answers with accurate citations.
  - Expired, future, or superseded policies are excluded when queried with an active `as_of_date`.
  - Adversarial prompt injection payloads in policy text fail to breach application boundaries.
  - Full test suite passes cleanly.

---

## 7. Confirmation of Exact Files Inspected

- `app/models/base.py`
- `app/models/constraint.py`
- `app/models/constraint_instrument.py`
- `app/models/fee_schedule.py`
- `app/models/holding.py`
- `app/models/instrument.py`
- `app/models/investor_profile.py`
- `app/models/market_price.py`
- `app/models/portfolio.py`
- `app/models/rebalance_proposal.py`
- `app/models/target_allocation.py`
- `app/models/trade.py`
- `app/models/__init__.py`
- `app/schemas/portfolio_analytics.py`
- `app/schemas/rebalancing.py`
- `app/schemas/__init__.py`
- `app/services/portfolio_analytics_service.py`
- `app/services/rebalancing_service.py`
- `app/services/__init__.py`
- `app/api/v1/analytics.py`
- `app/api/v1/rebalancing.py`
- `app/api/v1/__init__.py`
- `app/core/config.py`
- `app/database/session.py`
- `policy_documents/.gitkeep`
- `docs/data-dictionary.md`
- `requirements.txt`
- `.env.example`
- `README.md`
- All 35 test files in `tests/` (320 tests verified).

*No application code, models, dependencies, migrations, datasets, or tests were modified during this read-only audit.*

