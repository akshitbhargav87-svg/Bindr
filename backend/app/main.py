import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.config import settings
from backend.app.core.database import Base, engine, run_sqlite_migrations
from backend.app.api.router import api_router

logger = logging.getLogger("backend.app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite tables and run non-destructive schema migrations
    Base.metadata.create_all(bind=engine)
    run_sqlite_migrations(engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Promise Keeper Backend - Milestones 1-3",
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

# Global Error Normalization Handlers per docs/API_CONTRACT.md

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = str(uuid.uuid4())
    details = []
    for err in exc.errors():
        loc = [str(x) for x in err.get("loc", []) if x not in ("body",)]
        field_name = ".".join(loc) if loc else None
        details.append({
            "field": field_name,
            "message": str(err.get("msg", "Invalid input"))
        })
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "details": details,
                "request_id": req_id
            }
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    req_id = str(uuid.uuid4())
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        payload = exc.detail["error"]
        if "request_id" not in payload:
            payload["request_id"] = req_id
        return JSONResponse(status_code=exc.status_code, content={"error": payload})

    code_map = {
        400: "INVALID_JSON",
        401: "UNAUTHENTICATED",
        403: "CSRF_FAILED",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        413: "FILE_TOO_LARGE",
        415: "UNSUPPORTED_MEDIA_TYPE",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_ERROR",
        502: "AI_INVALID_OUTPUT",
        503: "AI_UNAVAILABLE",
        504: "AI_TIMEOUT"
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": str(exc.detail),
                "details": [],
                "request_id": req_id
            }
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    req_id = str(uuid.uuid4())
    logger.exception(f"Unhandled internal server error (request_id={req_id}): {exc}")
    # Internal details, stack traces, paths, and credentials are completely redacted
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal server error occurred.",
                "details": [],
                "request_id": req_id
            }
        }
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
