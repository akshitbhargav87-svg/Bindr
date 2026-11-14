from fastapi import APIRouter
from backend.app.api.endpoints import health, cases, commitments, evidence, timeline

api_router = APIRouter()

# Health endpoints
api_router.include_router(health.router)

# Cases & Commitments
api_router.include_router(cases.router)
api_router.include_router(commitments.router)

# Evidence & Timeline
api_router.include_router(evidence.router)
api_router.include_router(timeline.router)
