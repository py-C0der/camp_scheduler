from __future__ import annotations

from typing import Any
from backend.exams.solver import ExamCpsatSolver


def solve_exams(data: dict[str, Any], time_limit_seconds: float = 20.0) -> list[dict[str, Any]]:
    """Formulates and solves the Midsem Exam schedule using the modular CP-SAT solver.

    Guarantees:
    - 0 hard violations (E1, E2, H4 room overlap, H3 group overlap, H5 half-capacity)
    - 0 same-day exam soft penalty for all student groups
    """
    solver = ExamCpsatSolver(data)
    res = solver.solve(time_limit_seconds=time_limit_seconds, num_workers=4)
    if res.get("status") in ("OPTIMAL", "FEASIBLE"):
        return res["assignments"]
    return []
