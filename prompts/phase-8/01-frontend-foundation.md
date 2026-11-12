# Phase 8.1 — Frontend Architecture, Foundation & Application Shell

## Role

Act as a senior frontend architect and full-stack engineer working on the existing **YottaFlex Portfolio Rebalancing System**.

Your responsibility is to establish a production-quality frontend foundation that integrates with the existing FastAPI backend.

This is an existing financial application, not a new greenfield project. Preserve all completed backend functionality, existing database records, API contracts, security controls, tests, and Git history.

---

## 1. Project context

Project: YottaFlex — Portfolio Rebalancing System.

Existing backend:
- Python 3.12
- FastAPI
- SQLAlchemy 2.x
- PostgreSQL 17
- Alembic
- Pydantic
- pytest

Existing backend capabilities:
1. Portfolio management and valuation
2. Portfolio analytics and drift analysis
3. Rebalancing proposal generation
4. Trade generation and simulation
5. Constraint evaluation and financial safety
6. Approval and rejection workflows
7. Audit event retrieval
8. Policy document ingestion and retrieval
9. Policy RAG question answering
10. Workflow orchestration
11. Authentication and role-based access control

Existing API routers:
- `app/api/v1/analytics.py`
- `app/api/v1/approvals.py`
- `app/api/v1/policies.py`
- `app/api/v1/rebalancing.py`
- `app/api/v1/workflows.py`

Existing documentation:
- `docs/architecture.md`
- `docs/api-reference.md`
- `docs/data-dictionary.md`
- `docs/demo-guide.md`
- `docs/deployment.md`
- `docs/submission-readiness.md`

Frontend directory:
- `frontend/`
- Currently contains only `.gitkeep`.
- No existing React application has been confirmed.

Prompt history:
- `prompts/phase-0/` through `prompts/phase-7/`
- Phase 8 prompts must be maintained in `prompts/phase-8/`.

---

## 2. Primary objective

Create the initial frontend foundation for YottaFlex.

The frontend must provide a professional, responsive financial application shell that can subsequently support portfolio analytics, rebalancing, governance, policy intelligence, and workflow monitoring.

Do not implement all business modules in this phase.

This phase establishes the architecture, reusable foundations, navigation, application shell, API integration infrastructure, and development tooling.

---

## 3. Mandatory initial repository audit

Before changing any files:

1. Inspect Git status and current branch.
2. Inspect the complete `frontend/` directory.
3. Read `README.md`.
4. Read `docs/architecture.md`.
5. Read `docs/api-reference.md`.
6. Read `docs/deployment.md`.
7. Read `docs/demo-guide.md`.
8. Inspect existing API routers, Pydantic schemas, authentication dependencies, and relevant service contracts.
9. Inspect `prompts/README.md` and recent Phase 7 prompts to understand project conventions.
10. Identify the backend's actual API prefix, response formats, authentication behavior, and CORS configuration.

Do not assume endpoint paths, response structures, authentication mechanisms, or field names.

Create a concise architecture and integration assessment before implementation.

If existing documentation and implementation disagree, identify the discrepancy and treat the actual backend implementation as authoritative. Do not silently change backend behavior.

### Git safety

- Preserve the current branch and existing commits.
- Do not reset, rebase, force-push, or rewrite Git history.
- Do not discard existing changes.
- Do not modify backend files unless a genuine frontend integration blocker is identified and explicitly justified.
- Do not commit changes unless explicitly requested.

---

## 4. Frontend technology selection

Use the following target stack unless the repository audit identifies an existing documented decision that should be preserved:

- React
- TypeScript
- Vite
- React Router
- Tailwind CSS
- Lucide React icons
- Recharts for future financial charts
- TanStack Query for server-state management
- Axios or a well-structured Fetch API client
- React Hook Form and Zod when forms are introduced

Use stable, mutually compatible package versions.

Avoid unnecessary dependencies and premature abstraction.

Use npm unless the repository already establishes another package manager.

---

## 5. Application architecture

Create a clean, scalable structure inside `frontend/`.

Suggested structure:

```text
frontend/
├── public/
├── src/
│   ├── app/
│   │   ├── router/
│   │   ├── providers/
│   │   └── layouts/
│   ├── assets/
│   ├── components/
│   │   ├── ui/
│   │   ├── layout/
│   │   └── feedback/
│   ├── features/
│   │   ├── dashboard/
│   │   ├── portfolios/
│   │   ├── rebalancing/
│   │   ├── approvals/
│   │   ├── policies/
│   │   └── workflows/
│   ├── hooks/
│   ├── lib/
│   ├── services/
│   │   ├── api/
│   │   └── types/
│   ├── styles/
│   ├── types/
│   ├── utils/
│   ├── App.tsx
│   └── main.tsx
├── .env.example
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

This is a proposed structure, not a requirement to create empty files for every future feature.

Create only the folders and files needed for this phase.

Keep feature-specific code inside its respective feature directory.

---

## 6. UI/UX design direction

Build a professional financial operations dashboard.

Design characteristics:

- Enterprise financial software appearance.
- Clean, modern, restrained visual design.
- Consistent typography and spacing.
- Neutral background with clear visual hierarchy.
- Dark navy or similarly professional navigation.
- Accessible contrast.
- Carefully designed cards, tables, badges, dialogs, and navigation.
- Responsive layout for desktop, tablet, and mobile.
- Consistent loading, empty, success, and error states.

Create:

### A. Application shell

- Sidebar navigation.
- Header/top navigation.
- Main content area.
- Breadcrumb or page-title region.
- Responsive mobile navigation.
- User/profile area.
- Application branding for YottaFlex.

### B. Navigation

Prepare routes for the future modules:

| Route | Purpose |
|---|---|
| `/dashboard` | Financial overview |
| `/portfolios` | Portfolio management |
| `/rebalancing` | Rebalancing workspace |
| `/approvals` | Human review and approvals |
| `/policies` | Policy management and RAG |
| `/workflows` | Workflow monitoring |
| `/settings` | Application settings |

Do not create fake functional modules.

For routes not implemented in this phase, provide a clearly identified placeholder page rather than fabricated business data.

### C. Initial dashboard shell

Create a dashboard landing page with:
- Welcome/title area.
- Overview section.
- Clearly labeled placeholder KPI cards.
- Recent activity placeholder.
- Portfolio overview placeholder.

Do not invent actual financial figures or display hardcoded values as real portfolio data.

---

## 7. API integration foundation

Build a centralized API client.

Requirements:

1. Configure the API base URL using a Vite environment variable.
2. Provide a typed API client.
3. Centralize request and response error handling.
4. Support request cancellation where appropriate.
5. Handle HTTP 401 and 403 without silently bypassing authentication.
6. Avoid exposing secrets in frontend source code.
7. Do not hardcode development tokens in production code.
8. Keep authentication integration compatible with the actual backend contract.
9. Provide a development-only configuration approach if the backend currently uses mock authentication.
10. Never weaken backend authentication or authorization to accommodate frontend development.

Create `.env.example` with documented frontend environment variables.

Never overwrite or expose the repository's existing `.env`.

Do not assume that the backend supports a login endpoint. Inspect the implementation first.

If authentication integration requires a future identity-provider decision, document the limitation instead of inventing an authentication flow.

---

## 8. TypeScript and code quality

- Enable strict TypeScript.
- Avoid `any` unless explicitly justified.
- Create reusable typed components.
- Keep API DTOs separate from UI view models.
- Use consistent naming conventions.
- Avoid oversized components.
- Keep business logic out of presentation components.
- Avoid unnecessary global state.
- Keep environment-specific configuration centralized.
- Ensure accessible semantic HTML.

---

## 9. Testing requirements

Set up appropriate frontend tooling.

At minimum:

- TypeScript type checking.
- ESLint.
- Frontend build verification.
- Component or application-shell tests using an appropriate testing library.
- Router rendering test.
- API client error-handling tests.

Test:
1. Application mounts successfully.
2. Navigation routes render correctly.
3. Unknown routes show a not-found page.
4. Responsive navigation behaves correctly.
5. API client uses the configured base URL.
6. API client handles unauthorized and forbidden responses.
7. No fake portfolio data is presented as real data.

Do not claim tests passed unless they were actually executed.

---

## 10. Documentation and prompt-history requirements

Maintain the existing prompt convention.

Create:

`prompts/phase-8/01-frontend-foundation.md`

This file must contain the complete master prompt used for this phase.

Update `prompts/README.md` only if necessary to include Phase 8.

Create or update `frontend/README.md` documenting:

- Frontend technology stack.
- Installation.
- Development server.
- Build and test commands.
- Environment variables.
- Backend connection configuration.
- Current implementation scope.
- Known limitations.

Do not create a second root README.

Do not modify existing Phase 0–7 prompt files.

---

## 11. Out-of-scope items

Do not implement these in Phase 8.1:

- Full portfolio management functionality.
- Actual financial KPI calculations in the frontend.
- Rebalancing proposal generation UI.
- Trade approval or rejection actions.
- Policy ingestion or document upload.
- Policy RAG chat.
- Workflow execution UI.
- Production identity-provider implementation.
- Backend schema or database migrations.
- Changes to seeded database data.

These will be implemented in subsequent Phase 8 subphases.

---

## 12. Execution approach

Follow this order:

1. Repository audit.
2. Frontend architecture decision.
3. Dependency and tooling setup.
4. Application entry point and routing.
5. Reusable design foundations.
6. Responsive application shell.
7. Dashboard placeholder.
8. Centralized API client.
9. Tests and quality checks.
10. Documentation and prompt-history updates.
11. Final implementation review.

Work incrementally.

Do not generate the entire application in one massive component or one unreviewable change.

If a major architectural decision is unclear, document the options and recommend one before proceeding.

---

## 13. Acceptance criteria

Phase 8.1 is complete only when:

- [ ] Frontend application exists under `frontend/`.
- [ ] React and TypeScript are configured.
- [ ] Development server starts successfully.
- [ ] Production build succeeds.
- [ ] Routing works.
- [ ] Responsive application shell is implemented.
- [ ] Dashboard placeholder is implemented without fabricated financial data.
- [ ] Centralized API client exists.
- [ ] Environment configuration is documented.
- [ ] Type checking succeeds.
- [ ] Linting succeeds.
- [ ] Frontend tests pass.
- [ ] Backend behavior remains unchanged.
- [ ] Existing backend tests remain passing.
- [ ] Prompt history is maintained.
- [ ] Git diff is reviewed.
- [ ] No secrets or real credentials are committed.

---

## 14. Final report

At completion, report:

1. Files created.
2. Files modified.
3. Final frontend architecture.
4. Dependencies installed and versions.
5. Routes implemented.
6. API integration capabilities.
7. Tests executed and exact results.
8. Production build result.
9. Backend changes, if any, with justification.
10. Known limitations.
11. Git status.
12. Recommended next subphase.

Do not mark Phase 8.1 complete if acceptance criteria remain unmet.

**Final instruction:** Build a maintainable foundation for a real financial application. Prioritize correctness, security, usability, and integration with the existing YottaFlex backend over visual decoration or unnecessary complexity.