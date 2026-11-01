"""
Authentication and User Role Management API Routes.
Provides:
- Email existence check & exclusive role occupancy status.
- Secure PBKDF2 password login with brute-force lockout protection.
- Session bearer token generation and verification.
- New user registration with single-user exclusive Dean role constraint.
- Password change functionality.
- Admin user activation / deactivation.
- Security audit logs.
- Active users list.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Header
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


class ChangePasswordPayload(BaseModel):
    user_id: str
    old_password: str
    new_password: str


class UserStatusPayload(BaseModel):
    admin_id: str
    is_active: bool


class VerifyTokenPayload(BaseModel):
    token: str


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
    Returns authenticated user with signed bearer token and expiration.
    Enforces brute-force lockout and deactivated account protection.
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


@router.post("/change-password")
def change_password(payload: ChangePasswordPayload):
    """Changes password for an authenticated user after verifying current password."""
    return auth_service.change_password(
        user_id=payload.user_id,
        old_password=payload.old_password,
        new_password=payload.new_password
    )


@router.post("/users/{user_id}/status")
def set_user_status(user_id: str, payload: UserStatusPayload):
    """Activates or deactivates an account (Admin only)."""
    return auth_service.set_user_status(
        admin_id=payload.admin_id,
        target_user_id=user_id,
        is_active=payload.is_active
    )


@router.post("/verify-token")
def verify_token_api(payload: VerifyTokenPayload):
    """Validates signature and expiration of a session bearer token."""
    return auth_service.verify_token(payload.token)


@router.get("/users")
def list_users():
    """Lists registered system users without exposing password hashes."""
    from backend.db.database import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, role, department, is_active, last_login_at, created_at FROM users ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return {"users": [dict(r) for r in rows]}


@router.get("/audit-logs")
def get_audit_logs(admin_id: str = "admin_1", limit: int = 50):
    """Returns security audit logs (Admin only)."""
    user = auth_service.get_user_by_id(admin_id)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized: Only an Administrator can access security audit logs.")

    from backend.db.database import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, user_id, user_role, action, details_json, timestamp FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return {"audit_logs": [dict(r) for r in rows]}
