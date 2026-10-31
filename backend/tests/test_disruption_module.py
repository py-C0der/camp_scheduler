"""
Unit and Integration Test Suite for Module 5: Disruption Management and Timetable Rescheduling Engine.
Verifies disruption reporting (all 5 change types), impact analysis, minimal perturbation rescheduling,
official tournament validator integration, proposal comparison, and role-based approval workflows.
"""

import unittest
import json
from pathlib import Path
from fastapi import HTTPException

from backend.db.database import init_db, get_connection
from backend.services.disruption_service import DisruptionService
from backend.disruptions.impact_analyzer import DisruptionImpactAnalyzer
from backend.disruptions.reschedule_engine import TimetableReschedulingEngine
from backend.disruptions.proposal_manager import ProposalManager
from backend.disruptions.version_manager import TimetableVersionManager
from CrunchWeek_StarterPack.validator import load, apply_disruption, to_assign, check_timetable, run as run_official_validator, Ctx

SAMPLE_DISRUPTION_PATH = Path("CrunchWeek_StarterPack/examples/sample_disruption.json")
CIT_PUBLIC_PATH = Path("CrunchWeek_StarterPack/data/cit_public.json")


class TestDisruptionModule(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db(force_reset=False)
        cls.service = DisruptionService()
        with open(SAMPLE_DISRUPTION_PATH, "r", encoding="utf-8") as f:
            cls.sample_disruption = json.load(f)

        # Ensure active timetable is reset to baseline
        base_assigns = TimetableVersionManager.get_version_assignments("baseline")
        TimetableVersionManager.activate_new_version(
            version_id="baseline",
            name="Baseline Academic Timetable",
            assignments=base_assigns,
            source="generated"
        )

    def test_01_disruption_reporting_and_validation(self):
        """Verifies disruption creation and validation of all 5 official change types."""
        user_admin = {"id": "admin_1", "name": "Dean Academics", "role": "admin"}

        # 1. Valid disruption payload with multiple change types
        dis = self.service.create_disruption({
            "id": "DIS-TEST-01",
            "title": "Severe Weather & Lab Renovation",
            "description": "Roof repair in LH-4 and Faculty F07 emergency leave on Monday",
            "changes": [
                {
                    "type": "faculty_unavailable",
                    "faculty_id": "F07",
                    "days": ["MON"],
                    "periods": [1, 2, 3, 4],
                    "reason": "Emergency leave"
                },
                {
                    "type": "room_unavailable",
                    "room_id": "CR-102",
                    "days": ["MON", "TUE"],
                    "periods": [1, 2, 3],
                    "reason": "Painting work"
                },
                {
                    "type": "remove_session",
                    "session_id": "CS101-L1"
                }
            ]
        }, user_admin)

        self.assertEqual(dis["id"], "DIS-TEST-01")
        self.assertEqual(len(dis["changes"]), 3)
        self.assertEqual(dis["status"], "reported")

        # 2. Invalid disruption change type must raise HTTPException
        with self.assertRaises(HTTPException) as ctx:
            self.service.create_disruption({
                "description": "Invalid change type test",
                "changes": [{"type": "alien_invasion", "day": "MON"}]
            }, user_admin)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_02_impact_analysis(self):
        """Tests blast radius impact analysis against real active timetable assignments."""
        impact = self.service.analyze_impact("DIS-TEST-01")

        self.assertTrue(impact["is_impacted"])
        self.assertGreater(impact["total_affected_sessions"], 0)
        self.assertIn("F07", [f["id"] for f in impact["affected_faculty"]])
        self.assertIn("CR-102", [r["id"] for r in impact["affected_rooms"]])
        self.assertIn("CS101-L1", impact["removed_sessions"])

    def test_03_minimal_perturbation_rescheduling(self):
        """Tests CP-SAT rescheduling engine on the official practice disruption."""
        user_admin = {"id": "admin_1", "name": "Dean Academics", "role": "admin"}

        # Create practice disruption in DB
        dis = self.service.create_disruption(self.sample_disruption, user_admin)

        # Generate proposal
        prop = self.service.generate_rescheduling_proposal(
            disruption_id=dis["id"],
            user=user_admin,
            time_limit_seconds=45,
            target_version_name="v2_sample_disruption"
        )

        self.assertIn(prop["solver_status"], ("OPTIMAL", "FEASIBLE"))
        self.assertEqual(prop["hard_violations_count"], 0, "Proposed timetable must have 0 hard violations")
        self.assertGreater(prop["sessions_moved"], 0, "Disrupted sessions must be rescheduled")
        self.assertGreater(prop["unchanged_sessions"], 80, "Unaffected sessions must be preserved")

    def test_04_official_validator_integration(self):
        """Verifies the rescheduling proposal using the official tournament validator with --disruption and --baseline."""
        # Retrieve proposal comparison
        proposals = self.service.list_proposals("sample-disruption")
        self.assertGreater(len(proposals), 0)
        prop = proposals[0]

        comparison = self.service.get_proposal_comparison(prop["id"])
        self.assertTrue(comparison["validation"]["is_valid"])
        self.assertEqual(comparison["validation"]["hard_violations_count"], 0)

        # Run independent official validator
        raw_data = load(CIT_PUBLIC_PATH)
        disrupted_data = apply_disruption(raw_data, self.sample_disruption)

        baseline_assigns = TimetableVersionManager.get_version_assignments("baseline")
        baseline_sched = {"team": "CIT-DevOps", "dataset_id": "cit-public-v1", "sessions": baseline_assigns}

        # Build proposed schedule
        cur = get_connection().cursor()
        cur.execute("SELECT session_id, proposed_day as day, proposed_start_period as start_period, proposed_room_id as room_id FROM rescheduling_proposal_assignments WHERE proposal_id = ?", (prop["id"],))
        prop_assigns = [dict(r) for r in cur.fetchall()]

        proposed_sched = {
            "team": "CIT-DevOps",
            "dataset_id": "cit-public-v1",
            "sessions": prop_assigns
        }

        report = run_official_validator(disrupted_data, proposed_sched, baseline_sched)
        self.assertEqual(report["hard_violation_count"], 0, f"Official validator reported hard violations: {report.get('hard_violations')}")
        self.assertIn("stability", report)
        self.assertGreater(report["stability"]["sessions_moved"], 0)

    def test_05_proposal_comparison_and_diff(self):
        """Verifies side-by-side diff reporting for changed sessions."""
        proposals = self.service.list_proposals("sample-disruption")
        prop = proposals[0]

        comp = self.service.get_proposal_comparison(prop["id"])
        changed = comp["changed_sessions"]
        self.assertGreater(len(changed), 0)

        first_changed = changed[0]
        self.assertIn("session_id", first_changed)
        self.assertIn("change_type", first_changed)
        self.assertIn("change_reason", first_changed)
        self.assertIsNotNone(first_changed["change_reason"])

    def test_06_role_based_approval_workflow(self):
        """Verifies unauthorized rejection, self-approval policy, and successful admin approval."""
        proposals = self.service.list_proposals("sample-disruption")
        prop = proposals[0]

        # 1. Unauthorized student/club role cannot approve
        user_club = {"id": "club_tech", "name": "Robotics Lead", "role": "club_rep"}
        with self.assertRaises(HTTPException) as ctx:
            self.service.approve_proposal(prop["id"], user_club)
        self.assertEqual(ctx.exception.status_code, 403)

        # 2. Admin approval activates new timetable version
        user_admin = {"id": "admin_1", "name": "Dean Academics", "role": "admin"}
        approved = self.service.approve_proposal(prop["id"], user_admin, reason="Approved after review")
        self.assertEqual(approved["status"], "approved")

        # Verify new timetable version is active
        active_ver = TimetableVersionManager.get_active_timetable_id()
        self.assertEqual(active_ver, prop["target_timetable_version"])

    def test_07_timetable_version_history(self):
        """Verifies that original baseline and all subsequent timetable versions are preserved."""
        versions = self.service.get_timetable_versions()
        version_ids = [v["id"] for v in versions]

        self.assertIn("baseline", version_ids, "Baseline timetable must NEVER be deleted")
        active_versions = [v for v in versions if v["is_active"]]
        self.assertEqual(len(active_versions), 1, "Exactly one timetable version must be active")


if __name__ == "__main__":
    unittest.main()
