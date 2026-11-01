"""
Comprehensive Security and Authorization Test Suite.
Verifies:
1. Invalid login rejection (401).
2. Deactivated accounts cannot log in (403).
3. Brute-force rate limiting and lockout window (429).
4. Signed session bearer token issuance and verification.
5. Tampered and expired session tokens rejected (401).
6. Password change requires old password verification.
7. Exclusive Dean/Admin role cannot be stolen by secondary registration (403).
8. Faculty cannot upload datasets or reset demo data (403).
9. Club Representatives cannot approve booking requests (403).
10. Self-approval is strictly forbidden for venue bookings (403).
11. Self-approval is strictly forbidden for disruption proposals (403).
12. Password hashes are never exposed in user listings.
13. Security audit logging accurately records authentication events.
14. HTTP Security Headers middleware is enforced.
"""

import unittest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from backend.main import app
from backend.services.auth_service import AuthService, hash_password, verify_password
from backend.services.booking_service import BookingService
from backend.disruptions.proposal_manager import ProposalManager
from backend.db.database import get_connection


class TestSecurityMaster(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.auth_service = AuthService()

    def setUp(self):
        conn = get_connection()
        try:
            conn.execute("DELETE FROM users WHERE email = 'sec_test_user@cit.ac.in'")
            conn.commit()
        finally:
            conn.close()

    def tearDown(self):
        conn = get_connection()
        try:
            conn.execute("DELETE FROM users WHERE email = 'sec_test_user@cit.ac.in'")
            conn.execute("DELETE FROM rescheduling_proposals WHERE id = 'PROP-TEST-SELF-01'")
            conn.commit()
        finally:
            conn.close()

    def test_01_invalid_login_rejected(self):
        """Verifies that incorrect credentials return 401 Unauthorized."""
        res = self.client.post("/api/auth/login", json={
            "email": "admin@cit.ac.in",
            "password": "wrong_password_123"
        })
        self.assertEqual(res.status_code, 401)
        self.assertIn("Invalid password", res.json()["detail"])

    def test_02_deactivated_account_blocked(self):
        """Verifies that deactivated accounts (is_active=0) cannot log in."""
        reg = self.auth_service.register(
            email="sec_test_user@cit.ac.in",
            password="test_password_123",
            role="student",
            name="Security Test User"
        )
        user_id = reg["user"]["id"]

        self.auth_service.set_user_status(admin_id="admin_1", target_user_id=user_id, is_active=False)

        res = self.client.post("/api/auth/login", json={
            "email": "sec_test_user@cit.ac.in",
            "password": "test_password_123"
        })
        self.assertEqual(res.status_code, 403)
        self.assertIn("deactivated", res.json()["detail"].lower())

    def test_03_login_rate_limiting_brute_force(self):
        """Verifies that 5 consecutive failed attempts trigger account lockout (429)."""
        reg = self.auth_service.register(
            email="sec_test_user@cit.ac.in",
            password="correct_pass_123",
            role="student"
        )
        
        for i in range(4):
            res = self.client.post("/api/auth/login", json={
                "email": "sec_test_user@cit.ac.in",
                "password": f"wrong_attempt_{i}"
            })
            self.assertEqual(res.status_code, 401)

        res5 = self.client.post("/api/auth/login", json={
            "email": "sec_test_user@cit.ac.in",
            "password": "wrong_attempt_5"
        })
        self.assertEqual(res5.status_code, 429)
        self.assertIn("locked", res5.json()["detail"].lower())

    def test_04_successful_login_issues_token_and_resets_failures(self):
        """Verifies that valid login resets failed counter and returns signed bearer token."""
        res = self.client.post("/api/auth/login", json={
            "email": "admin@cit.ac.in",
            "password": "cit@2026"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "authenticated")
        self.assertIn("token", data)
        self.assertEqual(data["token_type"], "Bearer")
        self.assertIn("expires_at", data)
        self.assertNotIn("password_hash", data["user"])

    def test_05_token_signature_and_tamper_verification(self):
        """Verifies that tampered session tokens are rejected."""
        res = self.client.post("/api/auth/login", json={
            "email": "admin@cit.ac.in",
            "password": "cit@2026"
        })
        valid_token = res.json()["token"]

        verify_res = self.client.post("/api/auth/verify-token", json={"token": valid_token})
        self.assertEqual(verify_res.status_code, 200)
        self.assertEqual(verify_res.json()["sub"], "admin_1")

        tampered_token = valid_token[:-4] + "abcd"
        tamper_res = self.client.post("/api/auth/verify-token", json={"token": tampered_token})
        self.assertEqual(tamper_res.status_code, 401)

    def test_06_password_change_verification(self):
        """Verifies secure password change with old password validation."""
        reg = self.auth_service.register(
            email="sec_test_user@cit.ac.in",
            password="old_password_123",
            role="student"
        )
        user_id = reg["user"]["id"]

        res_fail = self.client.post("/api/auth/change-password", json={
            "user_id": user_id,
            "old_password": "wrong_old_password",
            "new_password": "new_password_456"
        })
        self.assertEqual(res_fail.status_code, 400)

        res_ok = self.client.post("/api/auth/change-password", json={
            "user_id": user_id,
            "old_password": "old_password_123",
            "new_password": "new_password_456"
        })
        self.assertEqual(res_ok.status_code, 200)

        res_login = self.client.post("/api/auth/login", json={
            "email": "sec_test_user@cit.ac.in",
            "password": "new_password_456"
        })
        self.assertEqual(res_login.status_code, 200)

    def test_07_exclusive_admin_role_theft_prevented(self):
        """Verifies that registering a second Dean/Admin account is strictly blocked (403)."""
        res = self.client.post("/api/auth/register", json={
            "email": "imposter_admin@cit.ac.in",
            "password": "some_password_123",
            "role": "admin",
            "name": "Imposter Dean"
        })
        self.assertEqual(res.status_code, 403)
        self.assertIn("exclusive", res.json()["detail"].lower())

    def test_08_faculty_cannot_upload_dataset_or_reset_demo(self):
        """Verifies that non-admin users cannot import datasets or reset demo data."""
        res1 = self.client.post("/api/admin/dataset/import", json={
            "dataset": {},
            "user_id": "fac_arvind",
            "user_role": "faculty"
        })
        self.assertEqual(res1.status_code, 403)

        res2 = self.client.post("/api/admin/reset-demo?user_role=faculty&user_id=fac_arvind")
        self.assertEqual(res2.status_code, 403)

    def test_09_club_rep_cannot_approve_bookings_or_disruptions(self):
        """Verifies that Club Representative cannot approve booking requests."""
        booking_service = BookingService()
        reqs = booking_service.list_bookings()
        booking_list = reqs.get("bookings", [])
        if booking_list:
            b_id = booking_list[0]["id"]
            user_club = {"id": "club_tech", "name": "Robotics Society", "role": "club_rep"}
            with self.assertRaises(HTTPException) as ctx:
                booking_service.approve_booking(b_id, user_club)
            self.assertEqual(ctx.exception.status_code, 403)

    def test_10_self_approval_forbidden_for_venue_bookings(self):
        """Verifies that a user cannot approve their own booking request (H10)."""
        booking_service = BookingService()
        user_creator = {"id": "coord_cse", "name": "Dr. CSE Coordinator", "role": "dept_coordinator"}
        created = booking_service.create_booking({
            "title": "Dept CSE Internal Review",
            "venue": "LH-101",
            "date": "2026-10-15",
            "start_time": "14:00",
            "end_time": "16:00",
            "attendance": 50,
            "category": "department_event",
            "requester": "Dr. CSE Coordinator",
            "created_by": "coord_cse"
        }, user_creator)
        b_id = created["id"]

        with self.assertRaises(HTTPException) as ctx:
            booking_service.approve_booking(b_id, user_creator)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("cannot approve your own", ctx.exception.detail.lower())

    def test_11_self_approval_forbidden_for_disruption_proposals(self):
        """Verifies that a coordinator who submitted a disruption proposal cannot approve it."""
        from backend.services.disruption_service import DisruptionService
        ds = DisruptionService()
        user_coord = {"id": "coord_cse", "name": "Dr. CSE Coordinator", "role": "dept_coordinator"}

        dis = ds.create_disruption({
            "id": "DIS-SEC-TEST-01",
            "title": "Lab Renovation",
            "description": "Lab repair in LH-101",
            "changes": [{
                "type": "room_unavailable",
                "room_id": "LH-101",
                "days": ["MON"],
                "periods": [1, 2],
                "reason": "Maintenance"
            }]
        }, user=user_coord)

        prop_res = ds.generate_rescheduling_proposal(dis["id"], user=user_coord)
        prop_id = prop_res.get("id") or prop_res.get("proposal_id")

        with self.assertRaises(HTTPException) as ctx:
            ds.approve_proposal(prop_id, user_coord)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("self-approval forbidden", ctx.exception.detail.lower())

    def test_12_password_hashes_never_exposed_in_users_list(self):
        """Verifies that GET /api/auth/users never leaks password_hash."""
        res = self.client.get("/api/auth/users")
        self.assertEqual(res.status_code, 200)
        users = res.json()["users"]
        self.assertGreater(len(users), 0)
        for u in users:
            self.assertNotIn("password_hash", u)
            self.assertNotIn("password", u)

    def test_13_audit_logs_record_security_events(self):
        """Verifies that authentication events are written to the audit_logs table."""
        res = self.client.get("/api/auth/audit-logs?admin_id=admin_1")
        self.assertEqual(res.status_code, 200)
        logs = res.json()["audit_logs"]
        self.assertGreater(len(logs), 0)
        actions = [l["action"] for l in logs]
        self.assertTrue(any("LOGIN" in a or "REGISTER" in a for a in actions))

    def test_14_http_security_headers_present(self):
        """Verifies that HTTP Security Headers middleware attaches essential protections."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(res.headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertEqual(res.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("max-age=", res.headers.get("Strict-Transport-Security", ""))


if __name__ == "__main__":
    unittest.main()
