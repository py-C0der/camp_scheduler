import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
from fastapi import HTTPException
from backend.db.database import get_connection
from backend.config import SECRET_KEY, TOKEN_EXPIRY_HOURS, MAX_FAILED_LOGIN_ATTEMPTS, LOCKOUT_MINUTES


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
    """Manages identity, authentication, session tokens, rate limiting, and RBAC."""

    def __init__(self):
        self._ensure_schema()
        self._seed_default_credentials()

    def _ensure_schema(self):
        """Ensures password_hash and security control columns exist on users table."""
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA table_info(users)")
            cols = [r[1] for r in cur.fetchall()]
            
            migrations = [
                ("password_hash", "TEXT"),
                ("is_active", "INTEGER DEFAULT 1"),
                ("failed_login_attempts", "INTEGER DEFAULT 0"),
                ("locked_until", "TEXT DEFAULT NULL"),
                ("last_login_at", "TEXT DEFAULT NULL")
            ]
            for col, col_def in migrations:
                if col not in cols:
                    cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_def}")
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
            cur.execute("SELECT id, email, password_hash, is_active FROM users")
            rows = cur.fetchall()
            for r in rows:
                if not r["password_hash"]:
                    cur.execute(
                        "UPDATE users SET password_hash = ? WHERE id = ?",
                        (default_pwd, r["id"])
                    )
                if r["is_active"] is None:
                    cur.execute(
                        "UPDATE users SET is_active = 1 WHERE id = ?",
                        (r["id"],)
                    )
            conn.commit()
        except Exception as e:
            print(f"[Warning] Failed to seed default credentials: {e}")
        finally:
            conn.close()

    def generate_token(self, user_id: str, role: str, email: str) -> Tuple[str, str]:
        """
        Generates an HMAC-SHA256 signed bearer token.
        Returns: (token_string, iso_expiry_timestamp)
        """
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=TOKEN_EXPIRY_HOURS)
        exp_iso = exp.isoformat()

        payload = {
            "sub": user_id,
            "role": role,
            "email": email,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp())
        }
        
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode('ascii').rstrip('=')
        
        signature = hmac.new(
            SECRET_KEY.encode('utf-8'),
            payload_b64.encode('ascii'),
            hashlib.sha256
        ).hexdigest()
        
        token = f"{payload_b64}.{signature}"
        return token, exp_iso

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verifies bearer token signature and expiration.
        Raises HTTPException(401) on invalid or expired token.
        """
        if not token or "." not in token:
            raise HTTPException(status_code=401, detail="Invalid token format.")
            
        payload_b64, signature = token.split(".", 1)
        expected_sig = hmac.new(
            SECRET_KEY.encode('utf-8'),
            payload_b64.encode('ascii'),
            hashlib.sha256
        ).hexdigest()
        
        if not secrets.compare_digest(signature, expected_sig):
            raise HTTPException(status_code=401, detail="Authentication token signature verification failed.")
            
        try:
            # Add padding back if necessary
            rem = len(payload_b64) % 4
            if rem > 0:
                payload_b64 += '=' * (4 - rem)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode('ascii')).decode('utf-8'))
        except Exception:
            raise HTTPException(status_code=401, detail="Corrupted token payload.")
            
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if payload.get("exp", 0) < now_ts:
            raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
            
        return payload

    def log_audit(self, user_id: str, user_role: str, action: str, details: Dict[str, Any]):
        """Records security actions in the audit_logs table."""
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO audit_logs (user_id, user_role, action, details_json, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                user_role,
                action,
                json.dumps(details),
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()
        except Exception as e:
            print(f"[Warning] Failed to write security audit log: {e}")
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

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves user profile by ID."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id.strip(),))
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
            "department": user.get("department", "CIT Campus"),
            "is_active": bool(user.get("is_active", 1)),
            "role_occupancy": occupancy
        }

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticates a user with email and password:
        1. Checks account activation (blocks deactivated accounts).
        2. Enforces brute-force lockout window.
        3. Validates PBKDF2 hash.
        4. Issues HMAC-signed bearer session token.
        5. Logs security audit events.
        """
        email_clean = email.strip().lower()
        alias_map = {
            "coordinator@cit.ac.in": "cse_coord@cit.ac.in",
            "coordinator": "cse_coord@cit.ac.in",
            "cse_coord": "cse_coord@cit.ac.in",
            "faculty@cit.ac.in": "arvind@cit.ac.in",
            "faculty": "arvind@cit.ac.in",
            "arvind": "arvind@cit.ac.in",
            "club@cit.ac.in": "techclub@cit.ac.in",
            "club": "techclub@cit.ac.in",
            "admin": "admin@cit.ac.in",
            "dean": "admin@cit.ac.in"
        }
        if email_clean in alias_map:
            email_clean = alias_map[email_clean]
        user = self.get_user_by_email(email_clean)

        if not user:
            # User doesn't exist yet -> Instruct frontend to request role
            return {
                "status": "new_user",
                "email": email_clean,
                "message": "User not found. Please choose your role to complete registration.",
                "role_occupancy": self.get_role_occupancy()
            }

        user_id = user["id"]
        user_role = user["role"]

        # 1. Check Account Activation
        if user.get("is_active") == 0:
            self.log_audit(user_id, user_role, "LOGIN_BLOCKED_INACTIVE", {"email": email_clean})
            raise HTTPException(
                status_code=403,
                detail="Account is deactivated. Please contact the Campus System Administrator."
            )

        # 2. Check Lockout Status
        now_dt = datetime.now(timezone.utc)
        locked_until_str = user.get("locked_until")
        if locked_until_str:
            try:
                locked_until_dt = datetime.fromisoformat(locked_until_str)
                if now_dt < locked_until_dt:
                    remaining_sec = int((locked_until_dt - now_dt).total_seconds())
                    remaining_min = max(1, remaining_sec // 60)
                    self.log_audit(user_id, user_role, "LOGIN_BLOCKED_LOCKOUT", {"email": email_clean, "remaining_seconds": remaining_sec})
                    raise HTTPException(
                        status_code=429,
                        detail=f"Account is temporarily locked due to multiple failed login attempts. Please try again in {remaining_min} minutes."
                    )
            except Exception as e:
                if isinstance(e, HTTPException): raise e

        # 3. Verify Password
        stored_hash = user.get("password_hash")
        if not stored_hash:
            new_hash = hash_password(password)
            conn = get_connection()
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
            conn.commit()
            conn.close()
            user["password_hash"] = new_hash

        if not verify_password(password, user["password_hash"]):
            # Increment failed attempts
            failed = (user.get("failed_login_attempts") or 0) + 1
            conn = get_connection()
            if failed >= MAX_FAILED_LOGIN_ATTEMPTS:
                lock_time = (now_dt + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
                conn.execute("UPDATE users SET failed_login_attempts = ?, locked_until = ? WHERE id = ?", (failed, lock_time, user_id))
                conn.commit()
                conn.close()
                self.log_audit(user_id, user_role, "ACCOUNT_LOCKED", {"email": email_clean, "failed_attempts": failed, "locked_until": lock_time})
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many failed login attempts ({failed}/{MAX_FAILED_LOGIN_ATTEMPTS}). Account locked for {LOCKOUT_MINUTES} minutes."
                )
            else:
                conn.execute("UPDATE users SET failed_login_attempts = ? WHERE id = ?", (failed, user_id))
                conn.commit()
                conn.close()
                self.log_audit(user_id, user_role, "LOGIN_FAILED", {"email": email_clean, "failed_attempts": failed})
                raise HTTPException(
                    status_code=401,
                    detail=f"Invalid password. Attempt {failed} of {MAX_FAILED_LOGIN_ATTEMPTS} before temporary lockout."
                )

        # 4. Success -> Reset failed attempts & issue token
        now_str = now_dt.isoformat()
        conn = get_connection()
        conn.execute("UPDATE users SET failed_login_attempts = 0, locked_until = NULL, last_login_at = ? WHERE id = ?", (now_str, user_id))
        conn.commit()
        conn.close()

        token, expires_at = self.generate_token(user_id, user_role, email_clean)
        self.log_audit(user_id, user_role, "LOGIN_SUCCESS", {"email": email_clean})

        return {
            "status": "authenticated",
            "success": True,
            "message": "Login successful.",
            "token": token,
            "token_type": "Bearer",
            "expires_at": expires_at,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "department": user.get("department", "CIT Campus"),
                "faculty_id": user.get("faculty_id"),
                "is_active": bool(user.get("is_active", 1))
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
        """Registers a new user with exclusive role protection."""
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

        user_id = email_clean.split("@")[0].replace(".", "_")
        if normalized_role == "student":
            user_id = f"stu_{user_id}"

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
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO users (id, name, email, password_hash, role, department, created_at, is_active, failed_login_attempts)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0)
        """, (user_id, name, email_clean, pwd_hash, normalized_role, department or "General", now_str))
        conn.commit()
        conn.close()

        token, expires_at = self.generate_token(user_id, normalized_role, email_clean)
        self.log_audit(user_id, normalized_role, "REGISTER", {"email": email_clean})

        return {
            "status": "authenticated",
            "message": f"Account successfully created as {normalized_role.upper()}.",
            "token": token,
            "token_type": "Bearer",
            "expires_at": expires_at,
            "user": {
                "id": user_id,
                "name": name,
                "email": email_clean,
                "role": normalized_role,
                "department": department or "General",
                "is_active": True
            }
        }

    def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """Secure password change with old password verification and complexity checks."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        if not verify_password(old_password, user.get("password_hash", "")):
            self.log_audit(user_id, user["role"], "PASSWORD_CHANGE_FAILED", {"reason": "incorrect_old_password"})
            raise HTTPException(status_code=400, detail="Current password incorrect.")

        if not new_password or len(new_password) < 6:
            raise HTTPException(status_code=400, detail="New password must be at least 6 characters long.")

        new_hash = hash_password(new_password)
        conn = get_connection()
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
        conn.commit()
        conn.close()

        self.log_audit(user_id, user["role"], "PASSWORD_CHANGED", {"timestamp": datetime.now(timezone.utc).isoformat()})
        return {"status": "success", "message": "Password changed successfully."}

    def set_user_status(self, admin_id: str, target_user_id: str, is_active: bool) -> Dict[str, Any]:
        """Admin-only account activation/deactivation."""
        admin = self.get_user_by_id(admin_id)
        if not admin or admin.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Unauthorized: Only an Administrator can change account status.")

        target = self.get_user_by_id(target_user_id)
        if not target:
            raise HTTPException(status_code=404, detail="Target user not found.")

        if target["role"] == "admin" and not is_active:
            raise HTTPException(status_code=400, detail="Cannot deactivate the Dean/Admin account.")

        conn = get_connection()
        conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (1 if is_active else 0, target_user_id))
        conn.commit()
        conn.close()

        self.log_audit(admin_id, "admin", "ACCOUNT_STATUS_CHANGED", {
            "target_user_id": target_user_id,
            "target_email": target["email"],
            "is_active": is_active
        })
        return {
            "status": "success",
            "message": f"User '{target_user_id}' {'activated' if is_active else 'deactivated'} successfully."
        }
