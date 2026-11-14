from fastapi import APIRouter
from backend.app.api.endpoints import health, auth, cases, commitments, evidence, timeline, extractions

api_router = APIRouter()

# Auth session bootstrap
api_router.include_router(auth.router)

# Health endpoints
api_router.include_router(health.router)

# Cases & Commitments
api_router.include_router(cases.router)
api_router.include_router(commitments.router)

# Evidence & Timeline
api_router.include_router(evidence.router)
api_router.include_router(timeline.router)

# Extractions & Review
api_router.include_router(extractions.router)
