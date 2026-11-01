# CIT Campus Scheduling and Venue Management Platform
## Application Security & Governance Specification

---

### 1. Executive Summary & Security Philosophy

The CIT Campus Scheduling and Venue Management Platform is designed under the **Defense-in-Depth** and **Zero-Trust Backend Authorization** security paradigms. Security is enforced strictly at the database, service, and API gateway layers—never relying solely on client-side UI visibility or hidden navigation elements.

---

### 2. Authentication & Identity Management

#### 2.1 Password Hashing & Storage
- **Cryptographic Standard**: PBKDF2-HMAC-SHA256.
- **Work Factor**: $100,000$ iterations.
- **Salt Generation**: 16-byte cryptographically secure random salt generated via `secrets.token_hex(16)`.
- **Storage Format**: `salt$hash` stored in the `password_hash` column of the `users` table.
- **Exposure Control**: Password hashes and salts are strictly excluded from public user endpoints (`GET /api/auth/users`), response schemas, error logs, and frontend bundles.

#### 2.2 Brute-Force Rate Limiting & Account Lockout
- **Threshold**: 5 consecutive failed login attempts.
- **Action**: Immediate account lockout for a 15-minute cooldown window (`locked_until`).
- **HTTP Response**: `429 Too Many Requests` detailing the remaining lockout duration.
- **Success Behavior**: Any valid credential verification immediately resets `failed_login_attempts` to `0` and clears `locked_until`.
- **Audit Event**: Every lockout event logs an `ACCOUNT_LOCKED` security audit trail entry.

#### 2.3 Account Lifecycle & Status Controls
- **Activation Flag**: Boolean `is_active` column (default: `1`).
- **Deactivated Accounts**: Any login attempt on an account with `is_active = 0` is rejected with `403 Forbidden: Account is deactivated. Please contact the Campus System Administrator.`
- **Administrative Activation API**: `POST /api/auth/users/{user_id}/status` allows authorized Admins to activate/deactivate accounts.
- **Protected Accounts**: The Dean/Admin account cannot be deactivated (`400 Bad Request`).

#### 2.4 Session Management & Signed Bearer Tokens
- **Token Format**: URL-safe base64 payload signed with HMAC-SHA256 using the server-side `SECRET_KEY`.
- **Payload Claims**:
  - `sub`: User ID
  - `role`: Canonical role string
  - `email`: Authenticated institutional email
  - `iat`: Epoch issuance timestamp
  - `exp`: Epoch expiration timestamp (configurable, default 12 hours)
- **Signature Verification**: Verified using constant-time string comparison (`secrets.compare_digest`) to prevent timing side-channel attacks.
- **Expiration Check**: Expired tokens are rejected with `401 Unauthorized: Session expired. Please sign in again.`

---

### 3. Server-Side Role-Based Access Control (RBAC)

The platform enforces a strict 4-role hierarchy:

| Capability / API Operation | Admin (Dean) | Department Coordinator | Faculty Member | Club Representative | Student (Default) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Upload Institutional Dataset** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Validate Dataset Structure** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Reset Demo Database** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Run Master Timetable Solver** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Schedule Midsem Examinations** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Approve Disruption Proposals** | ✅ | ✅ (Dept Scope) | ❌ | ❌ | ❌ |
| **Approve Venue Bookings** | ✅ | ✅ (Dept Labs) | ❌ | ❌ | ❌ |
| **Submit Venue Bookings** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Report Timetable Disruption** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Self-Approve Own Request** | 🚫 **FORBIDDEN** | 🚫 **FORBIDDEN** | 🚫 **FORBIDDEN** | 🚫 **FORBIDDEN** | 🚫 **FORBIDDEN** |
| **Access Security Audit Logs** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Deactivate User Accounts** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Change Own Password** | ✅ | ✅ | ✅ | ✅ | ✅ |

---

### 4. Mandatory Access Control Rules

#### 4.1 Strict Self-Approval Ban (Rule H10)
- **Venue Bookings**:
  ```python
  if booking["created_by"] == user_id or str(booking["requester"]).lower() in str(user.get("name", "")).lower():
      raise HTTPException(
          status_code=403,
          detail="Policy Violation (H10): You cannot approve your own booking request. Approval requires independent authorization."
      )
  ```
- **Disruption Proposals**:
  Non-admin users cannot approve proposals they authored. Approvals must be signed off by an independent authority or Dean.

#### 4.2 Exclusive Single-Occupancy Dean Account
- The platform enforces an architectural limit of **exactly 1 Dean (Full Admin)** account in the entire institutional database.
- Any attempt to register an unauthorized second `admin` account is rejected with `403 Forbidden: The Dean / Full Admin role is exclusive and already occupied.`

---

### 5. API Hardening & HTTP Security Headers

The backend enforces standard HTTP security headers across every endpoint via `SecurityHeadersMiddleware`:

| Header | Configured Value | Security Purpose |
| :--- | :--- | :--- |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing attacks. |
| `X-Frame-Options` | `DENY` | Prevents clickjacking and framing vulnerabilities. |
| `X-XSS-Protection` | `1; mode=block` | Enables legacy browser reflective XSS filters. |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Protects sensitive path information in referrers. |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Enforces HTTPS on all modern browsers. |

---

### 6. AI Copilot Security & Safe Automation

- **Untrusted Input Handling**: All natural-language queries (English and Hinglish) are treated as untrusted user input.
- **Validation Gates**: The LLM is never permitted to authorize a booking, publish a schedule, or mutate database state directly.
- **Deterministic Code Verification**: Every booking request generated via the AI assistant must undergo deterministic validation (`BookingValidationEngine`) and requires manual user review before submission.
- **Prompt-Injection Defense**: User prompts are sanitized to prevent jailbreak or system-prompt extraction attempts.

---

### 7. Audit Logging & Compliance

All sensitive security and scheduling operations are recorded in the persistent `audit_logs` table:
- **Tracked Events**: `LOGIN_SUCCESS`, `LOGIN_FAILED`, `ACCOUNT_LOCKED`, `LOGIN_BLOCKED_INACTIVE`, `REGISTER`, `PASSWORD_CHANGED`, `ACCOUNT_STATUS_CHANGED`, `DATASET_IMPORT`, `DEMO_RESET`, `BOOKING_APPROVAL`, `DISRUPTION_APPROVAL`.
- **Stored Fields**: `user_id`, `user_role`, `action`, `details_json`, `timestamp` (ISO UTC).
- **Access Control**: Audit logs are accessible exclusively to authorized Administrators via `GET /api/auth/audit-logs`.

---

### 8. Automated Security Test Suite Verification

Automated security verification is maintained in [backend/tests/test_security_master.py](file:///d:/Python%20Projects/tools/IITBBSR/backend/tests/test_security_master.py):

```text
backend/tests/test_security_master.py::TestSecurityMaster::test_01_invalid_login_rejected PASSED
backend/tests/test_security_master.py::TestSecurityMaster::test_02_deactivated_account_blocked PASSED
backend/tests/test_security_master.py::TestSecurityMaster::test_03_login_rate_limiting_brute_force PASSED
backend/tests/test_security_master.py::TestSecurityMaster::test_04_successful_login_issues_token_and_resets_failures PASSED
backend/tests/test_security_master.py::TestSecurityMaster::test_05_token_signature_and_tamper_verification PASSED
backend/tests/test_security_master.py::TestSecurityMaster::test_06_password_change_verification PASSED
backend/tests/test_security_master.py::TestSecurityMaster::test_07_exclusive_admin_role_theft_prevented PASSED
backend/tests/test_security_master.py::TestSecurityMaster::test_08_faculty_cannot_upload_dataset_or_reset_demo PASSED
backend/tests/test_security_master.py::TestSecurityMaster::test_09_club_rep_cannot_approve_bookings_or_disruptions PASSED
backend/tests/test_security_master.py::TestSecurityMaster::test_10_self_approval_forbidden_for_venue_bookings PASSED
backend/tests/test_security_master.py::TestSecurityMaster::test_11_self_approval_forbidden_for_disruption_proposals PASSED
backend/tests/test_security_master.py::TestSecurityMaster::test_12_password_hashes_never_exposed_in_users_list PASSED
backend/tests/test_security_master.py::TestSecurityMaster::test_13_audit_logs_record_security_events PASSED
backend/tests/test_security_master.py::TestSecurityMaster::test_14_http_security_headers_present PASSED
======================================== 14 passed in 29.00s ========================================
```

---

### 9. Environment & Deployment Checklist

1. Configure `CIT_SECRET_KEY` in environment variables before production deployment.
2. Enable HTTPS termination at the reverse proxy or cloud gateway (e.g. Vercel / Nginx).
3. Ensure automated daily backups of `cit_campus.db` and exports directory.
4. Verify that `.env` is listed in `.gitignore` and `.vercelignore` to avoid credential leakage.
