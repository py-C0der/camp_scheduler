import unittest
import json
from pathlib import Path
from backend.db.database import get_connection
from backend.services.validation_service import audit_all_constraints
from backend.services.exam_service import ExamService
from backend.services.booking_service import BookingService
from backend.services.disruption_service import DisruptionService
from backend.services.decision_evidence_service import DecisionEvidenceService
from backend.ai.assistant import AIAssistantService
from backend.notifications.notification_service import NotificationService
from backend.schemas.ai_schemas import AIChatRequest
from CrunchWeek_StarterPack.validator import load, run as run_validator

DATA_PATH = Path("CrunchWeek_StarterPack/data/cit_public.json")
EXPORTS_PATH = Path("exports/schedule.json")


class TestModule9SystemIntegrationE2E(unittest.TestCase):
    """
    Module 9: Final System Integration, End-to-End Testing & Official Validation.
    Verifies that Modules 1 through 8 integrate seamlessly as a single unified campus scheduling platform.
    """

    @classmethod
    def setUpClass(cls):
        from backend.services.dataset_service import DatasetService
        DatasetService.reset_demo_data(user_id="admin_1")

    def setUp(self):
        self.evidence = DecisionEvidenceService()
        self.ai = AIAssistantService()

    # 1. Dataset & Database Integrity
    def test_01_database_single_source_of_truth(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM rooms")
        rooms_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM faculty")
        fac_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM sessions")
        sess_count = cur.fetchone()[0]
        conn.close()

        self.assertEqual(rooms_count, 27, "Must contain exactly 27 campus venues")
        self.assertEqual(fac_count, 40, "Must contain exactly 40 faculty members")
        self.assertGreaterEqual(sess_count, 189, "Must contain at least 189 teaching sessions")

    # 2. Teaching Timetable Constraint Validation
    def test_02_teaching_timetable_validation(self):
        audit = audit_all_constraints()
        self.assertEqual(audit.get("status"), "success")
        self.assertEqual(audit["summary"]["hard_violations_count"], 0, "Zero hard violations required")
        self.assertEqual(audit["summary"]["overall_academic_status"], "FULLY COMPLIANT")

    # 3. Examination Scheduling & Capacity
    def test_03_examination_scheduling_integrity(self):
        service = ExamService()
        diag = service.get_diagnostics()
        self.assertTrue(diag["is_feasible_structurally"])
        self.assertEqual(diag["eligible_venues"], 19)
        self.assertEqual(len(service.ctx.raw_exams), 41)

    # 4. Venue Booking Priority & Arbitration
    def test_04_venue_booking_priority(self):
        service = BookingService()
        service.initialize_and_sync()
        summary = service.get_summary()
        self.assertGreater(summary.get("total_requests", 0), 0)
        self.assertGreater(summary.get("approved_requests", 0), 0)
        self.assertGreater(summary.get("booking_score", 0), 0)

    # 5. Disruption Rescheduling Engine
    def test_05_disruption_rescheduling_workflow(self):
        service = DisruptionService()
        summary = service.get_dashboard_summary()
        self.assertIn("total_disruptions", summary)
        versions = service.get_timetable_versions()
        self.assertGreaterEqual(len(versions), 1)

    # 6. Notification Hub
    def test_06_notification_delivery_logging(self):
        service = NotificationService()
        notifs = service.get_user_notifications("admin_1")
        self.assertGreaterEqual(notifs.total, 0)
        self.assertIsInstance(notifs.notifications, list)

    # 7. AI Assistant Bilingual Integration
    def test_07_ai_assistant_bilingual_workflow(self):
        user = {"id": "F01", "role": "faculty", "name": "Dr. Arvind Rao"}
        # English
        res_en = self.ai.process_chat(AIChatRequest(message="Move my Monday 10 AM class to Tuesday morning."), user)
        self.assertEqual(res_en.intent, "schedule_change")

        # Hinglish
        res_hi = self.ai.process_chat(AIChatRequest(message="Wednesday ko meri availability nahi hai."), user)
        self.assertEqual(res_hi.intent, "schedule_change")

    # 8. Decision Explainability
    def test_08_grounded_decision_explainability(self):
        ev = self.evidence.explain_timetable_slot("CS301-L2")
        self.assertIn("rules_involved", ev)
        self.assertIn("H1", ev["rules_involved"])

    # 9. Official Tournament Validator
    def test_09_official_tournament_validator_execution(self):
        self.assertTrue(EXPORTS_PATH.exists(), "exports/schedule.json must exist")
        data = load(str(DATA_PATH))
        with open(EXPORTS_PATH, "r", encoding="utf-8") as f:
            sched = json.load(f)
        report = run_validator(data, sched)
        self.assertEqual(len(report["hard_violations"]), 0, f"Validator found hard violations: {report['hard_violations']}")


if __name__ == "__main__":
    unittest.main()
