import os
from typing import List
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
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"
    ]


settings = Settings()
