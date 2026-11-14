"""
Promise Keeper - AI Extraction Engine Package.

Exposes core models, extraction functions, document processing, and provider interfaces.
"""

from backend.app.ai import env  # Auto-loads .env if present
from backend.app.ai.schemas import (
    CommitmentExtractionResult,
    CommitmentCategory,
    CommitmentType,
    DeadlineType,
    DeadlineInfo,
    SourceMetadata,
    EvidenceMetadata,
)
from backend.app.ai.document_processor import (
    DocumentProcessor,
    DocumentPage,
    ExtractedDocument,
    DocumentProcessingError,
    UnsupportedFileTypeError,
    UnreadableDocumentError,
)
from backend.app.ai.engine import (
    PromiseExtractionEngine,
    extract_commitment,
    extract_commitment_from_evidence,
)
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
    # Schemas
    "CommitmentExtractionResult",
    "CommitmentCategory",
    "CommitmentType",
    "DeadlineType",
    "DeadlineInfo",
    "SourceMetadata",
    "EvidenceMetadata",
    # Document Processing (Milestone 2)
    "DocumentProcessor",
    "DocumentPage",
    "ExtractedDocument",
    "DocumentProcessingError",
    "UnsupportedFileTypeError",
    "UnreadableDocumentError",
    # Engines & Pipelines
    "PromiseExtractionEngine",
    "extract_commitment",
    "extract_commitment_from_evidence",
    # Providers
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
