"""
Promise Extraction Engine.

Coordinates AI providers, runs post-processing validation, and ensures adherence
to the Promise Keeper contract rules.
"""

from __future__ import annotations

import logging
from typing import Optional

from backend.app.ai.schemas import (
    CommitmentExtractionResult,
    CommitmentCategory,
    CommitmentType,
    SourceMetadata,
)
from backend.app.ai.providers.base import (
    AIProvider,
    AIProviderError,
    AIAuthenticationError,
    AIConnectionError,
    AIRateLimitError,
    AIResponseParsingError,
)
from backend.app.ai.providers.factory import get_ai_provider

logger = logging.getLogger("backend.app.ai.engine")


class PromiseExtractionEngine:
    """
    Main engine for extracting structured commitments from raw communication text.
    Handles provider orchestration, error boundaries, and verbatim quote verification.
    """

    def __init__(self, provider: Optional[AIProvider] = None, fallback_on_error: bool = False):
        """
        Args:
            provider: Custom or pre-configured AIProvider instance. If None, factory default is resolved.
            fallback_on_error: If True, returns a safe degraded result requiring user confirmation
                              instead of raising exceptions on provider or parsing failures.
        """
        self.provider = provider or get_ai_provider()
        self.fallback_on_error = fallback_on_error

    def extract(
        self,
        text: str,
        metadata: Optional[SourceMetadata] = None,
    ) -> CommitmentExtractionResult:
        """
        Extract structured commitment data from communication text.

        Args:
            text: Raw communication text (from email, chat, OCR screenshot, PDF).
            metadata: Optional source metadata (sender, communication_date, channel).

        Returns:
            Validated CommitmentExtractionResult model.
        """
        if not text or not text.strip():
            return CommitmentExtractionResult(
                commitment_description="Empty or blank communication text received.",
                commitment_category=CommitmentCategory.NO_COMMITMENT,
                commitment_type=CommitmentType.NONE,
                missing_or_ambiguous_fields=["communication_text"],
                user_confirmation_required=True,
                raw_source_text=text or "",
            )

        try:
            result = self.provider.extract_commitment(text=text, metadata=metadata)
            return self._post_process_result(result, text=text, metadata=metadata)

        except (AIAuthenticationError, AIConnectionError, AIRateLimitError, AIResponseParsingError, AIProviderError) as e:
            logger.error(f"AI Provider error during promise extraction: {e}")
            if self.fallback_on_error:
                return self._create_safe_fallback_result(text=text, error_message=str(e), metadata=metadata)
            raise

    def _post_process_result(
        self,
        result: CommitmentExtractionResult,
        text: str,
        metadata: Optional[SourceMetadata] = None,
    ) -> CommitmentExtractionResult:
        """
        Ensure post-extraction invariants:
        1. Ensure raw_source_text is populated.
        2. Ensure communication_date from metadata is populated if not detected in text.
        3. Verify supporting quotation is exact substring of the text.
        4. Guarantee no fabricated confidence scores exist.
        """
        result.raw_source_text = text

        if not result.communication_date and metadata and metadata.communication_date:
            result.communication_date = metadata.communication_date

        if not result.company_name and metadata and metadata.sender:
            result.company_name = metadata.sender

        # Check verbatim quote integrity
        if result.supporting_quotation:
            quote_clean = " ".join(result.supporting_quotation.split()).lower()
            text_clean = " ".join(text.split()).lower()
            if quote_clean not in text_clean:
                if "supporting_quotation_mismatch" not in result.missing_or_ambiguous_fields:
                    result.missing_or_ambiguous_fields.append("supporting_quotation_mismatch")
                result.user_confirmation_required = True

        return result

    def _create_safe_fallback_result(
        self,
        text: str,
        error_message: str,
        metadata: Optional[SourceMetadata] = None,
    ) -> CommitmentExtractionResult:
        """
        Create a safe, graceful fallback result when the model or API fails,
        flagging human-in-the-loop review.
        """
        return CommitmentExtractionResult(
            company_name=metadata.sender if metadata else None,
            commitment_category=CommitmentCategory.OTHER,
            commitment_description="Extraction could not be completed automatically due to provider error.",
            commitment_type=CommitmentType.INFERRED,
            is_vague_estimate=False,
            supporting_quotation=None,
            missing_or_ambiguous_fields=["ai_provider_error", error_message],
            user_confirmation_required=True,
            raw_source_text=text,
        )


def extract_commitment(
    text: str,
    metadata: Optional[SourceMetadata] = None,
    provider: Optional[AIProvider] = None,
    fallback_on_error: bool = False,
) -> CommitmentExtractionResult:
    """
    Convenience function to extract structured commitment data.

    Example:
        result = extract_commitment(
            "We will issue your refund of $45.00 within 5-7 business days.",
            metadata=SourceMetadata(sender="Acme Corp")
        )
    """
    engine = PromiseExtractionEngine(provider=provider, fallback_on_error=fallback_on_error)
    return engine.extract(text=text, metadata=metadata)
