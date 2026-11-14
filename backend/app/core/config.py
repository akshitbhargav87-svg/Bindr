import os
from typing import List, Optional
from pydantic import BaseModel


class Settings(BaseModel):
    PROJECT_NAME: str = "Promise Keeper Backend"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./promise_keeper.db")
    STORAGE_DIR: str = os.getenv("EVIDENCE_STORAGE_DIR", os.path.join(os.getcwd(), "storage", "evidence"))
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
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"
    ]


settings = Settings()
