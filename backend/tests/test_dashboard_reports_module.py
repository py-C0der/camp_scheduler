"""
Unit and Integration Test Suite for Module 7:
CIT Campus Admin Dashboard, Reports, Timetable Views & Dataset Management.

Covers:
1. Dashboard Summary 7 KPIs matching authoritative DB state
2. Student Group 3-mode weekly timetable grid & free period detection
3. Faculty weekly timetable grid with unavailability & <=4h daily load checks
4. Room weekly timetable distinguishing teaching sessions, event bookings, and maintenance
5. Unified Pending Approvals hub (combining bookings + disruption proposals)
6. Conflict Monitor constraint violation checks & empty-state accuracy
7. Room Utilisation report using exact formula: (Occupied / (45 - Unavailable)) * 100
8. Dataset structure & foreign-key relational validation
9. Transactional dataset import with failure rollback
10. Safe demo data baseline reset
11. Official tournament validator execution on exported schedule
"""

import unittest
import json
from pathlib import Path

from backend.db.database import get_connection, init_db
from backend.services.dataset_service import DatasetService
from backend.api.dashboard_routes import (
    get_dashboard_summary,
    get_group_timetable,
    get_faculty_timetable,
    get_room_timetable,
    get_pending_approvals,
    get_conflicts_monitor,
    get_room_utilisation_report,
    get_dataset_info,
    run_validator_api
)

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "CrunchWeek_StarterPack" / "data" / "cit_public.json"
EXPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "exports"


class TestDashboardReportsModule(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ensure clean demo state is seeded and active
        DatasetService.reset_demo_data(user_id="admin_1")

    def test_01_dashboard_summary_7_kpis(self):
        """Verifies the 7 core dashboard summary KPIs match actual DB counts."""
        res = get_dashboard_summary()
        self.assertIn("kpis", res)
        kpis = res["kpis"]

        # 1. Total scheduled teaching sessions
        self.assertIn("scheduled_teaching_sessions", kpis)
        self.assertGreaterEqual(kpis["scheduled_teaching_sessions"], 189)

        # 2. Total scheduled examinations
        self.assertIn("scheduled_examinations", kpis)
        self.assertEqual(kpis["scheduled_examinations"], 41)

        # 3. Total active venue bookings
        self.assertIn("active_venue_bookings", kpis)
        self.assertGreaterEqual(kpis["active_venue_bookings"], 20)

        # 4. Pending approvals
        self.assertIn("pending_approvals", kpis)
        self.assertIsInstance(kpis["pending_approvals"], int)

        # 5. Current unresolved conflicts
        self.assertIn("unresolved_conflicts", kpis)
        self.assertEqual(kpis["unresolved_conflicts"], 0)

        # 6. Total available rooms
        self.assertIn("total_available_rooms", kpis)
        self.assertEqual(kpis["total_available_rooms"], 27)

        # 7. Room utilisation summary
        self.assertIn("room_utilisation_summary", kpis)
        util_summary = kpis["room_utilisation_summary"]
        self.assertIn("average_percentage", util_summary)
        self.assertGreater(util_summary["average_percentage"], 0.0)
        self.assertLessEqual(util_summary["average_percentage"], 100.0)

    def test_02_group_timetable_view_and_free_periods(self):
        """Verifies Student Group timetable grid (MON-FRI, P1-P9), free periods, and session kinds."""
        res = get_group_timetable("Y1-A")
        self.assertEqual(res["view_mode"], "student_group")
        self.assertEqual(res["group"]["id"], "Y1-A")

        grid = res["grid"]
        for day in ["MON", "TUE", "WED", "THU", "FRI"]:
            self.assertIn(day, grid)
            self.assertEqual(len(grid[day]), 9)

            for period_cell in grid[day]:
                self.assertIn("is_free", period_cell)
                if period_cell["is_free"]:
                    self.assertEqual(period_cell["kind"], "free")
                else:
                    self.assertIn("course_id", period_cell)
                    self.assertIn("room_id", period_cell)
                    self.assertIn("faculty_name", period_cell)
                    self.assertIn(period_cell["kind"], ["lecture", "tutorial", "lab"])

        stats = res["weekly_stats"]
        self.assertTrue(stats["max_daily_met"])
        self.assertGreater(stats["total_teaching_periods"], 0)
        self.assertGreater(stats["total_free_periods"], 0)

    def test_03_faculty_timetable_view_and_load(self):
        """Verifies Faculty weekly timetable, daily load compliance, and unavailable slots."""
        res = get_faculty_timetable("F01")
        self.assertEqual(res["view_mode"], "faculty")
        self.assertEqual(res["faculty"]["id"], "F01")

        grid = res["grid"]
        for day in ["MON", "TUE", "WED", "THU", "FRI"]:
            self.assertEqual(len(grid[day]), 9)

        stats = res["weekly_stats"]
        self.assertTrue(stats["max_daily_met"])
        for day, hours in stats["daily_teaching_hours"].items():
            self.assertLessEqual(hours, 4, f"Faculty daily teaching hours exceeded on {day}")

    def test_04_room_timetable_view_and_usage(self):
        """Verifies Room weekly grid distinguishing teaching sessions vs event bookings."""
        res = get_room_timetable("LH-1")
        self.assertEqual(res["view_mode"], "room")
        self.assertEqual(res["room"]["id"], "LH-1")

        grid = res["grid"]
        has_teaching = False
        for day in ["MON", "TUE", "WED", "THU", "FRI"]:
            self.assertEqual(len(grid[day]), 9)
            for cell in grid[day]:
                if cell.get("item_type") == "teaching_session":
                    has_teaching = True

        self.assertTrue(has_teaching, "LH-1 should host scheduled teaching sessions.")
        stats = res["weekly_stats"]
        self.assertEqual(stats["total_slots"], 45)
        self.assertGreater(stats["utilisation_percentage"], 0.0)

    def test_05_pending_approvals_hub(self):
        """Verifies unified Pending Approvals list combining venue bookings and disruption proposals."""
        res = get_pending_approvals(user_role="admin", user_id="admin_1")
        self.assertIn("total_pending", res)
        self.assertIn("pending_items", res)

        for item in res["pending_items"]:
            self.assertIn("request_id", item)
            self.assertIn("request_type", item)
            self.assertIn("requester", item)
            self.assertIn("target_venue_or_schedule", item)
            self.assertIn("current_status", item)
            self.assertIn("approval_responsibility", item)
            self.assertIn("can_current_user_approve", item)

    def test_06_conflict_monitor(self):
        """Verifies Conflict Monitor retrieves authoritative validation state with 0 baseline conflicts."""
        res = get_conflicts_monitor()
        self.assertTrue(res["verified"])
        self.assertEqual(res["unresolved_count"], 0)
        self.assertEqual(len(res["conflicts"]), 0)
        self.assertIn("0 conflicts", res["status_message"])

    def test_07_room_utilisation_formula(self):
        """Verifies room utilisation formula: Util% = (Occupied / (45 - Unavailable)) * 100."""
        report = get_room_utilisation_report()
        self.assertIn("institution_average_utilization", report)
        self.assertIn("rooms", report)
        self.assertEqual(report["total_rooms"], 27)

        for r in report["rooms"]:
            avail = r["available_periods"]
            unavail = r["unavailable_periods"]
            occupied = r["total_occupied_periods"]
            pct = r["utilization_percentage"]

            self.assertEqual(avail + unavail, 45)
            self.assertEqual(occupied, r["scheduled_teaching_periods"] + r["scheduled_event_periods"])
            expected_pct = round((occupied / avail) * 100, 1)
            self.assertEqual(pct, expected_pct, f"Utilisation mismatch for room {r['room_id']}")
            self.assertIn(r["status"], ["high", "optimal", "low"])

    def test_08_dataset_validation_structural_and_relational(self):
        """Tests DatasetService structural and foreign-key relational validation."""
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            valid_data = json.load(f)

        # 1. Valid dataset
        val_result = DatasetService.validate_dataset_structure(valid_data)
        self.assertTrue(val_result["is_valid"])
        self.assertEqual(len(val_result["errors"]), 0)

        # 2. Corrupt dataset missing required rooms key
        corrupted = dict(valid_data)
        del corrupted["rooms"]
        res_corrupt = DatasetService.validate_dataset_structure(corrupted)
        self.assertFalse(res_corrupt["is_valid"])
        self.assertTrue(any("rooms" in e for e in res_corrupt["errors"]))

        # 3. Corrupt foreign key reference in sessions
        bad_ref = json.loads(json.dumps(valid_data))
        bad_ref["sessions"][0]["faculty_id"] = "NON_EXISTENT_FACULTY_999"
        res_bad_ref = DatasetService.validate_dataset_structure(bad_ref)
        self.assertFalse(res_bad_ref["is_valid"])
        self.assertTrue(any("NON_EXISTENT_FACULTY_999" in e for e in res_bad_ref["errors"]))

    def test_09_dataset_import_transactional_rollback(self):
        """Tests that importing invalid dataset rolls back completely without partial commit."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM rooms")
        rooms_before = cur.fetchone()[0]
        conn.close()

        invalid_data = {
            "dataset_id": "invalid-dataset",
            "rooms": [{"id": "R1", "capacity": -10}], # negative capacity error
            "faculty": [],
            "student_groups": [],
            "courses": [],
            "sessions": []
        }

        res = DatasetService.import_dataset(invalid_data, user_id="admin_1")
        self.assertFalse(res["success"])

        # Verify DB remained untouched
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM rooms")
        rooms_after = cur.fetchone()[0]
        conn.close()
        self.assertEqual(rooms_before, rooms_after)

    def test_10_dataset_demo_reset(self):
        """Tests clean demo baseline reset restores official starter pack dataset."""
        res = DatasetService.reset_demo_data(user_id="admin_1")
        self.assertTrue(res["success"])
        self.assertEqual(res["dataset_id"], "cit-public-v1")

        info = get_dataset_info()
        self.assertEqual(info["counts"]["rooms"], 27)
        self.assertEqual(info["counts"]["faculty"], 40)
        self.assertEqual(info["counts"]["student_groups"], 14)

    def test_11_official_validator_runner(self):
        """Verifies official tournament validator execution on exports/schedule.json."""
        res = run_validator_api()
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["returncode"], 0)
        self.assertTrue(res["is_valid"])
        self.assertIn("Hard violations: 0", res["stdout"])
        self.assertIn("cit-public-v1", res["stdout"])


if __name__ == "__main__":
    unittest.main()
