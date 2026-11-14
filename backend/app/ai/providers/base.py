"""
Base interface and custom exceptions for AI providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from backend.app.ai.schemas import CommitmentExtractionResult, SourceMetadata


class AIProviderError(Exception):
    """Base exception for all AI provider errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AIAuthenticationError(AIProviderError):
    """Raised when API credentials are missing, expired, or invalid."""
    pass


class AIConnectionError(AIProviderError):
    """Raised when network connectivity or remote host is unavailable."""
    pass


class AIRateLimitError(AIProviderError):
    """Raised when API quota or rate limits are exceeded."""
    pass


class AIResponseParsingError(AIProviderError):
    """Raised when the LLM returns an unparseable or schema-violating response."""
    pass


class AIProvider(ABC):
    """
    Abstract Base Class for Promise Keeper AI extraction providers.
    Allows easy switching between Meta Model API, Anthropic, OpenAI, or Mock providers.
    """

    @abstractmethod
    def extract_commitment(
        self,
        text: str,
        metadata: Optional[SourceMetadata] = None
    ) -> CommitmentExtractionResult:
        """
        Analyze communication text and extract a structured CommitmentExtractionResult.

        Args:
            text: Raw extracted text from email, screenshot, letter, or PDF.
            metadata: Optional source metadata (sender, communication date, channel, etc.).

        Returns:
            Validated CommitmentExtractionResult instance.

        Raises:
            AIAuthenticationError: If API credentials are missing or invalid.
            AIConnectionError: If network or provider is unreachable.
            AIRateLimitError: If provider rate limits are hit.
            AIResponseParsingError: If provider output cannot be parsed into the schema.
        """
        pass
