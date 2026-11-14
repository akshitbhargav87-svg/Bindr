"""
Promise Keeper - AI Extraction Engine Package (Milestone 1).

Exposes core models, extraction functions, and provider interfaces.
"""

from backend.app.ai.schemas import (
    CommitmentExtractionResult,
    CommitmentCategory,
    CommitmentType,
    DeadlineType,
    DeadlineInfo,
    SourceMetadata,
)
from backend.app.ai.engine import PromiseExtractionEngine, extract_commitment
from backend.app.ai.providers.base import (
    AIProvider,
    AIProviderError,
    AIAuthenticationError,
    AIConnectionError,
    AIRateLimitError,
    AIResponseParsingError,
)
from backend.app.ai.providers.meta import MetaProvider
from backend.app.ai.providers.mock import MockAIProvider
from backend.app.ai.providers.factory import get_ai_provider

__all__ = [
    "CommitmentExtractionResult",
    "CommitmentCategory",
    "CommitmentType",
    "DeadlineType",
    "DeadlineInfo",
    "SourceMetadata",
    "PromiseExtractionEngine",
    "extract_commitment",
    "AIProvider",
    "AIProviderError",
    "AIAuthenticationError",
    "AIConnectionError",
    "AIRateLimitError",
    "AIResponseParsingError",
    "MetaProvider",
    "MockAIProvider",
    "get_ai_provider",
]
