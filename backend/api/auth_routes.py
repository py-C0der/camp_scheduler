"""
Authentication and User Role Management API Routes.
Provides:
- Email existence check & exclusive role occupancy status.
- Secure PBKDF2 password login.
- New user registration with single-user exclusive Dean role constraint.
- Automatic Student fallback.
- Active users list.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication & RBAC"])
auth_service = AuthService()


class CheckEmailPayload(BaseModel):
    email: str


class LoginPayload(BaseModel):
    email: str
    password: str


class RegisterPayload(BaseModel):
    email: str
    password: str
    role: str = "student"
    name: Optional[str] = None
    department: Optional[str] = None


@router.post("/check-email")
def check_email(payload: CheckEmailPayload):
    """Checks if an email is registered and reports role occupancy."""
    return auth_service.check_user_exists(payload.email)


@router.get("/roles-status")
def get_roles_status():
    """Returns status on whether single-occupant roles (like Dean) are claimed."""
    return auth_service.get_role_occupancy()


@router.post("/login")
def login(payload: LoginPayload):
    """
    Authenticates user with email and password.
    Returns authenticated user or instructs frontend if new user.
    """
    return auth_service.login(payload.email, payload.password)


@router.post("/register")
def register(payload: RegisterPayload):
    """
    Registers a new user with password and selected role.
    Strictly verifies that exclusive single-occupant roles (like Dean) are not stolen.
    Defaults to 'student' role if general user.
    """
    return auth_service.register(
        email=payload.email,
        password=payload.password,
        role=payload.role,
        name=payload.name,
        department=payload.department
    )


@router.get("/users")
def list_users():
    """Lists registered system users."""
    from backend.db.database import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, role, department, created_at FROM users ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return {"users": [dict(r) for r in rows]}
