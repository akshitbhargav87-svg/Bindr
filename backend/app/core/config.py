import os
from typing import List
from pydantic import BaseModel


class Settings(BaseModel):
    PROJECT_NAME: str = "Promise Keeper Backend"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./promise_keeper.db")
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"
    ]


settings = Settings()
