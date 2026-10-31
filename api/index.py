import sys
import os
from pathlib import Path

# Add project root to sys.path so 'backend' and 'CrunchWeek_StarterPack' can be imported
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure Vercel environment flag is recognized
os.environ["VERCEL"] = "1"

# Import the pre-configured FastAPI app
from backend.main import app

# Expose app for ASGI serverless runners
__all__ = ["app"]
