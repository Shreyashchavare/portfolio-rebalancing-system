# Phase 1 — Repository Audit & Safe Cleanup Report

**Project:** YottaFlex — Policy-Constrained Portfolio Rebalancing System  
**Date:** November 12, 2026  
**Status:** Completed  
**Execution Mode:** Read-Only Audit & Evidence-Based Safe Cleanup  

---

## 1. Repository Structure Overview

A comprehensive inspection of the root directory and all subdirectories was performed. The repository represents a production-grade modular monolithic application comprising a FastAPI backend, a React/TypeScript frontend, a synthetic data generation and validation framework, local vector search assets, comprehensive policy documentation, and a full regression test suite.

### Root Directory Layout

```
portfolio-rebalancing-system/
├── .env                                       # Local environment variables (PostgreSQL, auth, LLM configs)
├── .env.example                               # Production/development environment variable template
├── .gitignore                                 # Git ignore definitions (caches, local models, build artifacts)
├── CACHEDIR.TAG                               # Cache directory tag
├── pytest.ini                                 # Pytest configuration (testpaths = tests)
├── README.md                                  # Complete system architecture and operations documentation
├── requirements.txt                           # Backend Python package requirements
├── alembic/                                   # Database migration scaffolding (.gitkeep)
├── app/                                       # Modular monolithic FastAPI backend application
│   ├── api/                                   # HTTP presentation layer (dependencies, v1 route handlers)
│   ├── core/                                  # Application configuration and settings (Pydantic Settings)
│   ├── database/                              # Engine lifecycle and SessionLocal factory
│   ├── models/                                # 15 Declarative SQLAlchemy ORM models
│   ├── schemas/                               # Pydantic request/response validation schemas
│   └── services/                              # Domain business services (analytics, rebalancing, policy_rag, etc.)
├── data/                                      # Master reference datasets and SQL seed scripts
│   ├── full/                                  # Full-scale dataset (100 portfolios, CSV, JSON, seed_data.sql)
│   └── starter/                               # Starter dataset (10 portfolios, CSV, JSON, seed_data.sql)
├── docs/                                      # Architecture guides, data dictionary, API specs, and SQL migrations
│   └── migrations/                            # Production SQL migration scripts (000 to 003)
├── frontend/                                  # React 18 + TypeScript + Vite + Tailwind CSS single-page application
├── models--Qdrant--bge-small-en-v1.5-onnx-Q/  # Local FastEmbed ONNX embedding model weights cache (~67MB)
├── policy_documents/                          # Ground-truth markdown compliance policies for Policy RAG
├── prompts/                                   # Complete historical audit prompts (Phase 0 through Phase 8)
├── scripts/                                   # Operational scripts (seed_database.py, ingest_policies.py, demo)
├── synthetic_data/                            # Synthetic dataset generators, validators, and exporters
└── tests/                                     # 44 test files containing 507 unit and integration tests
```

---

## 2. Current Backend and Frontend Architecture

### Intended Architecture Alignment

The system adheres strictly to the target architecture:
- **One FastAPI backend** running on Python 3.12.10.
- **One React + TypeScript frontend** powered by Vite, TanStack Query, and Tailwind CSS.
- **One PostgreSQL database** (with in-memory SQLite support for rapid zero-dependency unit tests).
- **Modular monolithic backend architecture** with zero microservices, message queues, or distributed brokers.

### Expected Backend Business Modules Verification

All nine expected business modules are implemented and operational:

| # | Expected Business Module | Implementation Location | Architectural Status |
|---|---|---|---|
| 1 | **Authentication and RBAC** | `app/api/dependencies.py`<br>`app/core/config.py` | Implements fail-closed role verification (`ADMIN`, `REVIEWER`, `PORTFOLIO_MANAGER`, `COMPLIANCE_OFFICER`, `VIEWER`). Development mock auth is strictly prohibited in production. |
| 2 | **Portfolio Management** | `app/models/portfolio.py`<br>`app/models/holding.py`<br>`app/models/instrument.py`<br>`app/models/target_allocation.py` | Complete domain model with foreign keys, composite constraints, asset class enumerations, and validation. |
| 3 | **Valuation and Drift Analysis** | `app/services/portfolio_analytics_service.py`<br>`app/api/v1/analytics.py` | Deterministic asset-class and position valuation, absolute/relative drift calculations, and threshold rebalance trigger detection. |
| 4 | **Rebalancing Proposal Generation** | `app/services/rebalancing_service.py`<br>`app/api/v1/rebalancing.py` | Deterministic trade sizing, lot-size quantization, tiered fee calculation, and cash-solvency enforcement. |
| 5 | **Constraint Evaluation** | `app/services/rebalancing_service.py`<br>`app/models/constraint.py` | Pre-trade and post-trade evaluation of prohibited assets, min/max allocations, and turnover limits. |
| 6 | **Trade Simulation** | `app/services/rebalancing_service.py` | Post-trade portfolio simulation calculating hypothetical allocations, cash balance, and fee deductions prior to commitment. |
| 7 | **Policy RAG** | `app/services/policy_rag/`<br>`app/models/policy_document.py`<br>`app/api/v1/policies.py` | Local ONNX vector search (`BAAI/bge-small-en-v1.5`), policy family version resolution, chunk extraction, and citation grounding. |
| 8 | **Approval and Audit History** | `app/services/approval/`<br>`app/services/audit/`<br>`app/api/v1/approvals.py` | Human-in-the-loop review governance, two-person rule enforcement, atomic proposal state transitions, and tamper-evident audit logging. |
| 9 | **Lightweight Workflow Coordination** | `app/services/orchestration/`<br>`app/services/explanation/`<br>`app/api/v1/workflows.py` | Deterministic stateful workflow executor, idempotency control, citation validation, and natural language explanation generation. |

> **Authoritative Determinism**: Deterministic financial math and policy constraints remain authoritative across all workflows. Policy RAG is strictly utilized to provide contextual excerpts and grounded citations; it never overrides financial constraints or trade calculations.

---

## 3. Findings About the `rag` Directory

1. **Exact Location & Contents**:
   - Location: `app/rag`
   - Content: Single file `app/rag/__init__.py` containing a single line: `"""Policy-based RAG components."""`.
   - File size: 35 bytes.
2. **Repository Search & Usage**:
   - Backend search (`git grep -i "app\.rag"`, `rg`, AST parser): **0 imports or references**.
   - API routes, schemas, core config, models, and scripts: **0 references**.
   - Frontend and documentation: **0 references**.
   - Test suite (`tests/`): **0 references**.
3. **Actual Implementation Location**:
   - In Phase 5 ("Policy RAG"), the team implemented the entire RAG subsystem under `app/services/policy_rag/`:
     * `document_extractor.py` (PDF, Markdown, plain text parsing)
     * `embedding_service.py` (Local ONNX inference with `BAAI/bge-small-en-v1.5`)
     * `llm_client.py` (Ollama integration with prompt-injection defense)
     * `policy_rag_service.py` (Semantic retrieval, policy family version filtering)
     * `text_chunker.py` (Configurable token/character chunking with overlap)
     * `vector_store.py` (Relational vector persistence and cosine similarity query engine)
   - Schemas are located in `app/schemas/policy_rag.py`.
   - API endpoints are located in `app/api/v1/policies.py`.
   - ORM models are located in `app/models/policy_document.py`.
4. **Architecture Requirement**:
   - `app/rag` was an initial scaffold placeholder created during Phase 0.1 (`chore: establish Python project scaffold and test setup`, commit `4556304`). It was never populated because the project standardized all domain logic under `app/services/`.
5. **Future Plans**:
   - None of the future roadmap documents or Phase 8 prompts reference `app/rag`.
6. **Decision**:
   - **Safely removed** in accordance with Decision Rule 1 ("If a directory is genuinely empty, unused, unreferenced, and unnecessary, remove it").

---

## 4. Findings About the `agent` Directory

1. **Exact Location & Contents**:
   - Location: `app/agent`
   - Content: Single file `app/agent/__init__.py` containing a single line: `"""Single-agent orchestration components."""`.
   - File size: 45 bytes.
2. **Repository Search & Usage**:
   - Backend search (`git grep -i "app\.agent"`, `rg`, AST parser): **0 imports or references**.
   - API routes, schemas, core config, models, and scripts: **0 references**.
   - Frontend and documentation: **0 references**.
   - Test suite (`tests/`): **0 references**.
3. **Actual Implementation Location**:
   - In Phase 6 ("Agentic Workflow Orchestration"), the team implemented lightweight workflow orchestration in `app/services/orchestration/` and `app/services/explanation/`:
     * `workflow_context.py` (In-memory execution context and stage state bag)
     * `workflow_executor.py` (Deterministic multi-step rebalancing pipeline)
     * `workflow_service.py` (Workflow persistence, execution lifecycle, idempotency)
     * `workflow_state.py` (State machine definitions and transition guardrails)
     * `explanation_service.py` (Grounded LLM trade explanations)
     * `citation_validator.py` (Citation verification against retrieved policy chunks)
   - Schemas are located in `app/schemas/orchestration.py` and `app/schemas/explanation.py`.
   - API endpoints are located in `app/api/v1/workflows.py`.
   - ORM models are located in `app/models/workflow_run.py`.
4. **Architecture Requirement**:
   - `app/agent` was an initial scaffold placeholder created during Phase 0.1 (commit `4556304`). When Phase 6 was implemented, an explicit architectural decision was made to implement a deterministic workflow engine rather than an unconstrained autonomous agent, placing the services inside `app/services/orchestration/`.
5. **Future Plans**:
   - None of the future plans or active prompts reference `app/agent`.
6. **Decision**:
   - **Safely removed** in accordance with Decision Rule 1.

---

## 5. Other Empty or Unnecessary Directories Discovered

During the recursive repository walk, the following additional empty or special-purpose directories were evaluated:

1. **`.locks/`**:
   - Located at repository root.
   - Contained one subfolder `.locks/models--Qdrant--bge-small-en-v1.5-onnx-Q` with zero files.
   - Generated as an untracked lock directory by Hugging Face / FastEmbed model download routines.
   - Evaluated as transient and unnecessary.
2. **`alembic/`**:
   - Located at repository root.
   - Contains only `.gitkeep`.
   - No `alembic.ini` or migration scripts exist inside this directory; active migrations are located in `docs/migrations/`.
   - Evaluated for retention vs removal.
3. **`models--Qdrant--bge-small-en-v1.5-onnx-Q/blobs`**:
   - Located inside the local ONNX model cache folder.
   - Contains 0 files (Hugging Face snapshot format stores files under `snapshots/`).
   - Part of the git-ignored local ONNX runtime cache.
4. **`frontend/dist/`**:
   - Located at `frontend/dist`.
   - Contains static build artifacts from previous builds. Tracked in `frontend/.gitignore`.

---

## 6. Directories and Files Safely Removed, with Reasons

| Target Path | Type | Reason for Removal | Verification Before Removal |
|---|---|---|---|
| `app/rag/` (`app/rag/__init__.py`) | Directory & File | Abandoned Phase 0 scaffolding stub; 0 lines of code; 0 imports or references across repo; RAG is fully implemented in `app/services/policy_rag/`. | Checked git history, AST parsing, grep across codebase, and verified all 507 backend tests pass without it. |
| `app/agent/` (`app/agent/__init__.py`) | Directory & File | Abandoned Phase 0 scaffolding stub; 0 lines of code; 0 imports or references across repo; workflow orchestration is fully implemented in `app/services/orchestration/`. | Checked git history, AST parsing, grep across codebase, and verified all 507 backend tests pass without it. |
| `.locks/` | Directory | Transient empty directory generated during model caching; contains 0 files; not tracked in Git. | Verified directory was completely empty of files. |

---

## 7. Directories and Files Retained, with Reasons

| Retained Path | Reason for Retention |
|---|---|
| `alembic/` (with `.gitkeep`) | Retained per safety rule ("Do not assume a directory is unnecessary merely because it is currently empty"). Preserves standard Alembic scaffolding while `requirements.txt` includes `alembic>=1.13.0`. |
| `models--Qdrant--bge-small-en-v1.5-onnx-Q/` | Essential local FastEmbed ONNX weights (~67MB). Enables 100% offline vector embedding generation without network calls during development and testing. Tracked in `.gitignore`. |
| `data/full/` & `data/starter/` | Canonical seed datasets (100 portfolios and 10 portfolios respectively) in CSV, JSON, and SQL formats. Directly required by `scripts/seed_database.py` and tested by `test_seed_database.py`. |
| `policy_documents/` | Ground-truth investment mandates (`esg_exclusion_policy_v1.md`, `global_equity_mandate_v1.md`, etc.) required for policy ingestion tests and RAG demonstration. |
| `prompts/` (Phases 0 to 8 & `prompts.zip`) | Preserved in full per Section 5 instructions to ensure complete historical auditability. |
| `synthetic_data/` | Full data generation framework (10 generators, 2 validators, anomaly injector, exporters). Essential foundation with 18 dedicated test suites. |
| `docs/migrations/` | Authoritative SQL schema migration scripts (`000_create_core_tables.sql` through `003_add_orchestration_and_audit_tables.sql`). |
| `frontend/` | Complete active React application under active development. |

---

## 8. Existing RAG and Agent-Related Functionality Locations

The table below maps where all RAG and Agent/Workflow capabilities currently live in the repository:

### Policy RAG Component Map

| Capability | File Location | Key Class / Function |
|---|---|---|
| Multi-format Text Extraction | `app/services/policy_rag/document_extractor.py` | `DocumentExtractor.extract_text()` (PDF, Markdown, TXT) |
| Semantic Text Chunking | `app/services/policy_rag/text_chunker.py` | `TextChunker.chunk_text()` |
| Local ONNX Embeddings | `app/services/policy_rag/embedding_service.py` | `EmbeddingService` (`BAAI/bge-small-en-v1.5`, 384 dims) |
| Relational Vector Store | `app/services/policy_rag/vector_store.py` | `VectorStore` (Cosine similarity, L2 distance) |
| Semantic Search & Filtering | `app/services/policy_rag/policy_rag_service.py` | `PolicyRAGService.search_chunks()`, `retrieve_relevant_policies()` |
| Policy Family Versioning | `app/services/policy_rag/policy_rag_service.py` | `get_latest_effective_policy()`, family identity resolution |
| LLM Client & Guardrails | `app/services/policy_rag/llm_client.py` | `OllamaLLMClient`, `detect_prompt_injection()`, citation grounding |
| Policy Database Models | `app/models/policy_document.py` | `PolicyDocument`, `PolicyChunk` |
| Policy Pydantic Schemas | `app/schemas/policy_rag.py` | `PolicySearchRequest`, `PolicyAskRequest`, `PolicyCitation`, etc. |
| Policy API Endpoints | `app/api/v1/policies.py` | `/api/v1/policies/search`, `/api/v1/policies/ask`, `/api/v1/policies/ingest` |
| Ingestion CLI Tool | `scripts/ingest_policies.py` | Ingests all policy files into PostgreSQL / SQLite vector store |
| Policy Test Suites | `tests/test_policy_ingestion_and_vectors.py`<br>`tests/test_policy_rag_api.py`<br>`tests/test_ingest_policies.py` | 55 unit and integration tests |

### Agent & Workflow Orchestration Component Map

| Capability | File Location | Key Class / Function |
|---|---|---|
| Multi-Step Workflow Engine | `app/services/orchestration/workflow_executor.py` | `WorkflowExecutor.execute()` (Valuation -> Drift -> Rebalance -> Simulation -> Policy Search -> Explanation) |
| Workflow State Lifecycle | `app/services/orchestration/workflow_service.py`<br>`app/services/orchestration/workflow_state.py` | `WorkflowService`, `WorkflowState` (Idempotent state transitions) |
| Execution Context Bag | `app/services/orchestration/workflow_context.py` | `WorkflowContext` (Strongly-typed pipeline data carrier) |
| Grounded Explanation Service | `app/services/explanation/explanation_service.py` | `ExplanationService.generate_explanation()` |
| Citation Verification | `app/services/explanation/citation_validator.py` | `CitationValidator.validate_citations()` |
| Prompt Templates | `app/services/explanation/prompt_templates.py` | Rebalancing explanation system prompts and schema formatting |
| Human Approval Governance | `app/services/approval/approval_service.py` | `ApprovalService.approve_proposal()`, `reject_proposal()`, two-person rule |
| Tamper-Evident Audit Logging | `app/services/audit/audit_service.py` | `AuditService.record_event()` |
| Workflow & Audit ORM Models | `app/models/workflow_run.py`<br>`app/models/audit_event.py` | `WorkflowRun`, `AuditEvent` |
| Workflow & Approval Schemas | `app/schemas/orchestration.py`<br>`app/schemas/approval.py`<br>`app/schemas/audit.py` | `WorkflowRequest`, `WorkflowResponse`, `ApproveProposalRequest`, etc. |
| Workflow & Approval APIs | `app/api/v1/workflows.py`<br>`app/api/v1/approvals.py` | `/api/v1/workflows/rebalance`, `/api/v1/approvals/{id}/approve`, etc. |
| Orchestration Test Suites | `tests/test_workflow_orchestration.py`<br>`tests/test_explanation_service.py`<br>`tests/test_approval_audit_api.py` | 74 unit and integration tests |

---

## 9. Potential Risks and Unresolved Issues

1. **Structural Asymmetry in `app/services/`**:
   - `portfolio_analytics_service.py` (381 lines) and `rebalancing_service.py` (986 lines) are loose files in `app/services/`.
   - Newer services (`approval/`, `audit/`, `explanation/`, `orchestration/`, `policy_rag/`) are organized into dedicated subpackages.
   - Refactoring loose files into domain subpackages (`app/services/analytics/` and `app/services/rebalancing/`) should be considered in Phase 2.
2. **Size and Multi-Responsibility in `rebalancing_service.py`**:
   - At 986 lines, `rebalancing_service.py` handles trade sizing, cash solvency, lot-size rounding, fee schedules, pre-trade & post-trade constraint checking, simulation, and proposal persistence. Decomposing these concerns will improve maintainability and test isolation.
3. **Database Migration Tooling**:
   - `alembic/` currently contains only `.gitkeep`. Active migrations are manual SQL in `docs/migrations/`.
   - Risk: If PostgreSQL deployments require automated schema versioning, Alembic configuration (`env.py`, `alembic.ini`) will need to be formally linked to the declarative models in `app/models/`.
4. **Active Frontend Working Tree (Phase 8)**:
   - The frontend working tree contains uncommitted changes from an ongoing Phase 8 iteration (RBAC integration).
   - In accordance with safety restrictions, no frontend source files or test files were modified during Phase 1.
   - Identified issues to be addressed by the frontend team:
     * `src/test/shell.test.tsx` and `src/test/router.test.tsx` have selector ambiguities (`/REVIEWER/i` matches multiple elements).
     * `src/test/rbac.test.tsx` contains an unused import `'AppLayout'` causing `tsc --noEmit` to fail under strict flags.

---

## 10. Test and Build Results

### Backend Test Suite (Pytest)

- **Command**: `pytest -q`
- **Environment**: Python 3.12.10, pytest 8.4.2, SQLite in-memory test databases
- **Execution Time**: 49.01 seconds
- **Results**:
  - **Total Tests**: 507
  - **Passed**: 507 (100%)
  - **Failed**: 0
  - **Errors**: 0
  - **Skipped**: 0
- **Regression Analysis**:
  - 100% pass rate confirmed both before and after removing `app/rag` and `app/agent`.
  - Zero imports or database operations were impacted by the safe cleanup.

### Frontend Test & Build Verification

- **Vitest**: `vitest run`
  - Tests: 53 passed, 4 failed (9 test suites)
  - Cause of failure: Ongoing Phase 8 uncommitted work in `shell.test.tsx` and `router.test.tsx` where new reviewer badge elements created multiple text matches for `/REVIEWER/i`.
- **TypeScript**: `tsc --noEmit`
  - Result: 1 error in `src/test/rbac.test.tsx` (`'AppLayout' is declared but its value is never read`).
- **ESLint**: `eslint .`
  - Result: 0 errors, 1 warning (matching the unused import in `rbac.test.tsx`).
- **Safety Compliance**:
  - In strict compliance with Section 6 ("Do not modify tests merely to make them pass"), no frontend tests were modified.

---

## 11. Exact Files for Phase 2 Backend Refactoring

The following files represent the exact scope recommended for Phase 2 targeted backend refactoring:

### Primary Refactoring Candidates

1. **`app/services/rebalancing_service.py` (986 lines)**:
   - *Issue*: Monolithic file combining trade sizing, lot-size rounding, fee tiers, cash solvency, constraint evaluation, post-trade simulation, and proposal persistence.
   - *Target Structure*: Subpackage `app/services/rebalancing/`:
     * `trade_generator.py`: Delta calculation, lot rounding, and cash solvency.
     * `fee_calculator.py`: Tiered fee calculation logic.
     * `constraint_evaluator.py`: Pre-trade and post-trade constraint rule checking.
     * `simulator.py`: Post-trade allocation and cash simulation.
     * `proposal_service.py`: Proposal lifecycle and persistence manager.
     * `__init__.py`: Facade exposing `RebalancingService` for zero-breakage backwards compatibility.

2. **`app/services/portfolio_analytics_service.py` (381 lines)**:
   - *Issue*: Loose file in `app/services/` that belongs in a standardized domain package.
   - *Target Structure*: Subpackage `app/services/analytics/`:
     * `valuation_service.py`: Asset class and holding valuation logic.
     * `drift_service.py`: Target allocation comparison and drift metric calculations.
     * `trigger_service.py`: Drift threshold and rebalancing trigger evaluation.
     * `__init__.py`: Facade exposing `PortfolioAnalyticsService`.

3. **`app/services/__init__.py`**:
   - *Issue*: Currently exports loose service instances.
   - *Target Structure*: Central service registry and facade export to guarantee that `app/api/v1/` and existing tests do not experience broken import paths during subpackage refactoring.

4. **`app/api/v1/rebalancing.py`**:
   - *Scope*: Refactor endpoint dependency injections to consume the modular rebalancing subservices while preserving exact HTTP routes and Pydantic response contracts.

5. **`app/api/v1/analytics.py`**:
   - *Scope*: Refactor endpoint dependency injections to consume the modular analytics subservices while preserving exact HTTP routes and Pydantic response contracts.

6. **`app/database/session.py`**:
   - *Scope*: Standardize database engine lifecycle comments and review session context manager conventions to support nested transaction boundaries cleanly across decomposed subservices.

---

## Conclusion & Phase 1 Sign-Off

Phase 1 has fulfilled all audit objectives:
- Full repository was inspected and structural clarity established.
- `app/rag` and `app/agent` were rigorously investigated and proven to be unused Phase 0 stubs; both have been safely removed.
- All functional RAG, workflow orchestration, business logic, models, schemas, and test suites are 100% preserved.
- Backend regression test suite confirms **507 passed / 0 failed** in 49.01s.
- Zero Git commits or pushes were made.
- Clear, evidence-based roadmap delivered for Phase 2 backend refactoring.

