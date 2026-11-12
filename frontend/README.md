# YottaFlex — Frontend Application

Modern React 18 and TypeScript application shell for the **YottaFlex Portfolio Rebalancing System**.

---

## 1. Technology Stack

- **Framework:** React 18.3.1 (with TypeScript 5.7.2 in strict mode)
- **Build Tool & Dev Server:** Vite 6.0.3 (fast ESM bundler with built-in API proxying)
- **Routing:** React Router 6.28.0 (client-side routing with layout and child route guards)
- **Styling:** Tailwind CSS 3.4.16 + PostCSS + Autoprefixer
- **UI Components & Icons:** Custom accessible financial primitives & Lucide React 0.468
- **Server State Management:** TanStack Query 5.60.6 (`@tanstack/react-query`)
- **HTTP Client:** Axios 1.7.9 (typed client with request/response interceptors, error normalization, and cancellation support)
- **Form & Validation Primitives:** React Hook Form 7.54 + Zod 3.24
- **Testing:** Vitest 2.1.8 + `@testing-library/react` 16.1 + `@testing-library/jest-dom` 6.6 (JSDOM environment)
- **Code Quality:** ESLint 9.16 + TypeScript ESLint 8.18 + react-hooks plugin

---

## 2. Directory Architecture

```text
frontend/
├── public/
│   └── favicon.svg                  # Brand favicon
├── src/
│   ├── app/
│   │   ├── layouts/
│   │   │   ├── AppLayout.tsx        # Shell orchestrating Sidebar, Header, Outlet & Footer
│   │   │   ├── Header.tsx           # Breadcrumb, status banner, reviewer identity switcher
│   │   │   └── Sidebar.tsx          # Enterprise navy collapsible & responsive navigation
│   │   ├── providers/
│   │   │   ├── AuthContext.ts       # React Auth Context type and instance
│   │   │   ├── AuthProvider.tsx     # Reviewer identity provider & local storage token sync
│   │   │   └── QueryProvider.tsx    # TanStack Query Client provider
│   │   └── router/
│   │       └── index.tsx            # Declarative route configuration & future-flag opts
│   ├── components/
│   │   ├── feedback/
│   │   │   ├── EmptyState.tsx       # Standard empty state placeholder
│   │   │   ├── ErrorBoundary.tsx    # Class error boundary with reload recovery
│   │   │   └── StatusBanner.tsx     # Live FastAPI backend connectivity pill
│   │   └── ui/
│   │       ├── Alert.tsx            # Status and architectural notices
│   │       ├── Badge.tsx            # Financial tag badges (roles, states, indicators)
│   │       ├── Button.tsx           # Multi-variant accessible button with loading states
│   │       ├── Card.tsx             # Structured container primitives (Header, Content, Footer)
│   │       └── Skeleton.tsx         # Shimmer placeholder for async data loading
│   ├── features/
│   │   ├── common/
│   │   │   └── NotFoundPage.tsx     # Clean 404 handler with return link
│   │   ├── dashboard/
│   │   │   └── DashboardPage.tsx    # Operations landing page with verified placeholder KPIs
│   │   ├── portfolios/
│   │   │   └── PortfoliosPage.tsx   # Phase 8.2 target: Portfolio valuation & drift explorer
│   │   ├── rebalancing/
│   │   │   └── RebalancingPage.tsx  # Phase 8.3 target: Deterministic proposal generation
│   │   ├── approvals/
│   │   │   └── ApprovalsPage.tsx    # Phase 8.4 target: Human review & immutable audit log
│   │   ├── policies/
│   │   │   └── PoliciesPage.tsx     # Phase 8.5 target: FastEmbed ONNX RAG & compliance Q&A
│   │   ├── workflows/
│   │   │   └── WorkflowsPage.tsx    # Phase 8.6 target: Agentic workflow lifecycle monitor
│   │   └── settings/
│   │       └── SettingsPage.tsx     # System settings, API health ping, mock token selector
│   ├── hooks/
│   │   ├── useAuth.ts               # Hook accessing current reviewer principal & tokens
│   │   └── useHealth.ts             # Polling hook querying GET /health
│   ├── lib/
│   │   └── utils.ts                 # cn() class merge, formatCurrency, formatPercent, formatDate
│   ├── services/
│   │   └── api/
│   │       ├── client.ts            # Centralized Axios client, interceptors, error types
│   │       ├── endpoints.ts         # Backend API routes mapping exactly to FastAPI routers
│   │       └── health.ts            # Health check service function
│   ├── styles/
│   │   └── index.css                # Tailwind base, utilities, and financial scrollbars
│   ├── test/
│   │   ├── api-client.test.ts       # Base URL, token headers, 401/403/422/cancel tests
│   │   ├── app.test.tsx             # Root mounting and provider initialization test
│   │   ├── dashboard.test.tsx       # Placeholder integrity & no-fake-data test
│   │   ├── router.test.tsx          # Route rendering and 404 test
│   │   ├── setup.ts                 # JSDOM matchMedia mock & testing-library cleanup
│   │   ├── shell.test.tsx           # Responsive sidebar, header, reviewer badge tests
│   │   └── test-utils.tsx           # Custom render utility with memory router and providers
│   ├── types/
│   │   ├── api.ts                   # ApiError class, ApiErrorDetail, HealthResponse
│   │   ├── auth.ts                  # ReviewerRole, ReviewerContext, DevMockTokenOption
│   │   └── navigation.ts            # NavItem, BreadcrumbItem
│   ├── App.tsx                      # Root component tree
│   └── main.tsx                     # DOM mounting point
├── .env.example                     # Documented environment template
├── .gitignore                       # Ignored build outputs and node_modules
├── eslint.config.js                 # ESLint 9 flat config
├── index.html                       # HTML5 entry with fonts and metadata
├── package.json                     # Scripts and pinned dependencies
├── postcss.config.js                # Tailwind PostCSS configuration
├── tailwind.config.js               # Enterprise financial theme and color palette
├── tsconfig.json                    # Strict TypeScript configuration with @/ alias
├── tsconfig.node.json               # Node toolchain TypeScript config
├── vite.config.ts                   # Bundler config & dev reverse proxy (/api -> :8000)
├── vitest.config.ts                 # Unit test configuration
└── README.md                        # This documentation file
```

---

## 3. Installation & Getting Started

### Prerequisites
- Node.js `v20.0+` (tested on Node.js `v22.20.0`)
- npm `10.0+` (tested on npm `11.6.2`)

### Install Dependencies
```bash
cd frontend
npm install
```

### Start Development Server
```bash
npm run dev
```
The application will launch on `http://127.0.0.1:5173`. In development mode, API requests to `/api` and `/health` are automatically proxied to the backend at `http://127.0.0.1:8000`, bypassing browser cross-origin (CORS) constraints.

---

## 4. Scripts & Commands

| Command | Purpose |
|---|---|
| `npm run dev` | Launch Vite development server with Hot Module Replacement (HMR) |
| `npm run build` | Run strict TypeScript typecheck (`tsc -b`) and bundle for production (`vite build`) |
| `npm run preview` | Locally preview the generated production build (`dist/`) |
| `npm run typecheck` | Run strict TypeScript validation without emitting files |
| `npm run lint` | Run ESLint with TypeScript and React Hook rules |
| `npm test` | Run all Vitest unit and integration suites once |
| `npm run test:watch` | Run Vitest in interactive watch mode |

---

## 5. Environment Variables (`.env.example`)

Copy `.env.example` to `.env.local` to override local defaults:

| Variable | Default Value | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `""` (empty) | Base URL for FastAPI backend. Leave empty to use Vite's internal reverse proxy. Set to `http://localhost:8000` when connecting cross-origin with CORS enabled. |
| `VITE_BACKEND_PROXY_TARGET` | `http://127.0.0.1:8000` | Target URL used by `vite.config.ts` dev server proxy. |
| `VITE_APP_ENV` | `development` | Deployment tier: `development`, `staging`, or `production`. |
| `VITE_DEFAULT_MOCK_TOKEN` | `dev-reviewer-token` | Default token pre-selected in development mode. Strictly disabled in production. |

---

## 6. Backend Connection & Authentication Architecture

### 1. Fail-Closed Security Model
The YottaFlex backend enforces an unyielding fail-closed security boundary:
- In production (`APP_ENV=production`), all client-supplied mock tokens and spoofed headers are rejected with `HTTP 401 Unauthorized`.
- In local development (`ENABLE_DEV_MOCK_AUTH=true`), the backend accepts registered mock tokens (`dev-reviewer-token`, `dev-admin-token`, `dev-viewer-token`).
- There is **no backend `/auth/login` endpoint**. Production deployments integrate an external Identity Provider (OAuth2/OIDC/SAML).

### 2. Development Mock Identity Switcher
In development mode, the top navigation header provides a live reviewer identity switcher. Reviewers can toggle between:
- `REV-DEV-01` (`REVIEWER`): Standard governance permissions.
- `REV-DEV-ADMIN` (`ADMIN`): Full administrative permissions.
- `REV-DEV-VIEWER` (`VIEWER`): Read-only reviewer. Governance approval requests return `HTTP 403 Forbidden`.

The active token is passed via `Authorization: Bearer <token>` on all requests.

---

## 7. Current Implementation Scope (Phase 8.1)

- [x] Application shell architecture with enterprise dark navy sidebar, responsive drawer, and header.
- [x] Complete Dual Theme Design System with Light, Dark, and System modes.
- [x] Anti-flash initial theme bootstrapper and persistent `localStorage` preference synchronization.
- [x] Semantic design token system (Navy/Slate surfaces, brand blue, positive emerald, negative rose, warning amber, info sky).
- [x] Reusable financial UI component library (`DataTable`, `FinancialMetricCard`, `Tabs`, `Modal`, `SearchInput`, `Button`, `Card`, `Badge`, `Alert`, `EmptyState`, `Skeleton`, `StatusBanner`, `ThemeSelector`).
- [x] Feature-specific interface architecture for all 7 primary modules (`/dashboard`, `/portfolios`, `/rebalancing`, `/approvals`, `/policies`, `/workflows`, `/settings`) with zero fabricated financial numbers.
- [x] Navigation routing for all modules + `/` redirect + 404 catch-all.
- [x] Centralized typed Axios API client with request/response interceptors, base URL resolution, and `ApiError` mapping.
- [x] Live backend connectivity monitoring via `/health` with automatic status badges.
- [x] Development reviewer token context and RBAC switcher.
- [x] 100% test coverage across 6 test suites (30 tests) verifying mounting, routing, themes, 404, shell responsiveness, API errors, and placeholder data integrity.
- [x] Strict TypeScript (`tsc --noEmit`), ESLint 9 (`eslint .`), and production bundling (`vite build`) verified.

---

## 8. Dual Theme Architecture & Design Tokens

YottaFlex implements a zero-flash dual theme system built upon Tailwind CSS's `class` dark mode strategy:

### 1. Theme Persistence & Anti-Flash
- **Storage Key:** `yottaflex_theme_preference` in `localStorage` (`light` | `dark` | `system`).
- **Inline Script (`index.html`):** Runs synchronously before React mounts to detect stored preference or `window.matchMedia('(prefers-color-scheme: dark)')`, immediately appending `.dark` to `document.documentElement` if dark mode is active.
- **Dynamic System Listener:** When `system` preference is active, changes to OS appearance update the application immediately without requiring a page refresh.

### 2. Semantic Color Palette
| Token Group | Light Theme | Dark Theme | Purpose |
|---|---|---|---|
| Background | Slate-50 (`#F8FAFC`) | Slate-950 (`#020617`) | Main application canvas |
| Surface Primary | White (`#FFFFFF`) | Slate-900 (`#0F172A`) | Cards, panels, inputs |
| Surface Secondary | Slate-100 (`#F1F5F9`) | Slate-800 (`#1E293B`) | Badges, hover rows, headers |
| Text Primary | Slate-900 (`#0F172A`) | Slate-100 (`#F1F5F9`) | High-contrast headings & data |
| Text Muted | Slate-500 (`#64748B`) | Slate-400 (`#94A3B8`) | Subtitles, labels, metadata |
| Border | Slate-200 (`#E2E8F0`) | Slate-800 (`#1E293B`) | Dividers, card frames |
| Brand Primary | Blue-600 (`#2563EB`) | Blue-500 (`#3B82F6`) | Primary CTA, active states |
| Financial Gain | Emerald-600 (`#059669`) | Emerald-400 (`#34D399`) | Positive values, buys, approvals |
| Financial Loss | Rose-600 (`#E11D48`) | Rose-400 (`#FB7185`) | Sells, rejections, drift breaches |
| Warning / Drift | Amber-600 (`#D97706`) | Amber-400 (`#FBBF24`) | Corridor breaches, staleness alerts |

---

## 9. Known Limitations & Roadmap

1. **API Integration Readiness:** Portfolio valuation, live rebalancing proposals, approval workflows, policy RAG search, and workflow execution UI feature high-fidelity interfaces and are ready for full API integration in Phase 8.3+.
2. **Identity Provider Integration:** The frontend currently utilizes development mock tokens matching the backend's `ENABLE_DEV_MOCK_AUTH=true`. A production IdP flow (e.g. Auth0 / Keycloak / Cognito) will be connected when production auth infrastructure is provisioned.
3. **CORS Requirement in Standalone Production:** If the production frontend is hosted on a separate domain from the FastAPI backend without an API gateway or reverse proxy (such as Nginx/Caddy), `CORSMiddleware` will need to be configured on the FastAPI application.
