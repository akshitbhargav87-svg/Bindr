import uuid
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.config import settings
from backend.app.core.database import Base, engine, run_sqlite_migrations
from backend.app.api.router import api_router
from backend.app.core.auth import get_auth_secret
from backend.app.services.storage import validate_cloud_run_settings

logger = logging.getLogger("backend.app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_cloud_run_settings()
    get_auth_secret()  # Reject a weak or absent production signing key before serving traffic.
    # Initialize SQLite tables and run non-destructive schema migrations
    Base.metadata.create_all(bind=engine)
    run_sqlite_migrations(engine)
    yield


app = FastAPI(
    title="Bindr API",
    description="Evidence-linked promises with human-confirmed terms and outcomes.",
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
        field_name = ".".join(loc) if loc else "request"
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


@app.middleware("http")
async def private_response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "private, no-store"
    return response


@app.get("/health", include_in_schema=False)
@app.get("/healthz", include_in_schema=False)
def readiness():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "healthy", "service": "Bindr"}


# One origin for the browser, API, session and private downloads. API routes above
# retain their JSON 404s; BrowserRouter deep links receive the built application.
frontend_dir = Path(os.getenv("FRONTEND_DIST_DIR", "frontend/dist")).resolve()
if (frontend_dir / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_dir / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    if path == "api" or path.startswith("api/"):
        return JSONResponse(status_code=404, content={"error": {"code": "NOT_FOUND", "message": "Route not found", "details": [], "request_id": str(uuid.uuid4())}})
    candidate = (frontend_dir / path).resolve()
    if candidate.is_relative_to(frontend_dir) and candidate.is_file():
        return FileResponse(candidate)
    if (frontend_dir / "index.html").is_file():
        return FileResponse(frontend_dir / "index.html", headers={"Cache-Control": "no-cache"})
    return JSONResponse(status_code=503, content={"message": "Build the Bindr frontend before starting the combined app."})
