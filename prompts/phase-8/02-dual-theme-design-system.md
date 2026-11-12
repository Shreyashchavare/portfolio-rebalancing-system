# Phase 8.2 — Dual Theme Design System & Feature-Specific Interface Architecture

## Objective

Upgrade the existing YottaFlex frontend into a distinctive, premium enterprise fintech application with complete Light and Dark themes and dedicated interaction patterns for every business module.

This phase builds on the completed Phase 8.1 foundation. Do not recreate the frontend or replace its architecture unnecessarily.

## 1. Mandatory design principles

1. Support both Light and Dark themes across the entire application.
2. Every page, component, chart, table, dropdown, modal, tooltip, empty state and notification must support both themes.
3. Provide a persistent theme selector with Light, Dark and System options.
4. Default to the user's system preference when no preference has been saved.
5. Persist the explicit theme selection across browser sessions.
6. Avoid flash of the wrong theme during initial rendering.
7. Use semantic design tokens rather than hardcoded colors throughout components.
8. Maintain accessible contrast and keyboard navigation.
9. Do not make all feature pages look like identical CRUD dashboards.
10. Maintain an enterprise financial product aesthetic rather than a generic admin template.

## 2. Visual identity

Develop a consistent YottaFlex visual language.

Light theme:
- Soft neutral or off-white application background.
- White or subtly tinted content surfaces.
- Deep navy typography.
- Restrained blue brand accent.
- Clear borders and subtle elevation.
- Strong readability for dense financial tables.

Dark theme:
- Deep charcoal/navy application background.
- Distinct elevated surfaces.
- Muted secondary typography.
- Carefully selected brand accents.
- Clear semantic success, warning, danger and information colors.
- No excessive neon colors, gradients or glowing effects.

Both themes must have equivalent visual hierarchy and usability.

## 3. Design token architecture

Create centralized semantic tokens for:

- Application background.
- Sidebar and header surfaces.
- Primary, secondary and elevated surfaces.
- Primary and secondary text.
- Muted text.
- Borders and separators.
- Primary and secondary actions.
- Focus and selection states.
- Success, warning, danger and information.
- Financial positive and negative values.
- Chart series and chart grid lines.
- Shadows, radii and spacing.

Integrate tokens with Tailwind CSS and the existing component architecture.

Do not duplicate entire component implementations for dark and light themes.

## 4. Theme interaction

Implement:
- Light theme.
- Dark theme.
- System theme.
- Header theme selector.
- Persistent preference.
- System preference detection.
- Accessible selected-state indicators.
- Correct initial theme rendering.

Ensure charts, SVGs, icons, tables, skeletons, dialogs and third-party UI elements follow the active theme.

Test switching themes without navigating away from the current page.

## 5. Feature-specific interface architecture

Design each module around its actual business workflow.

### A. Dashboard
Executive financial overview:
- KPI presentation.
- Portfolio distribution.
- Risk and governance indicators.
- Recent workflow activity.
- Backend and data freshness status.

Do not invent financial data. Continue to use explicit placeholders until actual APIs are integrated.

### B. Portfolio management
Analytical interface:
- Portfolio selector.
- Valuation summary.
- Holdings table.
- Asset allocation visualization.
- Target versus actual allocation.
- Drift analysis.
- Market-price age diagnostics.

Use appropriate financial table density and chart layouts.

### C. Rebalancing workspace
Trading and decision-support interface:
- Selected portfolio context.
- Current allocation and target allocation.
- Proposed BUY and SELL trades.
- Trade quantities and notional values.
- Constraint evaluation.
- Blocked trades.
- Simulation results.
- Human-review requirements.

Make financial safety information visually prominent.

### D. Approvals and governance
Reviewer-centric interface:
- Pending review queue.
- Proposal summary.
- Trade-level detail.
- Constraint findings.
- Approval and rejection actions.
- Mandatory rejection reason.
- Audit history.

Never visually imply that approval executes trades.

### E. Policy intelligence
Knowledge and AI research interface:
- Policy document library.
- Document metadata and status.
- Search and filtering.
- Question-answering workspace.
- Grounded answer presentation.
- Citation/source inspection.
- Insufficient-evidence and human-review indicators.

### F. Workflow monitoring
Operational monitoring interface:
- Workflow list.
- Execution timeline.
- State transitions.
- Proposal association.
- Policy retrieval status.
- Explanation status.
- Errors and warnings.
- Human-review state.

Use a timeline or state visualization where appropriate.

### G. Settings
Provide clear configuration groups for:
- Appearance.
- API connectivity.
- Account and role information.
- Application preferences.

## 6. Reusable component system

Build or refine reusable primitives:

- Buttons.
- Icon buttons.
- Cards.
- Data tables.
- Financial metric cards.
- Status badges.
- Tabs.
- Dropdowns.
- Dialogs.
- Tooltips.
- Alerts.
- Empty states.
- Loading skeletons.
- Chart containers.
- Search inputs.
- Filter controls.
- Page headers.
- Breadcrumbs.

All components must consume semantic theme tokens.

Feature-specific components should remain within their feature folders.

## 7. Responsive behavior

Support:
- Desktop financial workstation.
- Laptop.
- Tablet.
- Mobile.

Financial tables should use an intentional responsive strategy such as horizontal scrolling, column prioritization or mobile detail cards.

Avoid simply shrinking desktop layouts.

## 8. Technical constraints

Preserve:
- React 18.
- TypeScript strict mode.
- Vite.
- React Router.
- Tailwind CSS.
- TanStack Query.
- Axios API client.
- Existing application providers.
- Existing test infrastructure.

Do not introduce unnecessary dependencies.

Do not weaken authentication, authorization or API error handling.

Do not change backend APIs or database records for visual implementation.

## 9. Testing

Add tests for:

1. Light theme rendering.
2. Dark theme rendering.
3. System theme behavior.
4. Persistent theme preference.
5. Theme switching without page reload.
6. Correct theme initialization.
7. Theme coverage across all routes.
8. Accessible controls.
9. No regression in existing frontend tests.

Run:
- npm run typecheck
- npm run lint
- npm test
- npm run build

Report exact results.

## 10. Documentation and prompt history

Create:

`prompts/phase-8/02-dual-theme-design-system.md`

Update `frontend/README.md` with theme architecture and development conventions.

Do not overwrite Phase 8.1 prompt history.

## 11. Acceptance criteria

Phase 8.2 is complete only when:

- Both themes are implemented.
- System theme is supported.
- User preference persists.
- All routes support both themes.
- Feature-specific visual architecture is established.
- Shared components use semantic tokens.
- No fabricated financial data is introduced.
- Existing frontend tests remain passing.
- New theme tests pass.
- Backend tests remain unaffected.
- Typecheck, lint and build succeed.
- Git diff is reviewed.
- No unrelated files or seeded data are changed.

## 12. Final report

Report:
- Theme architecture.
- Token system.
- Theme switching behavior.
- Feature-specific interface changes.
- Files created and modified.
- Tests and exact results.
- Build result.
- Known limitations.
- Git status.
- Recommended next implementation phase.

Do not mark this phase complete if any mandatory acceptance criterion fails.