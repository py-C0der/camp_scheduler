from __future__ import annotations

import json
from pathlib import Path
from backend.services.exam_service import ExamService
from backend.services.exam_validation_service import ExamValidationService
from backend.services.exam_export_service import ExamExportService
from CrunchWeek_StarterPack.validator import load, run as run_official_validator

DATA_PATH = Path("CrunchWeek_StarterPack/data/cit_public.json")
EXPORTS_PATH = Path("exports/schedule.json")


def test_full_examination_system():
    print("==================================================")
    print("  RUNNING MODULE 3: EXAMINATION SUITE TESTS")
    print("==================================================")

    service = ExamService()
    raw_data = service.data

    # 1. Dataset inspection
    exams_count = len(service.ctx.raw_exams)
    print(f"[TEST 1] Loaded dynamic exams count: {exams_count} (Expected: 41)")
    assert exams_count == 41, f"Expected 41 exams, got {exams_count}"

    # 2. Candidate generation & Pre-check diagnostics
    diag = service.get_diagnostics()
    print(f"[TEST 2] Structural Feasibility: {diag['is_feasible_structurally']}")
    print(f"         Total exam venues: {diag['eligible_venues']}")
    print(f"         Multi-room exams count: {diag['multi_room_exam_count']}")
    assert diag["is_feasible_structurally"] is True
    assert diag["eligible_venues"] == 19

    # 3. CP-SAT Solver Execution
    print("[TEST 3] Running CP-SAT Examination Solver...")
    solve_res = service.generate_schedule(time_limit_seconds=20, num_workers=4)
    print(f"         Solver Status: {solve_res['status']}")
    print(f"         Solve Time: {solve_res['solve_time_seconds']}s")
    print(f"         Soft Penalty: {solve_res['soft_penalty']}")
    assert solve_res["success"] is True
    assert solve_res["status"] in ("OPTIMAL", "FEASIBLE")
    assert solve_res["soft_penalty"] == 0, f"Expected 0 soft penalty, got {solve_res['soft_penalty']}"

    # 4. Independent Validation
    print("[TEST 4] Running Independent Exam Validation...")
    val_res = solve_res["validation"]
    print(f"         Validation Valid: {val_res['is_valid']}")
    print(f"         Hard Violations Count: {val_res['hard_violation_count']}")
    assert val_res["is_valid"] is True
    assert val_res["hard_violation_count"] == 0

    # 5. Versioning and Admin Approval
    version_id = solve_res["version_id"]
    print(f"[TEST 5] Testing Admin Approval for Version {version_id}...")
    app_res = service.approve_schedule(version_id, approved_by="Dean Academics", note="Module 3 Verified")
    print(f"         Approval Success: {app_res['success']}")
    assert app_res["success"] is True

    # 6. Pagination & Filtering
    print("[TEST 6] Testing Filter & Detail Queries...")
    list_res = service.get_exams(page=1, limit=10, day="MON", session="AM")
    print(f"         Found {len(list_res['items'])} exams on MON AM")
    detail_res = service.get_exam_detail("EX-MA101")
    assert detail_res is not None
    print(f"         EX-MA101 (size {detail_res['size']}): allocated rooms {detail_res['rooms']}")
    print(f"         Effective seats: {detail_res['total_effective_seats']} (is_multi_room={detail_res['is_multi_room']})")
    assert detail_res["total_effective_seats"] >= detail_res["size"]
    assert detail_res["is_multi_room"] is True

    # 7. Official Tournament Validator Verification
    print("[TEST 7] Running Official Tournament validator.py on exports/schedule.json...")
    official_data = load(str(DATA_PATH))
    sched_data = load(str(EXPORTS_PATH))
    report = run_official_validator(official_data, sched_data)
    print(f"         Hard Violations: {report['hard_violation_count']} {report['hard_by_rule']}")
    print(f"         Exam Soft Penalty: {report.get('exam_soft_penalty', 0)}")
    assert report["hard_violation_count"] == 0, f"Violations found: {report['hard_violations']}"
    assert report.get("exam_soft_penalty", 0) == 0

    print("==================================================")
    print("  ALL MODULE 3 EXAMINATION TESTS PASSED (100%)")
    print("==================================================")


if __name__ == "__main__":
    test_full_examination_system()
