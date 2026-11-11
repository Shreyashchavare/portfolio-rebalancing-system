# Phase 6.0 — Agentic Workflow Orchestration: Read-Only Architecture Audit

## 0. Exact Prompt Reference
```markdown
# Phase 6.0 — Agentic Workflow Orchestration: Read-Only Architecture Audit

## Project
YottaFlex — Portfolio Rebalancing Recommendation System

Repository:
E:\Yottaflex\portfolio-rebalancing-system

## Objective
Perform a comprehensive, strictly read-only architecture audit before implementing Phase 6.
Compare the actual repository against the approved HLD, LLD and architecture decisions.
Do not implement anything during this audit.
```

---

## 1. Executive Summary

This document presents a strictly **read-only architecture audit** for **Phase 6: Agentic Workflow Orchestration** of the YottaFlex Portfolio Rebalancing System. 

The repository currently contains a complete, verified financial foundation spanning Phases 0–5:
- **Phase 3 (Analytics)**: Deterministic valuation, drift, and rebalancing trigger evaluation ([`app/services/portfolio_analytics_service.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/services/portfolio_analytics_service.py)).
- **Phase 4 (Deterministic Rebalancing)**: Trade recommendation generation, lot-size rounding, fee tiers, cash solvency, post-trade simulation, constraint gatekeeping, and proposal persistence ([`app/services/rebalancing_service.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/services/rebalancing_service.py)).
- **Phase 5 (Policy RAG)**: Multi-format document extraction, FastEmbed embeddings, relational vector store, temporal policy filtering, policy family identity, Ollama LLM integration, and prompt-injection defense ([`app/services/policy_rag/`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/services/policy_rag/)).

**Current Test Status**: **387 passed, 1 skipped** (Windows OS symlink defense), **0 failed** across 388 items in 7.52 seconds.  
**Git Working Tree**: Clean on branch `main` at commit `5109409`, synchronized with `origin/main`.  
**Read-Only Integrity**: Zero application code, tests, dependencies, or database schemas were modified during this audit.

The system is ready for Phase 6.0 planning. Phase 6 must bridge the gap between deterministic calculations and human review by implementing workflow execution, grounded explanation generation, approval governance, and audit history.

---

## 2. Current Architecture and Actual Execution Flow

### 2.1 Current Request Flow
Currently, client requests interact with independent modular services:

```
FastAPI Router (/api/v1/portfolios/{id}/rebalance/proposals)
      │
      ▼
RebalancingService.create_and_persist_proposal()
      │
      ├──> PortfolioAnalyticsService.get_portfolio_valuation()
      │        └──> synthetic_data.calculations (position values, cash weights)
      │
      ├──> PortfolioAnalyticsService.get_portfolio_drift()
      │        └──> TargetAllocation drift calculation, action signals
      │
      ├──> RebalancingService.generate_rebalance_trades()
      │        ├──> match_fee_tier(), calculate_trade_fee()
      │        └──> Cash solvency check (executable sells fund buys)
      │
      ├──> RebalancingService.simulate_post_trade_state() (Initial)
      │        └──> In-memory position, allocation, and fee simulation
      │
      ├──> RebalancingService.evaluate_constraints()
      │        └──> Active Constraints (MAX_POSITION_WEIGHT, EXCLUDED_INSTRUMENT, etc.)
      │
      ├──> Cash reconciliation & re-simulation (excluding blocked trades)
      │
      └──> Transactional Persistence (Session.commit)
               ├──> RebalanceProposal (RB-YYYY-NNNNNN)
               └──> Trade records (TRD-NNNNNN)
```

In parallel, Policy RAG operates via a dedicated endpoint:
```
FastAPI Router (/api/v1/policies/ask)
      │
      ▼
PolicyRAGService.ask_question()
      │
      ├──> VectorStore.search() (FastEmbed cosine similarity, date & status filter)
      ├──> Conflict Detection (evaluates policy_family_id across retrieved chunks)
      ├──> _build_grounded_prompt() (XML isolation, query & context sanitization)
      └──> LocalLLMClient.generate_answer() (Ollama /api/generate)
               └──> Graceful fallback if offline (LLM_UNAVAILABLE -> evidence chunks)
```

### 2.2 Target Phase 6 Orchestrated Flow
Phase 6 will unify these independent capabilities into an end-to-end orchestrated workflow:

```
User / API Client
      │
      ▼
FastAPI Router (/api/v1/workflows/rebalance)
      │
      ▼
WorkflowService (Facade & Orchestrator)
      │
      ├── 1. WorkflowRun initialized (Status: INITIATED)
      │
      ├── 2. Analytics & Proposal Step (Status: PROPOSAL_GENERATED)
      │        └──> RebalancingService.create_and_persist_proposal() (Exactly once)
      │
      ├── 3. Policy Context Retrieval Step (Status: POLICY_EVALUATED)
      │        └──> PolicyRAGService.search_policies() (Grounded in as_of_date)
      │
      ├── 4. Grounded Explanation Generation (Status: EXPLAINED)
      │        └──> ExplanationService (Synthesizes trades, drift, simulation & policy citations)
      │
      ├── 5. Governance Check (Status: AWAITING_APPROVAL or REJECTED)
      │        └──> Hard blocked -> REJECTED; Executable -> AWAITING_APPROVAL
      │
      └── 6. Audit Trail Logging
               └──> AuditService.record_event() (Immutable audit history)
```

---

## 3. Existing Service Contracts with Exact Method Signatures

### 3.1 `PortfolioAnalyticsService`
- **File**: [`app/services/portfolio_analytics_service.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/services/portfolio_analytics_service.py)
- **Constructor**:
  ```python
  def __init__(self, session: Session) -> None
  ```
- **Public Methods**:
  1. `get_portfolio_valuation(portfolio_id: str, as_of_date: date) -> PortfolioValuationResult`
     - Evaluates current holdings against market prices on or before `as_of_date`.
     - Calculates market values, cash, asset class weights, price ages, and staleness flags.
  2. `get_portfolio_drift(portfolio_id: str, as_of_date: date) -> PortfolioDriftResult`
     - Compares valuation against effective `TargetAllocation` records.
     - Computes percentage and monetary drift, BUY/SELL/HOLD action signals, and invokes rebalance trigger evaluation.
  3. `evaluate_rebalance_trigger(portfolio_id: str, as_of_date: date, valuation: PortfolioValuationResult) -> RebalanceTriggerEvaluation`
     - Evaluates active portfolio-scoped constraints (`MAX_POSITION_WEIGHT`, `MIN_POSITION_WEIGHT`).
- **Exceptions Raised**: `PortfolioNotFoundError`, `MissingPriceError`.

### 3.2 `RebalancingService`
- **File**: [`app/services/rebalancing_service.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/services/rebalancing_service.py)
- **Constructor**:
  ```python
  def __init__(self, session: Session) -> None
  ```
- **Public Methods**:
  1. `generate_rebalance_trades(portfolio_id: str, as_of_date: date) -> RebalanceRecommendationResult`
     - Generates lot-sized, fee-matched BUY and SELL recommendations based on allocation drift.
  2. `simulate_post_trade_state(portfolio_id: str, as_of_date: date, proposed_trades: list[ProposedTrade]) -> PostTradeSimulationResult`
     - Simulates in-memory post-trade positions, asset allocations, cash balance, and fee totals.
  3. `evaluate_constraints(portfolio_id: str, as_of_date: date, proposed_trades: list[ProposedTrade], simulation: PostTradeSimulationResult) -> tuple[list[ConstraintFinding], list[str], list[str]]`
     - Returns `(findings, hard_violations, warnings)`.
  4. `create_and_persist_proposal(portfolio_id: str, as_of_date: date) -> RebalanceProposalResponse`
     - Atomic, transactional execution of trade generation, simulation, constraint gatekeeping, and persistence of `RebalanceProposal` and `Trade` records.
- **Exceptions Raised**: `PortfolioNotFoundError`, `MissingPriceError`, `ConstraintViolationError`, `ValueError`.

### 3.3 `PolicyRAGService`
- **File**: [`app/services/policy_rag/policy_rag_service.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/services/policy_rag/policy_rag_service.py)
- **Constructor**:
  ```python
  def __init__(
      self,
      session: Session,
      embedding_service: Optional[BaseEmbeddingService] = None,
      vector_store: Optional[VectorStore] = None,
      llm_client: Optional[BaseLLMClient] = None,
      extractor: Optional[DocumentExtractor] = None,
      chunker: Optional[TextChunker] = None,
  ) -> None
  ```
- **Public Methods**:
  1. `ingest_document(request: PolicyIngestRequest) -> PolicyIngestResponse`
  2. `search_policies(query: str, as_of_date: Optional[date] = None, document_type: Optional[str] = None, document_id: Optional[str] = None, status: Optional[Union[str, Sequence[str]]] = None, top_k: int = 5, similarity_threshold: Optional[float] = None) -> List[PolicySearchResult]`
  3. `ask_question(query: str, as_of_date: Optional[date] = None, document_type: Optional[str] = None, top_k: int = 5, similarity_threshold: Optional[float] = None) -> PolicyAskResponse`
  4. `get_document_details(document_id: str) -> PolicyDocumentDetailResponse`
- **Exceptions Raised**: `PolicyNotFoundError`, `PathTraversalError`, `UnsupportedFileTypeError`, `DocumentSizeLimitExceededError`, `EmptyDocumentError`, `CorruptDocumentError`, `PolicyIngestionError`, `LLMUnavailableError`, `LLMResponseError`.

### 3.4 `LocalLLMClient` & `FakeLLMClient`
- **File**: [`app/services/policy_rag/llm_client.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/services/policy_rag/llm_client.py)
- **Public Interface**:
  ```python
  class BaseLLMClient(ABC):
      @property
      @abstractmethod
      def model_name(self) -> str: ...
      @abstractmethod
      def generate_answer(self, prompt: str) -> str: ...
  ```
- **Exceptions Raised**: `LLMUnavailableError`, `LLMResponseError`, `LLMClientError`.

### 3.5 `EmbeddingService` & `FakeEmbeddingService`
- **File**: [`app/services/policy_rag/embedding_service.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/services/policy_rag/embedding_service.py)
- **Public Interface**:
  ```python
  class BaseEmbeddingService(ABC):
      @property
      @abstractmethod
      def model_name(self) -> str: ...
      @property
      @abstractmethod
      def dimension(self) -> int: ...
      @abstractmethod
      def generate_embedding(self, text: str) -> List[float]: ...
      @abstractmethod
      def generate_embeddings(self, texts: List[str]) -> List[List[float]]: ...
  ```

### 3.6 `VectorStore`
- **File**: [`app/services/policy_rag/vector_store.py`](file:///e:/Yottaflex/portfolio-rebalancing-system/app/services/policy_rag/vector_store.py)
- **Public Methods**:
  1. `store_document_chunks(document: PolicyDocument, chunks: List[Chunk]) -> List[PolicyChunk]`
  2. `search(query: str, as_of_date: Optional[date] = None, document_id: Optional[str] = None, document_type: Optional[str] = None, status: Optional[Union[str, Sequence[str]]] = PolicyStatus.ACTIVE.value, top_k: int = 5, similarity_threshold: Optional[float] = None) -> List[PolicySearchResult]`

---

## 4. Existing Versus Missing Components

| Component | Status | Existing Location / Notes | Missing Elements to Implement |
| :--- | :--- | :--- | :--- |
| **Portfolio Analytics** | Complete | `app/services/portfolio_analytics_service.py` | None (reuse directly) |
| **Deterministic Rebalancing Engine** | Complete | `app/services/rebalancing_service.py` | None (reuse directly) |
| **Policy Ingestion & Vector Retrieval** | Complete | `app/services/policy_rag/` | None (reuse directly) |
| **Local LLM Client** | Complete | `app/services/policy_rag/llm_client.py` | None (reuse directly for explanations) |
| **Workflow State & Transitions** | Missing | None | State machine enum and transitions validator |
| **Workflow Context & Executor** | Missing | None | `WorkflowContext`, `WorkflowExecutor`, pipeline steps |
| **Workflow Service (Facade)** | Missing | None | `WorkflowService.run_rebalance_workflow()` |
| **Workflow Persistence Model** | Missing | None | `WorkflowRun` SQLAlchemy entity and schema |
| **Grounded Explanation Service** | Missing | None | `ExplanationService`, structured evidence synthesis |
| **Explanation Validation & Citations** | Missing | None | Verification of LLM explanation citations |
| **Human Approval & Rejection Logic** | Incomplete | `RebalanceProposal` has status fields | Service logic for transition checks & trade status sync |
| **Reviewer Identity Tracking** | Incomplete | `reviewed_at`, `review_reason` exist | `reviewer_id` column on `RebalanceProposal` |
| **Audit Trail Persistence** | Missing | None | `AuditEvent` entity, `AuditService.record_event()` |
| **Workflow & Approval APIs** | Missing | None | FastAPI routers for workflow and approval |

---

## 5. HLD Gaps

1. **Absence of Unified Workflow Facade**:  
   Clients currently must call `/api/v1/portfolios/{id}/rebalance/proposals` directly. There is no high-level facade that coordinates proposal generation, policy retrieval, grounded narrative generation, and governance checks in a single orchestrated flow.
2. **Missing Explanation Synthesis Layer**:  
   While `PolicyRAGService.ask_question()` can answer general compliance queries, there is no service that synthesizes the specific financial outputs (starting drift, generated trades, simulation results, constraint violations) with relevant policy citations into an executive explanation for a portfolio manager.
3. **Decoupled Approval and Financial Engine**:  
   The `RebalanceProposal` model possesses `ProposalStatus` and `ReviewDecision` enums, but no application service or API endpoint exists to transition a proposal from `PENDING_REVIEW` to `APPROVED` or `REJECTED`. Trade records remain in `PROPOSED` status perpetually.
4. **Lack of Centralized Audit Log**:  
   There is no persistent audit table tracking who initiated a rebalancing workflow, who approved/rejected it, when, and the prior/new states.

---

## 6. LLD Gaps

1. **Missing Orchestration Package** (`app/services/orchestration/`):
   - `workflow_state.py`: Needs explicit `WorkflowStatus` enum (`INITIATED`, `ANALYZING`, `PROPOSAL_GENERATED`, `EXPLAINED`, `AWAITING_APPROVAL`, `APPROVED`, `REJECTED`, `FAILED`).
   - `workflow_transitions.py`: Deterministic transition validator preventing invalid state jumps.
   - `workflow_context.py`: Strongly typed state container carrying portfolio ID, as-of date, proposal response, policy chunks, explanation, and error details across steps.
   - `workflow_executor.py`: Step-by-step pipeline runner handling errors and recording step timings.
   - `workflow_service.py`: Public facade entry point.
2. **Missing Explanation Package** (`app/services/explanation/`):
   - `explanation_service.py`: Builds prompt from structured financial facts and policy evidence, calls `BaseLLMClient`, and handles graceful fallback if LLM is unavailable.
   - `prompt_templates.py`: Controlled, prompt-injection-shielded templates for rebalancing explanation.
   - `explanation_validator.py`: Ensures generated narrative does not hallucinate trade quantities or omit hard blocks.
3. **Missing Approval Package** (`app/services/approval/`):
   - `approval_service.py`: Validates proposal is in `PENDING_REVIEW`, updates proposal decision, synchronizes `Trade.status` (`APPROVED` or `REJECTED`), records `reviewer_id`, `reviewed_at`, `review_reason`.
4. **Missing Audit Package** (`app/services/audit/`):
   - `audit_service.py`: Records immutable `AuditEvent` records within active database transactions.
5. **Missing Database Models**:
   - `WorkflowRun`: In `app/models/workflow_run.py`.
   - `AuditEvent`: In `app/models/audit_event.py`.
   - Column `reviewer_id: Mapped[Optional[str]]` on `RebalanceProposal`.

---

## 7. Design-Pattern Assessment

| Pattern | Already Exists? | Location | Genuinely Useful? | Recommended Action for Phase 6 |
| :--- | :--- | :--- | :--- | :--- |
| **State** | Partially | `ProposalStatus`, `ReviewDecision` in `app/models/` | **Yes** | Implement `WorkflowStatus` and transition validator to control lifecycle without heavy class hierarchies. |
| **Command** | No | None | **Moderate** | Use discrete step functions (`run_analytics_and_proposal_step`, `run_policy_retrieval_step`, etc.) rather than full GoF Command objects. |
| **Strategy** | **Yes** | `BaseLLMClient`, `BaseEmbeddingService` in `policy_rag/` | **Yes** | Reuse directly. Allows swapping `FakeLLMClient` in tests and `LocalLLMClient` in production. |
| **Adapter** | **Yes** | `LocalLLMClient` (adapts Ollama API), `DocumentExtractor` | **Yes** | Keep existing adapters intact; no new external adapters required. |
| **Repository** | No | Direct SQLAlchemy `Session` queries | **No** | Unnecessary abstraction. SQLAlchemy 2.0 already provides Data Mapper / Unit of Work. Avoid repository boilerplate. |
| **Factory** | **Yes** | `_SessionLocalFactory` in `app/database/session.py` | **Moderate** | Use simple helper factory `get_workflow_service(db)` for dependency wiring in FastAPI. |
| **Dependency Injection** | **Yes** | `get_db()`, `get_policy_rag_service()` in FastAPI | **Yes** | Continue standard FastAPI DI conventions (`Depends(get_workflow_service)`). |
| **Specification** | Embedded | Constraints evaluated in `rebalancing_service.py` | **No** | Do not refactor existing working constraint logic. |
| **Facade** | Partially | `RebalancingService` coordinates calculations | **Yes** | Implement `WorkflowService` as the unified high-level facade for clients. |
| **Observer / Domain Events** | No | None | **Moderate** | Use explicit synchronous audit calls (`AuditService.record_event`) within transactions. Avoid async messaging/event bus. |
| **Builder / Template Method** | No | None | **No** | Unnecessary complexity for this modular monolith. |

---

## 8. Database and Transaction Assessment

### 8.1 Transaction Boundary Analysis
- In `RebalancingService.create_and_persist_proposal`: Proposal and Trade rows are committed atomically.
- **Workflow Orchestration Boundary**:
  1. `WorkflowRun` must be created in its own initial transaction so that if subsequent steps crash, the workflow record exists with `status="FAILED"`.
  2. Proposal creation commits `RebalanceProposal` and `Trade`s. The `workflow_run.proposal_id` must be updated and committed immediately.
  3. Approval/Rejection must run in a single atomic transaction: updating `RebalanceProposal.status`, all child `Trade.status` rows, `WorkflowRun.status`, and writing an `AuditEvent`. If any write fails, everything rolls back.

### 8.2 Models Required
1. **`WorkflowRun`**:
   - `workflow_id VARCHAR(50) PRIMARY KEY`
   - `portfolio_id VARCHAR(40) NOT NULL REFERENCES portfolio(portfolio_id)`
   - `proposal_id VARCHAR(30) REFERENCES rebalance_proposal(proposal_id)`
   - `status VARCHAR(30) NOT NULL` (CheckConstraint valid statuses)
   - `as_of_date DATE NOT NULL`
   - `initiated_by VARCHAR(100)`
   - `error_message TEXT`
   - `context_json TEXT` (serialized diagnostic/metadata bag)
   - `created_at TIMESTAMP WITH TIME ZONE NOT NULL`
   - `updated_at TIMESTAMP WITH TIME ZONE NOT NULL`
   - `completed_at TIMESTAMP WITH TIME ZONE`
2. **`AuditEvent`**:
   - `event_id VARCHAR(50) PRIMARY KEY`
   - `entity_type VARCHAR(50) NOT NULL` (`WORKFLOW`, `PROPOSAL`, `TRADE`)
   - `entity_id VARCHAR(50) NOT NULL`
   - `action VARCHAR(50) NOT NULL` (`WORKFLOW_INITIATED`, `PROPOSAL_GENERATED`, `PROPOSAL_APPROVED`, `PROPOSAL_REJECTED`)
   - `actor_id VARCHAR(100) NOT NULL`
   - `previous_state VARCHAR(50)`
   - `new_state VARCHAR(50)`
   - `metadata_json TEXT`
   - `timestamp TIMESTAMP WITH TIME ZONE NOT NULL`
3. **`RebalanceProposal` Update**:
   - Add `reviewer_id VARCHAR(100)` column (nullable).

### 8.3 Migration Status
Existing migrations in `docs/migrations/`:
- `001_create_policy_rag_tables.sql`
- `002_add_policy_family_id.sql`
*Deployment Limitation*: Neither migration has been applied to a live PostgreSQL production instance yet. In-memory SQLite is used for automated testing. Phase 6 will add `003_add_orchestration_and_audit_tables.sql`.

---

## 9. Security and Financial-Safety Assessment

### 9.1 Inviolable Financial Safety Invariants
1. **Read-Only LLM Sandbox**:  
   The LLM has zero direct write access to the database. It cannot alter holdings, prices, fee schedules, or constraints.
2. **Deterministic Financial Primacy**:  
   All BUY/SELL quantities, prices, fees, cash balances, and post-trade allocations are computed 100% deterministically by `synthetic_data.calculations` and `RebalancingService`. The LLM's role is strictly generating an explanatory narrative.
3. **Immutability of Hard Constraints**:  
   If `RebalancingService.evaluate_constraints()` flags a hard violation, the proposal is marked `REJECTED` by deterministic code. No prompt, agent, or LLM output can unblock a hard violation.
4. **Approval Exclusivity**:  
   Proposals cannot be approved by an automated LLM call. Approval requires an authenticated user calling `POST /api/v1/proposals/{proposal_id}/approve`.
5. **Prompt-Injection Defense**:  
   User input and policy chunks are strictly encapsulated in `<policy_context>` XML delimiters with breakout sanitization, as verified in Phase 5.

---

## 10. API Additions Required

To complete Phase 6 without duplicate endpoints:

1. **`POST /api/v1/workflows/rebalance`**:
   - Triggers the complete rebalance workflow for a portfolio and as-of date.
   - Idempotent: returns existing run if already initiated for the same request parameters.
   - Returns full `WorkflowResponse` (workflow status, proposal summary, trades, simulation, policy citations, explanation narrative).
2. **`GET /api/v1/workflows/{workflow_id}`**:
   - Retrieves workflow status, step progress, timings, and error diagnostics.
3. **`GET /api/v1/workflows/{workflow_id}/explanation`**:
   - Retrieves the grounded narrative explanation and citation list.
4. **`POST /api/v1/proposals/{proposal_id}/approve`**:
   - Accepts `ApprovalRequest(reviewer_id, review_reason)`.
   - Validates state is `PENDING_REVIEW`, updates proposal to `APPROVED`, updates executable trades to `APPROVED`, writes `AuditEvent`.
5. **`POST /api/v1/proposals/{proposal_id}/reject`**:
   - Accepts `RejectionRequest(reviewer_id, review_reason)`.
   - Updates proposal to `REJECTED`, updates trades to `REJECTED`, writes `AuditEvent`.
6. **`GET /api/v1/proposals/{proposal_id}`**:
   - Standalone retrieval for proposal entity, trades, and simulation.
7. **`GET /api/v1/audit/proposals/{proposal_id}`**:
   - Retrieves chronological audit trail of all actions performed on a proposal.

---

## 11. Test Gaps

The test suite must be expanded in Phase 6 to cover:
1. **Workflow State Transitions**: Valid progression (`INITIATED` $\rightarrow$ `PROPOSAL_GENERATED` $\rightarrow$ `AWAITING_APPROVAL`); rejection of invalid transitions.
2. **Proposal Invocation Idempotency**: Ensuring proposal generation is called exactly once per workflow run.
3. **Grounded Explanation Generation**: Proper extraction of trade facts and policy citations into prompt; rejection of hallucinations.
4. **LLM Offline Fallback**: Verification that if Ollama daemon is unreachable, the explanation service degrades gracefully to structured bullet-point summary without crashing or returning 500.
5. **Human Approval Workflow**:
   - Successful approval transitions proposal and trades to `APPROVED`.
   - Rejection transitions proposal and trades to `REJECTED`.
   - Attempting to approve an already approved/rejected proposal raises HTTP 409 / 422 Conflict.
   - Attempting to approve a hard-blocked proposal is rejected.
6. **Audit Event Verification**: Verification that workflow initiation, proposal generation, and human decisions generate immutable `AuditEvent` records.
7. **Financial Data Immutability**: Proving that workflow execution, explanation generation, and approval cannot alter existing `Holding` or `MarketPrice` records.

---

## 12. Recommended Phase 6 Implementation Batches

To maintain strict risk control, the implementation should be partitioned into four sequential batches, each capped under 120 minutes:

### Batch 6.1 — Core Workflow Engine & Persistence (Target: 90 min, Max: 120 min)
- Implement `WorkflowRun` and `AuditEvent` database models.
- Implement `WorkflowStatus` enum and transition validation.
- Implement `WorkflowContext` and `WorkflowExecutor`.
- Implement `WorkflowService` coordinating `RebalancingService` and `PolicyRAGService`.
- Author unit tests for workflow state, idempotency, and execution.

### Batch 6.2 — Grounded Explanation Service & Citations (Target: 90 min, Max: 120 min)
- Implement `ExplanationService` with prompt-injection-shielded templates.
- Bridge structured trade results, simulation metrics, and retrieved policy chunks.
- Implement citation validator for generated narratives.
- Implement graceful evidence-only fallback when LLM is offline or malformed.
- Author unit tests for explanation generation, citation integrity, and fallback.

### Batch 6.3 — Approval Governance, Audit Service & REST APIs (Target: 90 min, Max: 120 min)
- Implement `ApprovalService` (approve/reject transitions, trade status synchronization).
- Implement `AuditService` recording immutable audit events.
- Implement FastAPI endpoints (`/api/v1/workflows/...`, `/api/v1/proposals/{id}/approve`, etc.).
- Author integration tests for API workflows, approval permissions, and audit trails.

### Batch 6.4 — Final Safety Review & End-to-End Verification (Target: 60 min, Max: 90 min)
- Execute complete regression suite across all 6 phases.
- Perform adversarial security review (prompt injection, unauthorized approval).
- Create PostgreSQL migration `003_add_orchestration_and_audit_tables.sql`.
- Complete Phase 6 sign-off documentation.

---

## 13. Estimated Time per Batch

| Batch | Description | Target Duration | Hard Cap |
| :--- | :--- | :--- | :--- |
| **6.1** | Workflow Engine, State Machine, Models, and Context | 90 minutes | 120 minutes |
| **6.2** | Grounded Explanation Service & Citation Validation | 90 minutes | 120 minutes |
| **6.3** | Approval Governance, Audit Service, and REST APIs | 90 minutes | 120 minutes |
| **6.4** | Safety Review, Migration Script, and Full Verification | 60 minutes | 90 minutes |
| **Total** | Full Phase 6 Implementation | 330 minutes | 450 minutes |

---

## 14. Critical Risks and Blockers

1. **Local LLM Latency & Non-Determinism**:  
   *Risk*: Local Ollama inference with `llama3` on CPU or consumer GPU may take 5–15 seconds, potentially causing HTTP timeouts on synchronous workflow endpoints.  
   *Mitigation*: Set configurable HTTP client timeout (e.g. 15.0s), provide instant evidence-only fallback on timeout, and keep prompts compact.
2. **Double Decision / Race Conditions**:  
   *Risk*: Two operators concurrently attempting to approve or reject the same proposal.  
   *Mitigation*: Database-level status check within atomic transaction; second attempt encounters status check failure and raises HTTP 409 Conflict.
3. **Duplicate Proposal Creation on Retry**:  
   *Risk*: If explanation generation fails, retrying the workflow could accidentally create a second proposal.  
   *Mitigation*: Store `proposal_id` on `WorkflowRun`. When re-executing or resuming, the step checks if `proposal_id` already exists and reuses it.
4. **PostgreSQL Migration Drift**:  
   *Risk*: Migrations `001`, `002`, and `003` are not yet applied to live PostgreSQL.  
   *Mitigation*: Maintain backward compatibility, ensure all models run cleanly on SQLite for testing, and document migration scripts clearly.

---

## 15. Exact Files Likely to be Created or Modified

### Files to Create:
1. `app/models/workflow_run.py` — `WorkflowRun` entity.
2. `app/models/audit_event.py` — `AuditEvent` entity.
3. `app/schemas/orchestration.py` — Pydantic schemas for workflows, explanations, approvals, audit.
4. `app/services/orchestration/__init__.py`
5. `app/services/orchestration/workflow_state.py` — `WorkflowStatus` enum and state transitions.
6. `app/services/orchestration/workflow_context.py` — `WorkflowContext` data container.
7. `app/services/orchestration/workflow_executor.py` — Step runner.
8. `app/services/orchestration/workflow_service.py` — Facade service.
9. `app/services/explanation/__init__.py`
10. `app/services/explanation/explanation_service.py` — Explanation generator.
11. `app/services/explanation/prompt_templates.py` — Prompt templates.
12. `app/services/approval/__init__.py`
13. `app/services/approval/approval_service.py` — Human-in-the-loop governance.
14. `app/services/audit/__init__.py`
15. `app/services/audit/audit_service.py` — Immutable audit logger.
16. `app/api/v1/workflows.py` — Workflow REST router.
17. `app/api/v1/approvals.py` — Proposal approval REST router.
18. `docs/migrations/003_add_orchestration_and_audit_tables.sql` — PostgreSQL DDL.
19. `tests/test_workflow_orchestration.py` — Unit and integration tests for Phase 6.

### Files to Modify:
1. `app/models/rebalance_proposal.py` — Add optional `reviewer_id` column.
2. `app/models/__init__.py` — Export `WorkflowRun`, `AuditEvent`.
3. `app/schemas/__init__.py` — Export orchestration schemas.
4. `app/services/__init__.py` — Export `WorkflowService`, `ApprovalService`, `ExplanationService`, `AuditService`.
5. `app/api/v1/__init__.py` — Register new routers.
6. `app/main.py` — Include workflow and approval routers.

---

## 16. Audit Conclusion & Phase 6.1 Readiness

- **Full-Suite Test Result**: **387 passed, 1 skipped, 0 failed** (100% pass rate).
- **Git Working Tree Status**: Clean (branch `main` at `5109409`).
- **Files Modified During Audit**: None (Strictly read-only; report written to `prompts/phase-6/01-orchestration-architecture-audit.md`).
- **Readiness**: Phase 6.0 audit is complete. Phase 6.1 (Core Workflow Engine & Persistence) is **READY TO BEGIN**.

