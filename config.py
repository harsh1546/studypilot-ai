"""Central settings. Override with environment variables."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = ROOT / "data" / "uploads"
FRONTEND_DIR = ROOT.parent / "frontend"

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("STUDYPILOT_MODEL", "claude-sonnet-4-6")

TOP_K = 4                 # excerpts returned per question
MIN_SCORE = 0.12          # below this the material is treated as "not covered"
MAX_TOPICS = 8
