from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import Base, engine
from backend.app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite tables on startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Promise Keeper Backend - Milestone 1",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount router under /api/v1 (API_CONTRACT) and /api (Milestone 1 Health & Core APIs)
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": "Welcome to Promise Keeper API",
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
