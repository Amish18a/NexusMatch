from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PHASE2_ROOT = REPO_ROOT / "Phase2"
PHASE3_ROOT = REPO_ROOT / "Phase3"

DATA_DIR = Path(os.getenv("NEXUSMATCH_DATA_DIR", str(PHASE3_ROOT / "backend" / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.getenv("NEXUSMATCH_DB_PATH", str(DATA_DIR / "nexusmatch_phase3.db")))
PROFILE_SEED_PATH = Path(os.getenv("NEXUSMATCH_PROFILE_SEED", str(PHASE3_ROOT / "backend" / "data" / "player_profiles.json")))
MODEL_PATH = Path(os.getenv("NEXUSMATCH_MODEL_PATH", str(PHASE2_ROOT / "ml" / "artifacts" / "final_trust_model.joblib")))
TRUST_INFERENCE_DIR = PHASE2_ROOT / "inference"

CPP_HOST = os.getenv("NEXUSMATCH_SERVER_HOST", "127.0.0.1")
CPP_PORT = int(os.getenv("NEXUSMATCH_SERVER_PORT", "5050"))
CPP_TIMEOUT_SECONDS = float(os.getenv("NEXUSMATCH_CPP_TIMEOUT", "3"))

MAX_REGISTERED_PLAYERS = 10
ALLOWED_MATCH_SIZES = {3, 4, 5}
