"""API dependencies for authentication, authorization, and database session injection."""

from abc import ABC, abstractmethod
import logging
import os
from typing import Optional
from fastapi import Depends, Header, HTTPException, status

from app.schemas.approval import ReviewerContext

logger = logging.getLogger(__name__)

# Permitted roles for rebalance proposal approval and rejection governance
PERMITTED_APPROVAL_ROLES = {"REVIEWER", "ADMIN", "COMPLIANCE_OFFICER", "PORTFOLIO_MANAGER"}


class BaseAuthenticationVerifier(ABC):
    """Abstract interface for verifying external authentication tokens."""

    @abstractmethod
    def verify_token(self, token: str) -> Optional[ReviewerContext]:
        """Verify the credential/token and return a verified ReviewerContext principal, or None if invalid."""
        pass


class ProductionAuthenticationVerifier(BaseAuthenticationVerifier):
    """Production verifier that requires an integrated trusted IdP (e.g. OAuth2, OIDC, JWT).

    Fails closed: Because no production identity provider is configured in this standalone
    deployment, all unverified client tokens are rejected. Arbitrary tokens are NEVER accepted.
    """

    def verify_token(self, token: str) -> Optional[ReviewerContext]:
        # Production default: Reject all client-supplied tokens without a real IdP
        return None


class DevMockAuthenticationVerifier(BaseAuthenticationVerifier):
    """Explicit development-only mock verifier. Disabled by default, strictly unavailable in production."""

    def __init__(self, allowed_tokens: Optional[dict[str, ReviewerContext]] = None) -> None:
        self.allowed_tokens = allowed_tokens or {
            "dev-reviewer-token": ReviewerContext(
                reviewer_id="REV-DEV-01", role="REVIEWER", email="dev.reviewer@firm.com"
            ),
            "dev-admin-token": ReviewerContext(
                reviewer_id="REV-DEV-ADMIN", role="ADMIN", email="dev.admin@firm.com"
            ),
            "dev-viewer-token": ReviewerContext(
                reviewer_id="REV-DEV-VIEWER", role="VIEWER", email="dev.viewer@firm.com"
            ),
        }

    def verify_token(self, token: str) -> Optional[ReviewerContext]:
        return self.allowed_tokens.get(token)


def get_auth_verifier() -> BaseAuthenticationVerifier:
    """Dependency provider returning the active AuthenticationVerifier.

    Enforces that development mock authentication CANNOT be activated in a production environment.
    """
    app_env = os.getenv("APP_ENV", "development").lower()
    enable_dev_mock_str = os.getenv("ENABLE_DEV_MOCK_AUTH", "false").lower()
    enable_dev_mock = enable_dev_mock_str in ("1", "true", "yes", "on")

    # In production environments, mock authentication is strictly forbidden
    if app_env in ("production", "prod"):
        if enable_dev_mock:
            logger.error("SECURITY VIOLATION: ENABLE_DEV_MOCK_AUTH attempted in production environment!")
            raise RuntimeError(
                "Development-only mock authentication cannot be activated in a production environment."
            )
        return ProductionAuthenticationVerifier()

    if enable_dev_mock:
        logger.info("Using DevMockAuthenticationVerifier for local development/testing.")
        return DevMockAuthenticationVerifier()

    return ProductionAuthenticationVerifier()


def get_current_reviewer(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    verifier: BaseAuthenticationVerifier = Depends(get_auth_verifier),
) -> ReviewerContext:
    """Derive reviewer identity exclusively from a verified authentication principal.

    Security Requirements:
    - Never trust client-supplied X-Reviewer-Id, role, or request body.
    - Never accept arbitrary Bearer tokens without cryptographic or trusted verification.
    - Must reject unauthenticated requests with HTTP 401.
    - Must reject verified principals with insufficient permissions with HTTP 403.
    """
    if not authorization or not authorization.startswith("Bearer "):
        logger.warning("Unauthenticated request: missing or malformed Bearer authorization header.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided or are malformed.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:].strip()
    if not token:
        logger.warning("Unauthenticated request: empty Bearer token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token was empty.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    verified_principal = verifier.verify_token(token)
    if not verified_principal:
        logger.warning("Unauthenticated request: token verification failed for token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Permission check
    role = (verified_principal.role or "").strip().upper()
    if role not in PERMITTED_APPROVAL_ROLES:
        logger.warning(
            "Forbidden: verified principal '%s' with role '%s' lacks approval permission.",
            verified_principal.reviewer_id,
            role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Reviewer role '{role}' is not authorized to approve or reject rebalance proposals.",
        )

    return verified_principal
