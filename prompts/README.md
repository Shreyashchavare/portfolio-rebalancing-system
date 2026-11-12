# Portfolio Rebalancing System — Compact AI Prompt History

This folder contains the **condensed prompt and development history** for the Portfolio Rebalancing Recommendation System. The original archive contained many small, overlapping prompt files and long execution transcripts. Those have been consolidated into **2–3 focused Markdown files per phase**, plus this index.

The files preserve the original phase sequence, major objectives, requirements, design decisions, scope boundaries and verification approach. Repeated instructions, routine progress logs and duplicated terminal output have been removed.

> These are historical summaries of the supplied prompt archive, not a replacement for the source code, test suite or final technical audit. Historical test results are not represented as current results unless explicitly stated as source-reported.

## Phase index

| Phase | Name | Purpose / Information covered | Files |
|---|---|---|---:|
| 0 | Project Scaffolding | Repository setup, development workflow, AI-tool usage, quality principles and developer responsibility. | 2 |
| 1 | Database Foundation | SQLAlchemy configuration, core domain entities, financial/policy entities, relationships, constraints and TDD conventions. | 3 |
| 2 | Synthetic Data Foundation | Data dictionary, deterministic generators, valid baseline, labelled anomalies, exports, scaling and reproducibility. | 2 |
| 3 | Portfolio Analytics | Portfolio valuation, price freshness, target allocation, drift, runtime validation and configured rebalance triggers. | 2 |
| 4 | Rebalancing Engine | Deterministic BUY/SELL generation, fees, lot sizes, cash controls, simulation, constraints, proposal persistence and API. | 2 |
| 5 | Policy RAG | Policy ingestion, chunking, embeddings, vector retrieval, grounded answers, citations, temporal validity and policy-family identity. | 3 |
| 6 | Workflow Orchestration | Persisted workflow engine, state management, grounded explanations, approval governance, audit APIs, security and integration. | 3 |
| 7 | Documentation & Deployment | System documentation, deployment automation, database/seeder safety, authentication, test hygiene and reviewer submission. | 3 |
| 8 | Frontend | React/Vite foundation, themes/design system, analytics integration, business-facing UX and RBAC-aware workflows. | 2 |

**Total:** 22 phase documents across 9 phases, plus this README.

## Folder structure

```text
prompt-history/
├── README.md
├── phase-0/
│   ├── 01-project-scaffolding-and-phase-control.md
│   └── 02-development-workflow-and-responsibility.md
├── phase-1/
│   ├── 01-database-and-core-domain-models.md
│   ├── 02-financial-policy-and-rebalancing-models.md
│   └── 03-schema-integrity-and-tdd-record.md
├── phase-2/
│   ├── 01-data-dictionary-and-generator-foundation.md
│   └── 02-anomalies-export-and-reproducibility.md
├── phase-3/
│   ├── 01-portfolio-analytics-service.md
│   └── 02-rebalance-trigger-and-verification.md
├── phase-4/
│   ├── 01-deterministic-trade-generation.md
│   └── 02-simulation-constraints-and-persistence.md
├── phase-5/
│   ├── 01-policy-ingestion-and-vector-storage.md
│   ├── 02-policy-retrieval-grounding-and-api.md
│   └── 03-policy-family-identity-and-safety.md
├── phase-6/
│   ├── 01-workflow-engine-and-state-management.md
│   ├── 02-grounded-explanations-and-citations.md
│   └── 03-approval-governance-and-integration.md
├── phase-7/
│   ├── 01-system-documentation-and-reviewer-guides.md
│   ├── 02-deployment-automation-and-security.md
│   └── 03-test-hygiene-integrity-and-submission.md
└── phase-8/
    ├── 01-frontend-foundation-and-design-system.md
    └── 02-analytics-integration-and-business-roles.md
```

## Phase-by-phase source consolidation

| Phase | Original files consolidated |
|---|---|
| 0 | Project scaffolding; phase completion record |
| 1 | Database configuration tests/implementation; InvestorProfile; Portfolio; Instrument; Holding; MarketPrice; TargetAllocation; FeeSchedule; Constraint/ConstraintInstrument; Trade/RebalanceProposal |
| 2 | Data foundation; master/reference generators; complete synthetic dataset; deterministic export; full-scale optimization; anomaly-count reconciliation; PostgreSQL identifier quoting; null-validation fallback |
| 3 | Analytics audit; core analytics service; stale-price classification; analytics API; financial logic review |
| 4 | Rebalancing audit; deterministic trade generation; financial safety review; post-trade simulation/constraint gatekeeper/proposal API; persistence review |
| 5 | Policy RAG audit; ingestion/embeddings; vector safety; retrieval/orchestration API; temporal/grounding review; policy-family identity and edge cases |
| 6 | Orchestration architecture audit; workflow engine; grounded explanations; approval governance/audit APIs; security remediation; integration stabilization; portfolio initialization fix |
| 7 | Documentation/deployment audit; system documentation; deployment automation; seeder/auth safety; test hygiene; deployment safety; integrity fixes; final cleanup; reviewer demo |
| 8 | Frontend foundation; dual-theme design system; analytics API integration; user-facing abstraction; RBAC business frontend |

## Development tools recorded in the source archive

| Tool | Recorded purpose |
|---|---|
| ChatGPT | Technical guidance, architecture decisions, planning, testing strategy and code review |
| Antigravity | Implementation assistance, code generation and debugging |
| Claude | Documentation assistance |

## Project-wide engineering principles

1. Inspect the existing repository and contracts before editing.
2. Use tests-first development for scoped implementation work.
3. Preserve existing behavior and do not weaken tests to obtain a pass.
4. Use Decimal arithmetic for financial values.
5. Keep deterministic business rules separate from LLM-generated explanations.
6. Preserve referential integrity, auditability and historical records.
7. Treat policy documents and retrieved content as untrusted input.
8. Keep credentials and local environment files out of version control.
9. Verify the complete application and document actual limitations.
10. The developer remains responsible for reviewing and understanding AI-assisted changes.

## How to use this history

- Read this README first to understand the project sequence.
- Open the relevant phase folder for its consolidated objective, requirements and decisions.
- Use the repository source, tests and current audit for implementation truth.
- Do not treat a historical execution result as proof that the current checkout still passes.
- Keep future additions concise: update the relevant phase file instead of creating a new file for every small prompt or correction. Add a new file only when a phase has a genuinely separate workstream, and keep each phase to 2–4 files.
