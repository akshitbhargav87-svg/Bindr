"""
Lightweight environment loader to read .env variables without external dependencies.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_env():
    """
    Load environment variables from .env files if not already set in the environment.
    Looks in backend/app/ai/.env and repo root .env.
    """
    candidates = [
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parents[3] / ".env",
    ]
    for env_file in candidates:
        if env_file.is_file():
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'\"")
                        if key and key not in os.environ and val:
                            os.environ[key] = val
            except Exception:
                pass


# Auto-load on import
load_env()
