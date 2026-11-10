# Prompt P1-02 — Implement Database Configuration

**AI Tool:** Antigravity  
**Phase:** 1 — Database Foundation  
**Task:** Implement database configuration based on existing tests

## Context

The project uses:
- Python 3.12
- FastAPI
- SQLAlchemy 2.x
- PostgreSQL
- Pydantic Settings
- Pytest

The database configuration test-first stage has been completed.

Current test results:
- 8 database tests fail because implementation modules do not exist.
- 1 database import-isolation test passes.
- 1 existing health test passes.

## Objective

Implement the database configuration and session management required by the existing tests.

## Required module structure

```text
app/
├── core/
│   └── config.py
└── database/
    ├── __init__.py
    └── session.py
```

## Implementation requirements

### 1. Configuration

Implement `app/core/config.py`.

- Use Pydantic Settings.
- Read `DATABASE_URL` from environment configuration.
- Treat the database URL as required when database settings are instantiated.
- Raise a clear validation error if missing.
- Do not instantiate settings or connect to the database merely by importing `app.main`.

### 2. Database engine

Implement `app/database/session.py`.

- Provide a function to create an SQLAlchemy engine using a supplied database URL.
- Use SQLAlchemy 2.x.
- Keep engine creation separate from database connection execution.
- Do not connect to PostgreSQL at module import time.

### 3. Session factory

- Provide a session factory configured with the supplied engine.
- Use SQLAlchemy Session.
- Disable autoflush and autocommit.
- Do not create a global connection to PostgreSQL.

### 4. FastAPI database dependency

Implement `get_db`.

- Yield a database session.
- Close the session in a `finally` block.
- Allow FastAPI dependency overrides during tests.

### 5. Tests

Use the existing test suite as the acceptance contract.

Do not weaken, delete, skip, or rewrite tests merely to make them pass.

If a test contains an incorrect assumption or implementation-specific import, explain the issue before modifying it.

## Restrictions

- Do not create ORM entity models.
- Do not create Alembic migrations.
- Do not implement business logic.
- Do not introduce new infrastructure.
- Do not make real PostgreSQL connections during unit tests.
- Do not modify Git history.
- Do not commit or push automatically.

## Completion requirements

Run:

`pytest -v`

Report:
1. Files created or modified.
2. Implementation decisions.
3. Test results.
4. Any remaining failures or warnings.
5. Confirmation that importing the FastAPI application does not require PostgreSQL.

Stop after completing database configuration and session management.