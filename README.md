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
