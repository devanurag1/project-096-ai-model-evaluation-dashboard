"""Role-Based Access Control (RBAC) and Least Privilege Enforcement."""
from typing import Dict, Set
from fastapi import HTTPException, status
from app.models.domain import UserRole


# Explicit permission map by role
ROLE_PERMISSIONS: Dict[UserRole, Set[str]] = {
    UserRole.BUSINESS_USER: {
        "models:read",
        "evaluations:read",
        "comparison:read",
        "metrics:read",
        "health:read",
    },
    UserRole.EVAL_ENGINEER: {
        "models:read",
        "models:register",
        "evaluations:read",
        "evaluations:run",
        "comparison:read",
        "metrics:read",
        "benchmarks:read",
        "health:read",
    },
    UserRole.COMPLIANCE_OFFICER: {
        "models:read",
        "models:register",
        "evaluations:read",
        "evaluations:run",
        "comparison:read",
        "metrics:read",
        "benchmarks:read",
        "exceptions:grant",
        "exceptions:revoke",
        "policies:read",
        "policies:update",
        "audit:read",
        "audit:verify",
        "health:read",
    },
    UserRole.SECOPS_ADMIN: {
        "models:read",
        "models:register",
        "evaluations:read",
        "evaluations:run",
        "comparison:read",
        "metrics:read",
        "benchmarks:read",
        "exceptions:grant",
        "exceptions:revoke",
        "policies:read",
        "policies:update",
        "audit:read",
        "audit:verify",
        "audit:export",
        "system:quarantine",
        "health:read",
    },
}


def check_permission(role: UserRole, required_permission: str) -> bool:
    """Check if the given role possesses the required permission string."""
    allowed_permissions = ROLE_PERMISSIONS.get(role, set())
    return required_permission in allowed_permissions


def enforce_permission(role: UserRole, required_permission: str, actor: str = "anonymous") -> None:
    """Fail closed with HTTP 403 Forbidden if the user lacks the required permission."""
    if not check_permission(role, required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "AccessDenied",
                "message": f"Role '{role.value}' does not have permission '{required_permission}'.",
                "actor": actor,
                "required_permission": required_permission,
                "assigned_role": role.value,
            },
        )
