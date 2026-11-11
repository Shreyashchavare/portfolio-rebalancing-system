# Prompt P5-03 — Final Policy Ingestion and Vector Storage Safety Review

**AI Tool:** Antigravity  
**Phase:** 5 — Policy RAG  
**Task:** Phase 5.1 — Final Policy Ingestion and Vector Storage Safety Review  
**Execution Date:** 2026-11-11  

---

## 1. Prompt

```markdown
# Phase 5.1 — Final Policy Ingestion and Vector Storage Safety Review

Project: `E:\Yottaflex\portfolio-rebalancing-system`

Review the completed Phase 5.1 implementation before Batch 5.2.

Reference:
- `prompts/phase-5/01-policy-rag-audit.md`
- `prompts/phase-5/02-policy-ingestion-embeddings.md`

## 1. Review repository state
Check branch, working tree, latest commit and current test results. Do not commit or push.

## 2. Inspect implementation
Review:
- `app/models/policy_document.py`
- `app/schemas/policy_rag.py`
- `app/services/policy_rag/document_extractor.py`
- `app/services/policy_rag/text_chunker.py`
- `app/services/policy_rag/embedding_service.py`
- `app/services/policy_rag/vector_store.py`
- `app/core/config.py`
- `app/models/__init__.py`
- `app/services/__init__.py`
- `requirements.txt`
- `.env.example`
- `tests/test_policy_ingestion_and_vectors.py`

## 3. Verify these critical properties
A. Database and migrations
B. Embedding integrity
C. Document versioning and temporal filtering
D. File and ingestion safety
E. Offline model behavior
F. Vector search

## 4. Test-first corrections
If a defect exists:
- Add a regression test first.
- Demonstrate RED with a behavioral failure.
- Apply the smallest safe correction.
- Demonstrate GREEN.
- Run the full project test suite.

## 5. Final deliverable
Save findings and any corrections in:
`prompts/phase-5/03-ingestion-vector-safety-review.md`
```

---

## 2. Repository State Verification

- **Branch**: `main`
- **Latest Commit**: `99b668f test: add Phase 4.1 rebalancing trade generation unit tests`
- **Working Tree**: Only Phase 5.1 files modified/added; no unrelated modifications; no git commits or pushes made.
- **Financial Boundary**: Synthetic datasets, existing models, portfolio analytics, and rebalancing engine (`RebalancingService`) remained 100% untouched.

---

## 3. Inspected Files & Core Architectural Checks

| Component | File Inspected | Verification Result |
| :--- | :--- | :--- |
| **Models** | `app/models/policy_document.py` | `PolicyDocument` and `PolicyChunk` with cascade delete, validated `file_path`, and validated `embedding` getter. |
| **Schemas** | `app/schemas/policy_rag.py` | Pydantic v2 schemas: metadata, chunks, responses, search results, query filters. |
| **Extraction** | `app/services/policy_rag/document_extractor.py` | `DocumentExtractor` for PDF/MD/TXT with `allowed_root` boundary checks, 20MB limit, and domain exceptions. |
| **Chunking** | `app/services/policy_rag/text_chunker.py` | `TextChunker` with Markdown heading preservation, paragraph/sentence splitting, and overlap. |
| **Embeddings** | `app/services/policy_rag/embedding_service.py` | `EmbeddingService` with lazy ONNX model loading (`BAAI/bge-small-en-v1.5`), unit-$L_2$ normalization, and `FakeEmbeddingService` for offline tests. |
| **Vector Store** | `app/services/policy_rag/vector_store.py` | `VectorStore` with SQL pre-filtering by model, status, document type/id, temporal validity, and NumPy cosine similarity ranking. |
| **Config** | `app/core/config.py`, `.env.example` | Added RAG configuration settings (`EMBEDDING_MODEL_NAME`, `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`, `RAG_TOP_K`, `RAG_SIMILARITY_THRESHOLD`, `LOCAL_LLM_URL`). |
| **Dependencies** | `requirements.txt` | Added `pypdf>=7.0.0` and `fastembed>=0.5.0`. |
| **Test Suite** | `tests/test_policy_ingestion_and_vectors.py` | 38 comprehensive safety and behavioral unit tests. |

---

## 4. Verification of Critical Properties

### A. Database and Migrations
1. **Alembic Status**: The repository has an empty `alembic/` directory containing only `.gitkeep`, with no `alembic.ini`. As in Phases 1–4, unit tests utilize `Base.metadata.create_all()` against SQLite in-memory databases.
2. **PostgreSQL & SQLite Table Compilation**: Verified DDL compilation via `CreateTable` against both `postgresql.dialect()` and `sqlite.dialect()`. All column types (`VARCHAR`, `DATE`, `TIMESTAMP WITH TIME ZONE`, `TEXT`, `INTEGER`) compile without errors.
3. **Foreign Keys & Cascade**: Verified that `PolicyChunk.document_id` enforces `FOREIGN KEY ... ON DELETE CASCADE` in SQL and `cascade="all, delete-orphan"` in the ORM. Deleting a `PolicyDocument` completely removes all associated chunks.
4. **Documented Migration Path**: Created production-grade, idempotent PostgreSQL migration script at `docs/migrations/001_create_policy_rag_tables.sql` with indices on `status`, `document_type`, `(effective_from, effective_to)`, `sha256_checksum`, `document_id`, and `embedding_model`.

### B. Embedding Integrity
1. **Model Isolation**: Verified that `VectorStore.search` pre-filters `PolicyChunk.embedding_model == self.embedding_service.model_name` at the SQL level. Chunks embedded with a different model space (e.g. 768-dim models) are excluded and cannot contaminate similarity ranking.
2. **Dimension & Finite Checks**: Vectors are verified to match query dimensions; non-finite values (NaN / Inf) are rejected.
3. **Session Re-Opening**: Verified via `test_embeddings_retrievable_across_closed_sessions` that committing, closing the database session, and opening a new session preserves exact 384-dimensional float embeddings and retrieval scores.
4. **No Silent Fake Fallback**: Verified that `EmbeddingService` raises `EmbeddingModelError` upon ONNX initialization failure. `FakeEmbeddingService` is never called implicitly or selected as a silent fallback.

### C. Document Versioning & Temporal Filtering
1. **Multiple Versions Coexistence**: Verified via `test_multiple_policy_versions_coexist_with_identical_or_distinct_checksums` that version 1.0 (superseded) and version 2.0 (active) can be stored concurrently without primary key or checksum collisions.
2. **Inclusive Boundary Semantics**: Verified via `test_inclusive_effective_date_boundaries` that:
   - Evaluation on `effective_from` $\implies$ Active.
   - Evaluation before `effective_from` $\implies$ Excluded (future).
   - Evaluation on `effective_to` $\implies$ Active.
   - Evaluation after `effective_to` $\implies$ Excluded (expired).
   - `effective_to = None` $\implies$ Active indefinitely.
3. **Status Filtering**: `status = 'ACTIVE'` is applied by default; draft and superseded policies are excluded from active retrieval.

### D. File and Ingestion Safety
1. **Path Traversal & Symlinks**: `DocumentExtractor` resolves canonical paths against `allowed_root`, rejecting traversal attempts (`..`) and symlinks escaping the allowed directory.
2. **Database Record Protection**: Added `@validates("file_path")` to `PolicyDocument` to reject path traversal sequences (`..`) from ever being persisted into the database.
3. **Transaction Rollback**: Verified via `test_failed_ingestion_rolls_back_cleanly` that embedding or persistence failure in a transaction cleanly rolls back and leaves zero orphaned document or chunk records.

### E. Offline Model Behavior
1. **Configuration**: Configured model is `BAAI/bge-small-en-v1.5` generating 384-dimensional unit-$L_2$-normalized vectors.
2. **Lazy Initialization**: Neither `fastembed` nor the model weights are loaded during module import or FastAPI startup. Model instantiation only occurs upon the first explicit embedding call.
3. **Pre-Warming**: Documented the offline caching command in `README.md` (`python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5')"`).

### F. Vector Search
1. **Mathematical Accuracy**: Verified cosine similarity against known geometric vectors (`test_known_cosine_similarity_geometric_vectors`):
   - Identical ($1.0$)
   - 45-degree angle ($\sqrt{2}/2 \approx 0.7071$)
   - Orthogonal ($0.0$)
   - Opposite ($-1.0$)
2. **Deterministic Tie-Breaking**: Verified that identical similarity scores are sorted stably using `chunk.id` ascending as tie-breaker.
3. **Resilience to Corrupt Chunks**: Persisted malformed vectors (invalid JSON, non-numeric elements, dimension mismatch) are skipped safely without crashing search execution.

---

## 5. Test-First Corrections (RED -> GREEN)

### Defect 1: Mixed Embedding Models and Incompatible Dimensions
- **Vulnerability**: If the database contained chunks embedded with an incompatible model (e.g. 768 dimensions), `VectorStore.search` attempted dot-product computation against the 384-dimensional query vector, throwing an unhandled exception.
- **RED Evidence**:
  ```
  FAILED tests/test_policy_ingestion_and_vectors.py::TestVectorStore::test_reject_mixed_embedding_models_and_incompatible_dimensions
  ValueError: shapes (768,) and (384,) not aligned: 768 (dim 0) != 384 (dim 0)
  ```
- **Correction**: Added SQL pre-filter `.filter(PolicyChunk.embedding_model == self.embedding_service.model_name)` and dimension compatibility check `if emb.shape != query_vec.shape: continue`.
- **GREEN Evidence**: Test passed cleanly.

### Defect 2: Malformed Persisted Embedding JSON
- **Vulnerability**: If a chunk had corrupted JSON or non-float types in `embedding_json`, calling `chunk.embedding` during search threw `JSONDecodeError`.
- **RED Evidence**:
  ```
  FAILED tests/test_policy_ingestion_and_vectors.py::TestVectorStore::test_invalid_and_corrupt_persisted_vectors_handled_safely
  json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes
  ```
- **Correction**: Updated `PolicyChunk.embedding` to validate type list and added `try...except` handling in `VectorStore.search` to safely skip corrupt chunks.
- **GREEN Evidence**: Test passed cleanly.

### Defect 3: Unvalidated File Path Traversal in Database Model
- **Vulnerability**: `PolicyDocument` model accepted unvalidated relative traversal paths (`../../etc/passwd`).
- **Correction**: Added `@validates("file_path")` on `PolicyDocument` rejecting empty values or traversal `..` tokens.
- **GREEN Evidence**: Verified via `test_policy_document_rejects_path_traversal_in_file_path`.

---

## 6. Test Suite Results

- **Policy Ingestion & Vector Tests**: 38 tests total (37 passed, 1 skipped due to Windows unprivileged symlink restrictions).
- **Full Project Test Suite**:
  ```
  ================= 357 passed, 1 skipped, 3 warnings in 6.97s ==================
  ```
  Zero regressions across all existing Phase 1–4 tests (320 tests) and 37 Phase 5.1 tests.

---

## 7. Migration Readiness & Offline Readiness

- **PostgreSQL Migration**: Fully defined in `docs/migrations/001_create_policy_rag_tables.sql`.
- **Offline Readiness**: `fastembed` model weights for `BAAI/bge-small-en-v1.5` (~33MB ONNX) are pre-cached in local environment; zero network calls occur during unit tests or cached runs.
- **Remaining Risks for Batch 5.2**:
  - Grounded answer generation in Batch 5.2 must ensure prompt-injection shielding around untrusted policy chunk text.
  - Local LLM inference (e.g. Ollama) must degrade gracefully if the local inference daemon is unreachable, falling back to raw retrieved citations.

---

## 8. Completion Confirmation

Phase 5.1 is complete, verified, and secure. Batch 5.2 has not been started. No git commits or pushes have been made.

