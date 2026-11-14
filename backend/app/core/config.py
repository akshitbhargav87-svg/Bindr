import os
from typing import List, Optional
from pydantic import BaseModel


def _get_cors_origins() -> List[str]:
    raw = os.getenv("CORS_ORIGINS")
    origins = [o.strip().rstrip("/") for o in raw.split(",") if o.strip() and o.strip() != "*"] if raw else [
        "http://localhost:3000", "http://localhost:5173",
        "http://127.0.0.1:3000", "http://127.0.0.1:5173",
    ]
    for key in ("FRONTEND_ORIGIN", "RENDER_EXTERNAL_URL"):
        value = os.getenv(key, "").strip().rstrip("/")
        if value and value != "*" and value not in origins:
            origins.append(value)
    return origins


class Settings(BaseModel):
    PROJECT_NAME: str = "Promise Keeper Backend"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", os.getenv("ENV", "development"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./promise_keeper.db")
    STORAGE_DIR: str = os.getenv("EVIDENCE_STORAGE_DIR", os.path.join(os.getcwd(), "storage", "evidence"))
    EVIDENCE_STORAGE_BACKEND: str = os.getenv("EVIDENCE_STORAGE_BACKEND", "local")
    EVIDENCE_GCS_BUCKET: Optional[str] = os.getenv("EVIDENCE_GCS_BUCKET")
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MiB per API_CONTRACT
    ALLOWED_MIME_TYPES: List[str] = [
        "image/png",
        "image/jpeg",
        "application/pdf",
        "text/plain"
    ]
    # Meta Model API & AI configuration
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "meta")
    MODEL_API_KEY: Optional[str] = os.getenv("MODEL_API_KEY", None)
    META_MODEL: str = os.getenv("META_MODEL", "muse-spark-1.3")
    META_BASE_URL: str = os.getenv("META_BASE_URL", "https://api.meta.ai/v1")
    CORS_ORIGINS: List[str] = _get_cors_origins()
    # Auth & Session Security
    AUTH_SECRET: Optional[str] = os.getenv("AUTH_SECRET", None)
    SESSION_LIFETIME_SECONDS: int = int(os.getenv("SESSION_LIFETIME_SECONDS", "86400"))
    CLOCK_SKEW_TOLERANCE_SECONDS: int = int(os.getenv("CLOCK_SKEW_TOLERANCE_SECONDS", "60"))
    AUTH_PROVIDER: str = os.getenv("AUTH_PROVIDER", "firebase" if os.getenv("ENVIRONMENT", "development").lower() in {"production", "prod", "staging", "deployed"} else "anonymous")
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_API_KEY: str = os.getenv("FIREBASE_API_KEY", "")
    FIREBASE_AUTH_DOMAIN: str = os.getenv("FIREBASE_AUTH_DOMAIN", "")
    FIREBASE_APP_ID: str = os.getenv("FIREBASE_APP_ID", "")
    ACCOUNT_SESSION_SECONDS: int = int(os.getenv("ACCOUNT_SESSION_SECONDS", "432000"))


settings = Settings()
