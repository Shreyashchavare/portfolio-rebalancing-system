# Deployment and Automation Guide

## 1. Overview and Architecture Topology

The **Portfolio Rebalancing Recommendation System** is deployed as a modular FastAPI backend integrated with a standard PostgreSQL 16 database (without requiring the `pgvector` extension) and a local Ollama daemon for grounded explanations and compliance policy retrieval.

```
+----------------------------------------------------------------------------------+
|                                Production Host                                   |
|                                                                                  |
|  +--------------------+        +---------------------+                           |
|  |   Reverse Proxy    |------->|   FastAPI Backend   |                           |
|  |  (Nginx / Caddy)   |        |  (Uvicorn Workers)  |                           |
|  +--------------------+        +----------+----------+                           |
|                                           |                                      |
|                                           | SQLAlchemy 2.x                       |
|                                           v                                      |
|  +---------------------+       +----------+----------+       +----------------+  |
|  |   Ollama Daemon     |<------|  Policy RAG Engine  |------>| PostgreSQL 16  |  |
|  |  (llama3.2 text)   | HTTP  | (FastEmbed ONNX +   | SQL   |  (Relational)  |  |
|  |                     |       |  NumPy Similarity)  |       |                |  |
|  +---------------------+       +---------------------+       +----------------+  |
+----------------------------------------------------------------------------------+
```

---

## 2. Prerequisites

| Component | Minimum Version | Required Notes |
| :--- | :--- | :--- |
| **Python** | 3.12.0+ | Required for type hint syntax and package wheels. |
| **PostgreSQL** | 16.0+ | Standard relational database (no `pgvector` or external extensions required). |
| **Ollama** | 0.3.0+ | Local daemon running `llama3.2` for narrative explanation generation. |
| **Git** | 2.40+ | For repository deployment and version tracking. |

---

## 3. Environment Configuration

All operational configuration is managed via environment variables or a `.env` file at the repository root. Create `.env` from the provided template:

```bash
cp .env.example .env
```

### Configuration Variables Reference

| Variable Name | Type | Default | Production Requirement / Description |
| :--- | :--- | :--- | :--- |
| `APP_NAME` | string | `portfolio-rebalancing-system` | Application identifier in logs and OpenAPI metadata. |
| `APP_ENV` | string | `development` | Deployment tier: `development`, `staging`, or `production`. When set to `production`, mock authentication is hard-blocked. |
| `DEBUG` | boolean | `False` in prod | Set to `False` in production to prevent traceback leaks. |
| `HOST` | string | `0.0.0.0` | Bind host address for Uvicorn server. |
| `PORT` | integer | `8000` | Port for FastAPI application. |
| `DATABASE_URL` | string | *(Required)* | SQLAlchemy connection URI. Example: `postgresql+psycopg2://app_user:secret@localhost:5432/portfolio_rebalancing`. |
| `AUTH_PROVIDER` | string | `production` | Security provider. Set to `production` to enforce fail-closed verification until a trusted IdP is wired. |
| `ENABLE_DEV_MOCK_AUTH` | boolean | `False` | **Must be False in production.** When `True` in `development`, allows static tokens (`dev-reviewer-token`, `dev-admin-token`). Fails closed in production. |
| `POLICY_DOCUMENTS_DIR` | path | `policy_documents` | Directory containing compliance and mandate policy documents. |
| `EMBEDDING_MODEL_NAME` | string | `BAAI/bge-small-en-v1.5` | FastEmbed ONNX embedding model identifier. |
| `EMBEDDING_CACHE_DIR` | path | `None` (user cache) | Optional path to cache ONNX models and vector tokenizer files. |
| `RAG_CHUNK_SIZE` | integer | `500` | Target character size per policy document chunk. |
| `RAG_CHUNK_OVERLAP` | integer | `50` | Character overlap between consecutive chunks. |
| `RAG_TOP_K` | integer | `5` | Maximum policy chunks retrieved per query. |
| `RAG_SIMILARITY_THRESHOLD` | float | `0.5` | Minimum cosine similarity threshold for evidence inclusion. |
| `LOCAL_LLM_URL` | url | `http://localhost:11434` | Ollama daemon endpoint. |
| `LOCAL_LLM_MODEL` | string | `llama3.2` | Target local LLM model for grounded explanations. |
| `LOCAL_LLM_TIMEOUT` | float | `5.0` | Request timeout in seconds before falling back to deterministic explanation. |

---

## 4. Automated Database Initialization and Seeding

Database initialization and data loading are automated via [`scripts/seed_database.py`](../scripts/seed_database.py).

### Migration Sequence
The script applies SQL DDL migrations in strict chronological order from `docs/migrations/`:
1. `000_create_core_tables.sql`: 11 core tables (`investor_profile`, `portfolio`, `instrument`, `holding`, `market_price`, `target_allocation`, `fee_schedule`, `constraint`, `constraint_instrument`, `rebalance_proposal`, `trade`).
2. `001_create_policy_rag_tables.sql`: Policy RAG storage (`policy_documents`, `policy_chunks`).
3. `002_add_policy_family_id.sql`: Schema migration adding `policy_family_id` column and index.
4. `003_add_orchestration_and_audit_tables.sql`: Governance tables (`workflow_runs`, `audit_events`).

### Migration History and Transactional Safety
- **Tracking Table**: Automatically initializes `migration_history` (`filename VARCHAR(255) PRIMARY KEY`, `applied_at TIMESTAMP WITH TIME ZONE`).
- **Selective Execution**: Only unapplied migrations are executed. On repeat runs, already-recorded migrations are skipped safely.
- **Transactional Atomicity**: Each migration and its history record are executed within an atomic transaction. If any DDL statement fails, the transaction rolls back completely and the migration is never recorded in `migration_history`.

### Safety Safeguards
- **Database Pre-population Guard**: Detects existing records in core tables. Halts cleanly to prevent duplicate inserts or primary key collisions unless `--force` is provided.
- **Explicit `--force` Limitations**: Passing `--force` bypasses the populated-database safeguard **only**. It does **not** delete, overwrite, or imply safe replacement of existing data. Database primary key and unique constraints will reject conflicting inserts and trigger atomic rollback.
- **Full Dataset Protection**: Blocks accidental loading of the 414 MB `data/full` dataset by default. Seeding is strictly scoped to `data/starter`.
- **Pre-flight Connectivity Check**: Pings database with `SELECT 1` before executing DDL.
- **Dry-run Validation**: `--dry-run` verifies database reachability, migration scripts, and seed files without executing any state changes.

### CLI Usage Examples

```bash
# 1. Dry-run inspection (no changes made)
python scripts/seed_database.py --dry-run

# 2. Standard initialization and starter seeding
python scripts/seed_database.py

# 3. Apply migrations only without seeding records
python scripts/seed_database.py --skip-seed

# 4. Seed records only against pre-migrated schema
python scripts/seed_database.py --skip-migrations

# 5. Explicit database URL override
python scripts/seed_database.py --database-url "postgresql+psycopg2://postgres:secret@db.prod.internal:5432/rebalance_prod"
```

---

## 5. Automated Policy Document Ingestion

Compliance and mandate policy documents are ingested and vectorized using [`scripts/ingest_policies.py`](../scripts/ingest_policies.py).

### Ingestion Features
- **File Discovery**: Discovers `.pdf`, `.md`, and `.txt` files in deterministic order across policy directories and subdirectories.
- **Path Traversal Security**: Strict `allowed_root` boundary is enforced on all discovered files and extraction targets. Any symlinks or directory junctions resolving outside the policy directory are rejected with `PathTraversalError` in both normal and dry-run modes.
- **Metadata Protection**: Discovered files' actual resolved paths cannot be overridden by companion JSON (`<file>.meta.json`) `file_path` attributes.
- **Deterministic Family Identity**: Preserves stable policy family IDs across document revisions.
- **Idempotency & Duplicate Skipping**: Safely detects already-ingested versions and skips them without errors.
- **Failure Isolation**: If a document has invalid bounds (e.g., `effective_from > effective_to`), the script logs the failure and continues processing the rest of the batch.

### CLI Usage Examples

```bash
# 1. Dry-run parsing and metadata validation
python scripts/ingest_policies.py --dry-run

# 2. Ingest policies from default directory (policy_documents/)
python scripts/ingest_policies.py

# 3. Ingest policies with custom directory and database target
python scripts/ingest_policies.py --policies-dir /etc/compliance/policies --database-url "postgresql+psycopg2://postgres:secret@db.prod.internal:5432/rebalance_prod"

# 4. Offline testing with deterministic fake embeddings (no ONNX download)
python scripts/ingest_policies.py --use-fake-embeddings
```

---

## 6. Local LLM Setup (Ollama)

Ensure the Ollama daemon is running and the required model is pulled:

```bash
# 1. Pull the generation model for narrative explanations
ollama pull llama3.2

# 2. Verify daemon connectivity
curl http://localhost:11434/api/tags
```

> [!NOTE]
> Vector embeddings are generated locally in Python via FastEmbed ONNX (`BAAI/bge-small-en-v1.5`) and do not require Ollama embedding models or external embedding APIs.

---

## 7. Starting the Application

Run the application using Uvicorn:

```bash
# Development with hot-reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production with multi-worker process manager
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers
```

### Health Probe
Verify that the service is operational:
```bash
curl http://localhost:8000/health
# Response: {"status": "healthy"}
```

---

## 8. Security Disclosures and Limitations

1. **Authentication Boundary**: In production (`APP_ENV=production`), `AUTH_PROVIDER` fails closed. Until an enterprise OAuth2/OIDC provider is integrated, all mutation endpoints requiring Bearer tokens (`/workflows`, `/proposals/{id}/approve`, `/proposals/{id}/reject`) reject incoming tokens with HTTP 401. Development mock authentication (`ENABLE_DEV_MOCK_AUTH`) is permanently blocked in production environments.
2. **Financial Execution Boundary**: Proposal approval transitions proposal state and writes immutable audit logs. It does **not** execute live market broker orders or mutate raw portfolio holdings.
3. **Deterministic Financial Safety**: All calculations (valuation, drift, trade generation, constraints, simulation, fee schedules) execute in Python outside the LLM. The LLM has zero authority to alter trade parameters.
4. **Relational Vector Architecture**: Embeddings are stored in standard relational schema (`policy_chunks.embedding_json`) and searched via deterministic in-memory NumPy cosine similarity after metadata pre-filtering. This enables identical vector operations across both PostgreSQL production and SQLite test environments without requiring external C extensions or cloud vector databases.
