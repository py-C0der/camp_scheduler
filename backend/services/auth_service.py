"""
Authentication and User Access Management Service.
Handles:
1. PBKDF2 cryptographic password hashing and verification.
2. Single-account exclusive role enforcement (e.g. Dean/Admin can only be held by 1 person).
3. Email uniqueness and role verification (Dean, Coordinator, Faculty, Club Rep, Student).
4. Default fallback to Student role for general users.
5. Persistent SQLite storage with auto-migration.
"""

import hashlib
import os
import secrets
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from fastapi import HTTPException
from backend.db.database import get_connection


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hashes password using PBKDF2-HMAC-SHA256 with a unique cryptographic salt."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"{salt}${hashed}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a plain password against stored salt$hash."""
    if not stored_hash or "$" not in stored_hash:
        return False
    salt, hash_val = stored_hash.split("$", 1)
    computed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return secrets.compare_digest(computed, hash_val)


class AuthService:
    """Manages identity, authentication, role claims, and user state."""

    def __init__(self):
        self._ensure_schema()
        self._seed_default_credentials()

    def _ensure_schema(self):
        """Ensures password_hash column exists on users table."""
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA table_info(users)")
            cols = [r[1] for r in cur.fetchall()]
            if "password_hash" not in cols:
                cur.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
                conn.commit()
        except Exception as e:
            print(f"[Warning] Failed to migrate users schema: {e}")
        finally:
            conn.close()

    def _seed_default_credentials(self):
        """Ensures demo accounts have default password hashes set if unset."""
        conn = get_connection()
        cur = conn.cursor()
        try:
            default_pwd = hash_password("cit@2026")
            cur.execute("SELECT id, email, password_hash FROM users")
            rows = cur.fetchall()
            for r in rows:
                if not r["password_hash"]:
                    cur.execute(
                        "UPDATE users SET password_hash = ? WHERE id = ?",
                        (default_pwd, r["id"])
                    )
            conn.commit()
        except Exception as e:
            print(f"[Warning] Failed to seed default credentials: {e}")
        finally:
            conn.close()

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieves user profile by email (case-insensitive)."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_role_occupancy(self) -> Dict[str, Any]:
        """Returns details on which exclusive roles are currently claimed."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, role FROM users WHERE role IN ('admin', 'dept_coordinator', 'faculty', 'club_rep')")
        rows = cur.fetchall()
        conn.close()

        claimed = {}
        for r in rows:
            claimed[r["role"]] = {
                "user_id": r["id"],
                "name": r["name"],
                "email": r["email"]
            }

        return {
            "dean_claimed": "admin" in claimed,
            "dean_user": claimed.get("admin"),
            "coordinator_claimed": "dept_coordinator" in claimed,
            "coordinator_user": claimed.get("dept_coordinator"),
            "claimed_roles": claimed
        }

    def check_user_exists(self, email: str) -> Dict[str, Any]:
        """Checks if email is registered and returns public profile if found."""
        user = self.get_user_by_email(email)
        occupancy = self.get_role_occupancy()
        if not user:
            return {
                "exists": False,
                "email": email.strip().lower(),
                "role_occupancy": occupancy
            }
        return {
            "exists": True,
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "department": user.get("department"),
            "role_occupancy": occupancy
        }

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticates user with email and password.
        Returns user details or flags if user is new.
        """
        email_clean = email.strip().lower()
        user = self.get_user_by_email(email_clean)

        if not user:
            # User doesn't exist yet -> Instruct frontend to request role
            return {
                "status": "new_user",
                "email": email_clean,
                "message": "User not found. Please choose your role to complete registration.",
                "role_occupancy": self.get_role_occupancy()
            }

        stored_hash = user.get("password_hash")
        # If user has no password yet (legacy seed), accept cit@2026 or set the provided password
        if not stored_hash:
            new_hash = hash_password(password)
            conn = get_connection()
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user["id"]))
            conn.commit()
            conn.close()
            user["password_hash"] = new_hash

        if not verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid password. Please check your credentials and try again.")

        return {
            "status": "authenticated",
            "message": "Login successful.",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "department": user.get("department", "CIT Campus"),
                "faculty_id": user.get("faculty_id")
            }
        }

    def register(
        self,
        email: str,
        password: str,
        role: str,
        name: Optional[str] = None,
        department: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Registers a new user with exclusive role protection:
        - Only 1 user can occupy the 'admin' (Dean) role.
        - Defaults to 'student' if no valid role selected.
        """
        email_clean = email.strip().lower()
        if not email_clean or "@" not in email_clean:
            raise HTTPException(status_code=400, detail="Please provide a valid email address.")

        if not password or len(password) < 4:
            raise HTTPException(status_code=400, detail="Password must be at least 4 characters long.")

        existing = self.get_user_by_email(email_clean)
        if existing:
            raise HTTPException(status_code=400, detail="An account with this email already exists. Please log in instead.")

        valid_roles = ["admin", "dept_coordinator", "faculty", "club_rep", "student"]
        normalized_role = role.lower().strip() if role else "student"
        if normalized_role not in valid_roles:
            normalized_role = "student"

        # STRICT EXCLUSIVE ROLE CHECK: Only 1 Dean / Admin permitted in the entire system!
        if normalized_role == "admin":
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT email, name FROM users WHERE role = 'admin'")
            admin_row = cur.fetchone()
            conn.close()
            if admin_row:
                raise HTTPException(
                    status_code=403,
                    detail=f"The Dean / Full Admin role is exclusive and already occupied by {admin_row['email']}. Only one Dean account is permitted in the system."
                )

        # Generate User ID
        user_id = email_clean.split("@")[0].replace(".", "_")
        if normalized_role == "student":
            user_id = f"stu_{user_id}"

        # Default Names based on role
        if not name:
            if normalized_role == "admin":
                name = "Dean Academics"
            elif normalized_role == "dept_coordinator":
                name = "Department Coordinator"
            elif normalized_role == "faculty":
                name = "Faculty Member"
            elif normalized_role == "club_rep":
                name = "Club Representative"
            else:
                name = email_clean.split("@")[0].replace(".", " ").title()

        pwd_hash = hash_password(password)

        conn = get_connection()
        cur = conn.cursor()
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO users (id, name, email, password_hash, role, department, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, email_clean, pwd_hash, normalized_role, department or "General", now_str))
        conn.commit()
        conn.close()

        return {
            "status": "authenticated",
            "message": f"Account successfully created as {normalized_role.upper()}.",
            "user": {
                "id": user_id,
                "name": name,
                "email": email_clean,
                "role": normalized_role,
                "department": department or "General"
            }
        }
