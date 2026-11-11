# portfolio-rebalancing-system

Policy-Constrained Portfolio Rebalancing Recommendation System

## Project Overview

A Policy-Constrained Portfolio Rebalancing Recommendation System designed to provide deterministic rebalancing recommendations governed by investment policy constraints, portfolio analytics, fee validation, and post-trade simulation with mandatory human approval.

## Prerequisites

- Python 3.12 (compatible with Python 3.10+)
- PostgreSQL (for persistence in future phases)

## Virtual Environment Setup

### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Linux / macOS (bash/zsh)
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Dependency Installation

Upgrade pip and install the base dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Environment variables template is available in `.env.example`:

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

## Application Startup

Run the FastAPI application with Uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify that the health check endpoint responds:
- URL: `http://localhost:8000/health`
- Expected Response: `{"status": "healthy"}`

## Test Execution

Run the test suite using pytest:

```bash
pytest
```

## Policy RAG Foundation (Phase 5.1)

The system includes a local, deterministic Policy RAG ingestion and vector storage foundation:
- **Document Extraction**: Pure-Python extraction from PDF (`pypdf`), Markdown, and plain text with security boundaries (path traversal guards, file size limits, corrupt document detection).
- **Heading-Aware Text Chunking**: Semantic boundary chunking preserving document hierarchy and section headings with configurable chunk size and overlap.
- **Local ONNX Embeddings**: Zero-cloud local embedding inference using `fastembed` with quantized ONNX models (default: `BAAI/bge-small-en-v1.5`, 384 dimensions, $L_2$ normalized). Unit tests leverage a deterministic `FakeEmbeddingService` for 100% offline, zero-network test execution.
- **Relational Vector Store**: Embeddings are persisted in the relational database (`PolicyChunk.embedding_json`) with vectorized NumPy cosine similarity search and temporal compliance pre-filtering (`effective_from <= as_of_date <= effective_to`, `status == 'ACTIVE'`).

### Offline Model Preparation

To pre-warm and cache the local ONNX embedding model for completely offline air-gapped environments:

```bash
python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5')"
```
