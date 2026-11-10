# Prompt P1-01 — Database Configuration Tests

**AI Tool:** Antigravity  
**Phase:** 1 — Database Foundation  
**Task:** Test-first database configuration

## Context

We are developing a Policy-Constrained Portfolio Rebalancing Recommendation System.

The existing repository already contains:
- FastAPI application
- Python 3.12 environment
- SQLAlchemy 2.x dependency
- Alembic dependency
- PostgreSQL driver
- Pytest configuration

We are following Test-Driven Development.

## Objective

Create tests for database configuration and session management BEFORE implementing the database configuration.

## Expected design

The database layer should eventually support:

1. Database URL loaded from environment configuration.
2. SQLAlchemy engine creation.
3. Session factory creation.
4. Database session dependency for FastAPI.
5. Clean session lifecycle and resource handling.

Do not implement these components yet.

## Test requirements

Create focused tests covering:

### Configuration tests
- Database URL can be loaded from environment configuration.
- Missing required database configuration is handled clearly.
- No real database connection is attempted simply by importing the application.

### Engine and session factory tests
- Engine can be created using a supplied database URL.
- Session factory is configured with the expected engine.
- Sessions can be created and closed correctly.

### FastAPI dependency tests
- Database session dependency yields a session.
- Session is closed after dependency use.
- Dependency can be overridden during tests.

## Testing constraints

- Use SQLite in-memory for isolated database-layer tests where appropriate.
- Do not require a running PostgreSQL server for unit tests.
- Do not use external services.
- Avoid connecting to PostgreSQL during test collection.
- Do not mock every SQLAlchemy internal component.
- Test observable behavior.

## Strict restrictions

- Write tests only.
- Do not implement database configuration.
- Do not create SQLAlchemy entity models.
- Do not create Alembic migrations.
- Do not modify application business logic.
- Do not introduce additional dependencies without justification.
- Inspect existing project files before creating tests.
- Preserve existing tests.

## Expected output

1. List of test files created or modified.
2. Test cases and expected behavior.
3. Exact command to run tests.
4. Actual pytest results.
5. Any assumptions or design decisions.

Run the tests and report which failures are expected because implementation does not exist yet.

Stop after completing the test-first stage.