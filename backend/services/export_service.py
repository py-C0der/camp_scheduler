import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from backend.db.database import get_connection

EXPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "exports"
STARTER_PACK = Path(__file__).resolve().parent.parent.parent / "CrunchWeek_StarterPack"

def export_schedules(baseline_sched: Dict[str, Any], after_sched: Optional[Dict[str, Any]] = None):
    """
    Exports schedule.json and optionally schedule_after.json into the required exports/ directory.
    Validates them using the official validator.py.
    """
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    baseline_path = EXPORTS_DIR / "schedule.json"
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(baseline_sched, f, indent=2)
        
    after_path = None
    if after_sched:
        after_path = EXPORTS_DIR / "schedule_after.json"
        with open(after_path, "w", encoding="utf-8") as f:
            json.dump(after_sched, f, indent=2)
            
    print(f"Exported schedule files to {EXPORTS_DIR}")
    return {
        "schedule_path": str(baseline_path),
        "schedule_after_path": str(after_path) if after_path else None
    }

def run_official_validator(data_path: Path, schedule_path: Path, disruption_path: Optional[Path] = None, baseline_path: Optional[Path] = None):
    cmd = [
        sys.executable,
        str(STARTER_PACK / "validator.py"),
        "--data", str(data_path),
        "--schedule", str(schedule_path)
    ]
    if disruption_path and baseline_path:
        cmd.extend(["--disruption", str(disruption_path), "--baseline", str(baseline_path)])
        
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr
    }
