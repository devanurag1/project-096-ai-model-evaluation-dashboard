"""FastAPI request dependencies for authentication, correlation IDs, and RBAC."""
import uuid
from typing import Optional
from fastapi import Header, Depends
from app.security.auth import AuthenticatedUser, resolve_authenticated_user
from app.security.rbac import enforce_permission
from app.models.domain import UserRole


def get_correlation_id(x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")) -> str:
    """Extract or generate request correlation ID for end-to-end traceability."""
    return x_correlation_id or f"CORR-{uuid.uuid4().hex[:12].upper()}"


def get_current_user(user: AuthenticatedUser = Depends(resolve_authenticated_user)) -> AuthenticatedUser:
    """Return the currently resolved authenticated user persona."""
    return user


def require_permission(permission: str):
    """Factory creating dependency to enforce required permission."""
    def _dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        enforce_permission(user.role, permission, actor=user.email)
        return user
    return _dependency
