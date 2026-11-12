# Phase 7 — System Documentation and Reviewer Readiness

## Objective
Make the implemented system understandable, runnable and assessable by a reviewer.

## Documentation set
- Root `README.md`: concise project overview, prerequisites, environment setup, run instructions, tests and troubleshooting.
- `docs/architecture.md`: service/module boundaries, request flow, persistence and integrations.
- `docs/api-reference.md`: registered endpoints, request/response behavior and error semantics.
- `docs/data-dictionary.md`: domain tables, relationships, important fields and constraints.
- Deployment and reviewer/demo instructions.

## Accuracy rules
- Derive documentation from the actual repository, configuration, routes and tests.
- Do not document planned features as implemented.
- Distinguish local development configuration from production deployment.
- Document database initialization, migrations, seeding and policy ingestion.
- Explain authentication modes and their limitations.
- Include a reproducible reviewer walkthrough and known limitations.

## Demo narrative
Show portfolio overview and valuation, allocation drift, proposal generation, a constraint exception, human approval/rejection, audit traceability and policy-grounded explanation.
