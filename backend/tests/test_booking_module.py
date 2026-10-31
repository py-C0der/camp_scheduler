"""
Unit and Integration Test Suite for Module 4: Smart Venue Booking and Approval Management System.
Verifies all 25 Spectra-week booking requests, English & Hinglish parsing,
deterministic priority ranking, availability collision checks, self-approval prevention,
and official tournament validation.
"""

import unittest
import json
from pathlib import Path
from fastapi import HTTPException

from backend.db.database import init_db, get_connection
from backend.bookings.ingestion import BookingIngestionService
from backend.bookings.priority import BookingPriorityManager, DEFAULT_PRIORITY_ORDER
from backend.bookings.availability import VenueAvailabilityEngine
from backend.bookings.validation import BookingValidationEngine
from backend.bookings.alternatives import BookingAlternativeEngine
from backend.bookings.decision_engine import BookingDecisionEngine
from backend.bookings.cancellation import BookingCancellationService
from backend.bookings.normalizer import BookingNormalizer
from backend.services.booking_service import BookingService
from backend.services.booking_export_service import BookingExportService
from backend.ai.booking_extractor import NaturalLanguageBookingExtractor
from backend.ai.conversation import BookingClarificationAssistant
from CrunchWeek_StarterPack.validator import load, check_bookings, Ctx


class TestBookingModule(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from backend.services.dataset_service import DatasetService
        DatasetService.reset_demo_data(user_id="admin_1")
        cls.service = BookingService()
        cls.service.initialize_and_sync()

    def test_01_dataset_ingestion(self):
        """Verifies all 25 requests and 1 cancellation (BR-04) load dynamically."""
        reqs = self.service.ingestion_service.get_all_booking_requests()
        cancellations = self.service.ingestion_service.get_cancellations()

        self.assertEqual(len(reqs), 25, "Must load all 25 booking requests dynamically")
        self.assertEqual(len(cancellations), 1, "Must load 1 cancellation dynamically")
        self.assertEqual(cancellations[0]["request_id"], "BR-04")
        self.assertEqual(cancellations[0]["by"], "Robotics Club")

    def test_02_english_and_hinglish_extraction(self):
        """Tests natural-language parsing for English and Hinglish phrases."""
        # 1. English request
        text_en = "Need auditorium for robotics competition on Friday from 10 AM to 1 PM for around 200 students."
        parsed_en = NaturalLanguageBookingExtractor.extract_fields(text_en, user_role="club")
        self.assertEqual(parsed_en["detected_day"], "FRI")
        self.assertIn("auditorium", parsed_en["room_types"])
        self.assertEqual(parsed_en["attendance"], 200)

        # 2. Hinglish request
        text_hi = "Kal afternoon ek seminar hall chahiye, guest lecture ke liye, around 80 students."
        parsed_hi = NaturalLanguageBookingExtractor.extract_fields(text_hi, user_role="faculty")
        self.assertIn("seminar_hall", parsed_hi["room_types"])
        self.assertEqual(parsed_hi["attendance"], 80)
        self.assertEqual(parsed_hi["requested_category"], "guest_lecture")

        # 3. Lab request
        text_lab = "Computer lab book karna hai for coding hackathon, Saturday morning, 60 participants."
        parsed_lab = NaturalLanguageBookingExtractor.extract_fields(text_lab, user_role="club")
        self.assertEqual(parsed_lab["detected_day"], "SAT")
        self.assertIn("lab_cs", parsed_lab["room_types"])
        self.assertEqual(parsed_lab["attendance"], 60)

    def test_03_conversation_clarification_and_contradictions(self):
        """Verifies detection of missing fields and contradictory inputs."""
        incomplete_text = "I need a hall for an event."
        extracted = NaturalLanguageBookingExtractor.extract_fields(incomplete_text)
        analysis = BookingClarificationAssistant.analyze_booking_draft(extracted, incomplete_text)

        self.assertFalse(analysis["is_complete"])
        self.assertIn("day", analysis["missing_fields"])
        self.assertGreater(len(analysis["clarification_questions"]), 0)

        # Contradiction test: start period after end period
        contradictory_extracted = dict(extracted)
        contradictory_extracted["windows"] = [{"day": "MON", "from_period": 8, "to_period": 4}]
        analysis_contra = BookingClarificationAssistant.analyze_booking_draft(contradictory_extracted, "test")
        self.assertGreater(len(analysis_contra["contradictions"]), 0)

    def test_04_priority_hierarchy_and_role_caps(self):
        """Verifies role category capping and tie-breaking outranking."""
        pm = BookingPriorityManager()

        # Club role requesting institute_event must be capped to club_event
        club_req = {
            "id": "R1",
            "role": "club",
            "requested_category": "institute_event",
            "submitted_at": "2027-01-20T10:00:00"
        }
        eff = pm.get_effective_category(club_req)
        self.assertEqual(eff, "club_event", "Club cannot escalate to institute_event")

        # Admin requesting institute_event
        admin_req = {
            "id": "R2",
            "role": "admin",
            "requested_category": "institute_event",
            "submitted_at": "2027-01-20T11:00:00"
        }
        eff_admin = pm.get_effective_category(admin_req)
        self.assertEqual(eff_admin, "institute_event")

        # Admin request outranks club request
        self.assertTrue(pm.outranks(admin_req, club_req))

    def test_05_room_availability_and_conflict_detection(self):
        """Tests collision detection against maintenance periods and classes."""
        avail = self.service.availability_engine

        # Test room maintenance downtime
        # From public dataset: LH-4 on THU has maintenance (periods 1..9)
        chk = avail.check_room_availability("LH-4", "THU", 4, 2)
        self.assertFalse(chk["available"], "LH-4 must be unavailable during scheduled maintenance")

    def test_06_self_approval_prevention(self):
        """Enforces H10: No user may approve their own booking request."""
        # Create a booking as fac_arvind
        user_arvind = {"id": "fac_arvind", "name": "Prof. Arvind Rao", "role": "faculty", "department": "CSE"}
        booking = self.service.create_booking({
            "title": "Faculty Department Seminar",
            "requested_category": "department_event",
            "attendance": 30,
            "duration_periods": 1,
            "room_types": ["classroom"],
            "windows": [{"day": "MON", "from_period": 2, "to_period": 3}]
        }, user_arvind)

        # Arvind tries to approve his own request
        with self.assertRaises(HTTPException) as ctx:
            self.service.approve_booking(booking["id"], user_arvind)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("own booking request", ctx.exception.detail)

    def test_07_spectra_week_batch_resolution(self):
        """Runs the deterministic decision engine and verifies 0 hard violations and 0 priority inversions."""
        result = self.service.decide_all_spectra_bookings()

        self.assertGreater(result["stats"]["approved"], 0)
        self.assertEqual(len(result["priority_inversions"]), 0, "Must have 0 priority inversions")

        # Check export files exist
        export_file = Path("exports/schedule.json")
        self.assertTrue(export_file.exists())

        # Validate with official tournament validator
        ctx = Ctx(self.service.dataset)
        with open(export_file, "r", encoding="utf-8") as f:
            sched = json.load(f)

        base_assign = {s["session_id"]: (s["day"], s["start_period"], s["room_id"]) for s in sched.get("sessions", [])}
        V, W, stats = check_bookings(ctx, base_assign, sched["fest_week"])
        self.assertEqual(len(V), 0, f"Validator found hard violations: {V}")
        self.assertEqual(len(stats["priority_inversions"]), 0, "Validator found priority inversions")
        self.assertGreater(stats["booking_score"], 50.0, f"Expected high booking score, got {stats['booking_score']}")


if __name__ == "__main__":
    unittest.main()
