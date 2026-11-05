"""Authentication and user context resolution."""
from typing import Optional
from fastapi import Header, HTTPException, status
from app.models.domain import UserRole


# Default mock personas for enterprise demonstration
PRECONFIGURED_USERS = {
    "user_business": {
        "id": "usr-biz-01",
        "email": "sarah.finance@apexglobal.com",
        "name": "Sarah Jenkins (Financial Analyst)",
        "role": UserRole.BUSINESS_USER,
    },
    "user_engineer": {
        "id": "usr-eng-02",
        "email": "alex.chen@apexglobal.com",
        "name": "Alex Chen (Lead ML Engineer)",
        "role": UserRole.EVAL_ENGINEER,
    },
    "user_compliance": {
        "id": "usr-cmp-03",
        "email": "elena.rostova@apexglobal.com",
        "name": "Elena Rostova (Chief Compliance Officer)",
        "role": UserRole.COMPLIANCE_OFFICER,
    },
    "user_admin": {
        "id": "usr-adm-04",
        "email": "marcus.vance@apexglobal.com",
        "name": "Marcus Vance (SecOps Lead)",
        "role": UserRole.SECOPS_ADMIN,
    },
}


class AuthenticatedUser:
    def __init__(self, user_id: str, email: str, name: str, role: UserRole):
        self.user_id = user_id
        self.email = email
        self.name = name
        self.role = role


def resolve_authenticated_user(
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> AuthenticatedUser:
    """Resolve current user persona from header, default to business_user (least privilege)."""
    # 1. Check if explicit X-User-Role provided (useful for UI role switching)
    if x_user_role:
        role_key = x_user_role.lower().strip()
        for u in PRECONFIGURED_USERS.values():
            if u["role"].value == role_key or role_key in u["id"]:
                return AuthenticatedUser(
                    user_id=u["id"],
                    email=u["email"],
                    name=u["name"],
                    role=u["role"],
                )

    # 2. Check Authorization Bearer token
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()
        if token in PRECONFIGURED_USERS:
            u = PRECONFIGURED_USERS[token]
            return AuthenticatedUser(
                user_id=u["id"],
                email=u["email"],
                name=u["name"],
                role=u["role"],
            )

    # 3. Default to lowest privilege: business_user
    default_u = PRECONFIGURED_USERS["user_business"]
    return AuthenticatedUser(
        user_id=default_u["id"],
        email=default_u["email"],
        name=default_u["name"],
        role=default_u["role"],
    )
