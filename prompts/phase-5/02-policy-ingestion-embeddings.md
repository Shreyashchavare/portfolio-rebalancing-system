# Prompt P5-02 — Policy Ingestion, Chunking, Embeddings and Vector Storage

**AI Tool:** Antigravity  
**Phase:** 5 — Policy RAG  
**Task:** Phase 5.1 — Policy Ingestion, Chunking, Embeddings and Vector Storage  
**Execution Date:** 2026-11-11  

---

## 1. Prompt

```markdown
# Phase 5.1 — Policy Ingestion, Chunking, Embeddings and Vector Storage

Project: `E:\Yottaflex\portfolio-rebalancing-system`

Follow the approved Phase 5.1 audit report:
`prompts/phase-5/01-policy-rag-audit.md`

Target duration: 100 minutes. Hard limit: 120 minutes.

## 0. Repository safety

Before changes:
- Verify branch, working tree and latest commit.
- Confirm `main` is synchronized with `origin/main`.
- Stop if unrelated changes are present.
- Do not modify or regenerate synthetic datasets.

## 1. Implementation scope

Implement only the core Policy RAG ingestion and vector foundation:

1. Policy document metadata and persistence.
2. PDF, TXT and Markdown text extraction.
3. Deterministic text chunking.
4. Local embedding generation.
5. Embedding persistence and similarity search.
6. Unit tests and documentation.

Do not implement the RAG question-answering orchestrator or API in this batch. Those belong to the next batch.

## 2. Database models

Create `app/models/policy_document.py` containing:
- PolicyDocument
- PolicyChunk

## 3. Text extraction service

Create `app/services/policy_rag/document_extractor.py`

## 4. Deterministic text chunker

Create `app/services/policy_rag/text_chunker.py`

## 5. Embedding service

Create `app/services/policy_rag/embedding_service.py`

## 6. Vector storage and similarity search

Create `app/services/policy_rag/vector_store.py`

## 7. Configuration

Update `app/core/config.py` and `.env.example`

## 8. Unit tests

Create `tests/test_policy_ingestion_and_vectors.py` following strict TDD (RED -> GREEN).
```

---

## 2. Baseline & Repository Verification

- **Branch**: `main`
- **Initial Commit**: `99b668f test: add Phase 4.1 rebalancing trade generation unit tests`
- **Synchronization**: `origin/main` synchronized.
- **Working Tree**: Verified clean before edits.
- **Financial Boundary**: Synthetic datasets, existing models, portfolio analytics, and rebalancing engine (`RebalancingService`) remained 100% untouched.

---

## 3. TDD Progression

### A. RED Phase (Demonstrating Failure)
Implemented test suite in `tests/test_policy_ingestion_and_vectors.py` covering:
- Document extraction from PDF, TXT, and Markdown files.
- Security defenses: path traversal rejection, unsupported extensions, file size limits, corrupt PDF rejection, empty file rejection.
- Heading-aware text chunking with configurable size and overlap, heading inheritance, zero empty chunks, monotonic indexing.
- Fake and real local embedding services with 384-dimensional unit-$L_2$ norm and NaN/Inf validation.
- Database cascade deletion and relationship integrity.
- Vector store NumPy cosine similarity retrieval, temporal compliance pre-filtering (`effective_from <= as_of_date <= effective_to`), status filtering, document type/id filtering, threshold filtering, empty index handling, and deterministic tie-breaking.

**RED Test Output:**
```
collecting ... collected 0 items / 1 error
E   ModuleNotFoundError: No module named 'app.models.policy_document'
============================== 1 error in 0.68s ===============================
```

### B. GREEN Phase (Full Implementation Verification)
Implemented models, schemas, extraction, chunking, local ONNX embeddings (`fastembed`), and vectorized relational storage.

**GREEN Test Output:**
```
tests/test_policy_ingestion_and_vectors.py ............................. [100%]
============================= 29 passed in 1.86s ==============================
```

### C. Full Project Regression Suite
Executed complete pytest suite across Phase 1 to Phase 5:
```
======================= 349 passed, 3 warnings in 7.05s =======================
```
All 320 prior tests and 29 new tests passed without errors.

---

## 4. Architecture & Implementation Summary

### A. Database Models (`app/models/policy_document.py`)
- `PolicyDocument`: Ingested document registry (`id`, `title`, `filename`, `document_type`, `version`, `effective_from`, `effective_to`, `status`, `file_path`, `sha256_checksum`, `uploaded_at`).
- `PolicyChunk`: Child chunk entity with cascade deletion on document removal (`id`, `document_id`, `chunk_index`, `section_title`, `content`, `token_count`, `embedding_json`, `embedding_model`, `created_at`).

### B. Extraction Service (`app/services/policy_rag/document_extractor.py`)
- Supports `.pdf` via `pypdf`, `.md`, and `.txt`.
- Path traversal defense (`allowed_root` boundary checks).
- File size limit checks (default 20MB limit).
- Domain exceptions: `DocumentNotFoundError`, `PathTraversalError`, `UnsupportedFileTypeError`, `EmptyDocumentError`, `DocumentSizeLimitExceededError`, `CorruptDocumentError`.

### C. Chunking Service (`app/services/policy_rag/text_chunker.py`)
- Heading-aware parser tracking Markdown `#`, `##`, `###` headings to provide contextual `section_title` on all child chunks.
- Sentence and word boundary breaking when paragraphs exceed `chunk_size`.
- Word-bounded suffix overlap (`chunk_overlap`).
- Rejects invalid configurations and produces zero empty chunks.

### D. Local Embedding Service (`app/services/policy_rag/embedding_service.py`)
- `EmbeddingService`: Local ONNX inference via `fastembed` with `BAAI/bge-small-en-v1.5` producing 384-dimensional $L_2$-normalized vectors.
- Lazy model loading: Model weights are never loaded on application startup or module import.
- `FakeEmbeddingService`: Deterministic, offline hashing projection for fast unit test execution without network access.
- Error handling: Non-finite (NaN/Inf) guardrails and explicit `EmbeddingModelError` without silent fallback in production.

### E. Relational Vector Store (`app/services/policy_rag/vector_store.py`)
- Persists embeddings as JSON arrays in `PolicyChunk.embedding_json`.
- Query pre-filtering in SQL for status, document ID, document type, and temporal validity against `as_of_date`.
- Vectorized cosine similarity computed via NumPy dot product over normalized candidate embeddings.
- Deterministic sorting by `(-similarity_score, chunk.id)`.

---

## 5. Artifacts and Files Changed

1. `app/models/policy_document.py` (New model file)
2. `app/models/__init__.py` (Registered models & enums)
3. `app/schemas/policy_rag.py` (New Pydantic schemas)
4. `app/schemas/__init__.py` (Exported schemas)
5. `app/core/config.py` (Policy RAG configuration settings)
6. `.env.example` (Policy RAG environment variable defaults)
7. `requirements.txt` (Added `pypdf>=7.0.0`, `fastembed>=0.5.0`)
8. `app/services/policy_rag/document_extractor.py` (New extraction service)
9. `app/services/policy_rag/text_chunker.py` (New chunking service)
10. `app/services/policy_rag/embedding_service.py` (New embedding service)
11. `app/services/policy_rag/vector_store.py` (New vector store service)
12. `app/services/policy_rag/__init__.py` (Package exports)
13. `app/services/__init__.py` (Exported services)
14. `tests/test_policy_ingestion_and_vectors.py` (29 comprehensive unit tests)
15. `README.md` (Updated with Policy RAG details and offline pre-warming instructions)
16. `prompts/phase-5/02-policy-ingestion-embeddings.md` (This record)

---

## 6. Commitments & Next Steps

- **No commits or pushes made** (awaiting user review).
- **Ready for Batch 5.2**: Policy RAG Query Orchestrator, Citation Generator, Prompt Shielding, and FastAPI Endpoints.

