import os
import shutil
from pathlib import Path

# Base project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Detect if running in Vercel Serverless / Lambda environment
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

# Static and dataset input paths
DATA_PATH = BASE_DIR / "CrunchWeek_StarterPack" / "data" / "cit_public.json"
DISRUPTION_PATH = BASE_DIR / "CrunchWeek_StarterPack" / "examples" / "sample_disruption.json"
FRONTEND_DIR = BASE_DIR / "frontend"
PUBLIC_DIR = BASE_DIR / "public"

# Database storage path
DEFAULT_DB_DIR = BASE_DIR / "backend" / "data_store"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "cit_campus.db"

# Export directory
DEFAULT_EXPORTS_DIR = BASE_DIR / "exports"

if IS_VERCEL:
    # Writable paths in /tmp (Serverless environment)
    TMP_DIR = Path("/tmp")
    
    DB_DIR = TMP_DIR / "data_store"
    DB_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH = DB_DIR / "cit_campus.db"
    
    # Pre-seed SQLite database from repo into /tmp if not already present
    if not DB_PATH.exists() and DEFAULT_DB_PATH.exists():
        shutil.copy2(DEFAULT_DB_PATH, DB_PATH)
        
    EXPORTS_DIR = TMP_DIR / "exports"
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if DEFAULT_EXPORTS_DIR.exists():
        for f in DEFAULT_EXPORTS_DIR.glob("*.json"):
            dest_file = EXPORTS_DIR / f.name
            if not dest_file.exists():
                shutil.copy2(f, dest_file)
else:
    DB_DIR = DEFAULT_DB_DIR
    DB_PATH = DEFAULT_DB_PATH
    EXPORTS_DIR = DEFAULT_EXPORTS_DIR

# Security Configuration
SECRET_KEY = os.environ.get("CIT_SECRET_KEY", "cit_campus_secure_master_secret_key_2026_production")
TOKEN_EXPIRY_HOURS = int(os.environ.get("TOKEN_EXPIRY_HOURS", 12))
MAX_FAILED_LOGIN_ATTEMPTS = int(os.environ.get("MAX_FAILED_LOGIN_ATTEMPTS", 5))
LOCKOUT_MINUTES = int(os.environ.get("LOCKOUT_MINUTES", 15))
