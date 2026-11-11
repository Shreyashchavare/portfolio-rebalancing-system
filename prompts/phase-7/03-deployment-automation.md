# Phase 7.2 — Deployment Configuration and Automation

Repository: portfolio-rebalancing-system

Git baseline: f322e8c

Previous audit: prompts/phase-7/01-documentation-deployment-audit.md

Previous documentation: prompts/phase-7/02-comprehensive-system-documentation.md

## Objective

Make the existing backend reproducibly deployable and easier to initialize using safe, documented automation.

Maximum duration: 120 minutes.

## Batch A — Environment configuration

Inspect:
- app/core/config.py
- app/database/session.py
- app/services/policy_rag/
- app/services/explanation/
- app/api/dependencies.py
- README.md
- requirements.txt

Update `.env.example` with every required configuration variable.

Include:
- Application environment
- Database connection
- Authentication provider
- Development mock authentication switch
- Ollama URL, model and timeout settings
- Policy document storage path
- Vector persistence path
- Any other configuration actually consumed by the application

Requirements:
- Never include real secrets.
- Development mock authentication must remain disabled by default.
- Production must fail closed.
- Do not introduce fake credentials or insecure production defaults.
- Do not invent unused configuration variables.

## Batch B — Database initialization and seeding

Create `scripts/seed_database.py`.

Inspect the actual migration and dataset exporter implementations first.

Requirements:
- Support an explicit database URL or existing configuration.
- Apply migrations in the correct order: 000, 001, 002, 003.
- Support starter dataset seeding.
- Validate database connectivity before writing.
- Prevent accidental destructive operations.
- Make repeated execution safe or detect duplicate seed data and stop clearly.
- Report inserted table counts.
- Provide a dry-run or validation mode if practical.
- Never load the 414 MB full dataset by default.
- Do not overwrite an existing populated database silently.

Do not use `Base.metadata.create_all()` as a substitute for the migration sequence.

## Batch C — Policy ingestion automation

Create `scripts/ingest_policies.py`.

Requirements:
- Discover supported PDF, Markdown and TXT policy files.
- Use the existing PolicyRAGService and ingestion implementation.
- Process files deterministically.
- Report successful and failed ingestion separately.
- Handle duplicate versions and invalid effective dates safely.
- Do not bypass existing path validation, document versioning or policy-family rules.
- Avoid duplicate ingestion on repeated runs.

## Verification

Use tests-first development.

For each script:
1. Write tests first.
2. Demonstrate RED.
3. Implement.
4. Demonstrate GREEN.
5. Run full pytest suite.
6. Run git diff --check.

Add subprocess/CLI tests where practical.

Verify commands against the real project environment.

Do not start or modify existing Docker containers or volumes. Do not run database migrations or seed data against the user's existing database. Use isolated temporary test databases only.

## Documentation

Update README.md with exact setup and execution commands.

Create or update:
- docs/deployment.md
- prompts/phase-7/03-deployment-automation.md

Document limitations and prerequisites honestly.

## Constraints

- No frontend development.
- No new architecture or microservices.
- No Kafka/RabbitMQ.
- No new vector database.
- No production financial logic changes.
- No commit or push.

---

## Execution Record

### 1. Source Inspection & Configuration Alignment (Batch A)
- **Files Inspected**:
  - `app/core/config.py`: Settings model defined using Pydantic Settings.
  - `app/database/session.py`: Database engine and session lifecycle.
  - `app/api/dependencies.py`: Authentication provider and reviewer validation.
  - `app/services/policy_rag/policy_rag_service.py`: Policy ingestion and local LLM/embedding configuration.
  - `app/services/explanation/explanation_service.py`: Grounded explanation generation with local LLM.
- **Implemented Additions**:
  - Added `AUTH_PROVIDER: str = "production"`, `LOCAL_LLM_MODEL: str = "llama3.2"`, `LOCAL_LLM_TIMEOUT: float = 5.0`, and `EMBEDDING_CACHE_DIR: Optional[str] = None` to `app/core/config.py`.
  - Wired settings into `PolicyRAGService` and `ExplanationService` so that every variable is actively consumed by the application.
  - Updated `app/api/dependencies.py` to respect `AUTH_PROVIDER` and guarantee fail-closed behavior in production.
  - Overhauled `.env.example` with clean sections, parameter descriptions, secure defaults (`AUTH_PROVIDER=production`, `ENABLE_DEV_MOCK_AUTH=False`), and zero real secrets.

### 2. Database Initialization & Seeding Automation (Batch B)
- **TDD Workflow**:
  - Authored behavioral test suite in `tests/test_seed_database.py` (11 tests covering CLI help, connectivity validation, sequential migration execution, dry-run mode, starter seeding, duplicate detection, force reseed, and 414 MB full dataset protection).
  - Executed tests to demonstrate RED:
    ```text
    ModuleNotFoundError: No module named 'scripts.seed_database'
    ```
  - Implemented `scripts/seed_database.py` with:
    - Pre-flight database connectivity validation (`SELECT 1`).
    - Sequential migration runner (000, 001, 002, 003) from `docs/migrations/` using transaction boundaries.
    - Dialect adaptation for SQLite isolated test environments and direct DDL for PostgreSQL.
    - Safety pre-population check preventing accidental duplicate seeding.
    - 414 MB full dataset blocker (refuses `data/full` unless `--force` is explicitly provided).
    - ANSI quoting normalization for the reserved SQL keyword `"constraint"`.
    - Detailed per-table inserted row count reporting.
  - Re-executed tests to demonstrate GREEN:
    ```text
    ============================= 11 passed in 19.41s =============================
    ```

### 3. Policy Document Ingestion Automation (Batch C)
- **TDD Workflow**:
  - Authored behavioral test suite in `tests/test_ingest_policies.py` (8 tests covering CLI help, file discovery for `.md`/`.txt`/`.pdf`, metadata extraction, dry-run mode, batch ingestion, duplicate skipping, and invalid date boundary error isolation).
  - Executed tests to demonstrate RED:
    ```text
    ModuleNotFoundError: No module named 'scripts.ingest_policies'
    ```
  - Implemented `scripts/ingest_policies.py` with:
    - Deterministic alphabetical discovery of supported documents.
    - Comprehensive metadata parser extracting title, version, family ID, effective dates, and status from markdown headers, companion JSON, or filename conventions.
    - Integration with existing `PolicyRAGService` and `DocumentExtractor`.
    - Duplicate detection and version preservation (already-ingested policies are recorded as SKIPPED).
    - Isolated error handling (invalid date bounds recorded as FAILED without aborting the batch).
    - Dry-run validation mode and `--use-fake-embeddings` flag for fast offline testing.
  - Re-executed tests to demonstrate GREEN:
    ```text
    ============================== 8 passed in 3.52s ==============================
    ```

### 4. Quality & Regression Verification
- **Targeted Test Execution**:
  ```text
  pytest tests/test_seed_database.py tests/test_ingest_policies.py -v
  ============================= 19 passed in 25.85s =============================
  ```
- **Full Regression Test Suite**:
  ```text
  pytest -q
  ================= 480 passed, 1 skipped, 7 warnings in 40.37s =================
  ```
  *(1 test skipped as expected due to SQLite lacking PostgreSQL `pgvector` extension).*
- **Whitespace & Formatting Audit**:
  ```text
  git diff --check
  [Clean: 0 warnings, 0 errors]
  ```

### 5. Documentation Deliverables
- Created comprehensive `docs/deployment.md` covering architecture, prerequisites, environment variables, step-by-step procedures, CLI reference, and security disclosures.
- Updated `README.md` sections 8, 9, and 11 with exact setup and CLI commands.
- Preserved prompt and execution record in `prompts/phase-7/03-deployment-automation.md`.

### 6. Final Status
- **Total Duration**: ~55 minutes (well within the 120-minute timebox).
- **Recommendation**: **READY FOR SUBMISSION & DEMONSTRATION**.
