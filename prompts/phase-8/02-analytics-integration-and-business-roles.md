# Phase 8 — Analytics Integration, User Abstraction and RBAC

## Objective
Connect the frontend to real portfolio analytics and expose role-appropriate business workflows.

## Portfolio and analytics experience
- Integrate portfolio listing/details and valuation APIs.
- Show portfolio value, holdings and asset-class allocation.
- Visualize target versus actual allocation and portfolio drift.
- Support as-of-date context where the API provides it.
- Display stale/missing price diagnostics and API errors explicitly.
- Avoid fabricating values or silently using mock fallback data.

## User-facing abstraction
Present technical workflow details in clear business language while preserving traceability and meaningful exceptions. Users should understand why a recommendation was produced, what is blocked and what requires review.

## RBAC-aware experience
Provide role-appropriate actions and visibility for customer/account holder, operations analyst, risk/compliance reviewer and administrator, consistent with backend authorization. Hiding a UI control is not a substitute for backend authorization.

## Integration verification
Test API request/response mapping, loading/error/empty states, role-specific behavior, theme behavior and core user journeys. Verify the frontend against the actual running backend rather than hardcoded sample responses.
