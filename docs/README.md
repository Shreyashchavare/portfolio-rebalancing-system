# YottaFlex Portfolio Rebalancing System

A policy-constrained portfolio rebalancing application. It analyzes portfolios, detects allocation drift, creates simulated trade recommendations, checks financial and compliance constraints, and routes proposals for human review. **It does not execute live trades.**

## Requirements
- Python 3.12+
- Node.js 20+
- PostgreSQL (SQLite is supported for the local demo)
- Ollama with `llama3.2` (optional; an offline explanation fallback is available)

## Run locally

### Backend
Run from the repository root in PowerShell:

```powershell
# Activate the existing environment
.\.venv\Scripts\Activate.ps1

# If .venv does not exist, create it and install dependencies
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Configure `.env` from `.env.example`. For a disposable SQLite demo:

```env
DATABASE_URL=sqlite:///demo_rebalancing.db
APP_ENV=development
ENABLE_DEV_MOCK_AUTH=true
USE_FAKE_EMBEDDINGS=true
LOCAL_LLM_URL=http://localhost:11434
LOCAL_LLM_MODEL=llama3.2
```

Initialize demo data and policy documents:

```powershell
python scripts/seed_database.py --database-url sqlite:///demo_rebalancing.db --dataset-dir data/starter
python scripts/ingest_policies.py --database-url sqlite:///demo_rebalancing.db --use-fake-embeddings
```

Start the API:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

API docs: <http://127.0.0.1:8000/docs>

### Frontend
Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

### Optional local LLM

```powershell
ollama pull llama3.2
ollama run llama3.2
```

## Demo and safety

Run the non-destructive demo walkthrough from the repository root:

```powershell
python scripts/demo_walkthrough.py --database-url sqlite:///demo_rebalancing.db
```

Use synthetic or dedicated test data only. Development mock authentication is for local testing and must never be enabled in production. Production authentication is fail-closed. The system is advisory/simulation-only and does not connect to a live broker.
