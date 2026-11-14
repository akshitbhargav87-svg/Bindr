"""
Meta Model API Provider implementation for structured commitment extraction.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional, Any, Dict
import requests

from backend.app.ai.providers.base import (
    AIProvider,
    AIAuthenticationError,
    AIConnectionError,
    AIRateLimitError,
    AIResponseParsingError,
    AIProviderError,
)
from backend.app.ai.schemas import CommitmentExtractionResult, SourceMetadata
from backend.app.ai.prompts import SYSTEM_PROMPT_PROMISE_EXTRACTOR, EXTRACTION_USER_PROMPT_TEMPLATE


class MetaProvider(AIProvider):
    """
    Meta Model API extraction provider supporting Meta Muse and Llama models.
    Connects via Bearer token to Meta's chat completion endpoint.
    """

    DEFAULT_BASE_URL = "https://api.meta.ai/v1"
    DEFAULT_MODEL = "muse-spark-1.3"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: int = 30,
    ):
        self.api_key = api_key if api_key is not None else os.getenv("MODEL_API_KEY")
        self.base_url = (base_url or os.getenv("META_BASE_URL", self.DEFAULT_BASE_URL)).rstrip("/")
        self.model_name = model_name or os.getenv("META_MODEL", self.DEFAULT_MODEL)
        self.timeout = timeout

    def _validate_credentials(self) -> str:
        """Validate that the Meta API key is present."""
        if not self.api_key or not self.api_key.strip():
            raise AIAuthenticationError(
                "Meta API key is not configured. "
                "Please set MODEL_API_KEY environment variable or pass api_key to MetaProvider."
            )
        return self.api_key.strip()

    def extract_commitment(
        self,
        text: str,
        metadata: Optional[SourceMetadata] = None,
    ) -> CommitmentExtractionResult:
        """
        Send communication text to Meta Model API and parse the structured commitment result.
        """
        api_key = self._validate_credentials()

        if not text or not text.strip():
            return CommitmentExtractionResult(
                commitment_description="No input text provided.",
                missing_or_ambiguous_fields=["input_text"],
                user_confirmation_required=True,
                raw_source_text=text,
            )

        metadata_str = (
            json.dumps(metadata.model_dump(exclude_none=True), indent=2)
            if metadata
            else "None provided"
        )
        user_prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(
            metadata_str=metadata_str,
            text=text.strip(),
        )

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_PROMISE_EXTRACTOR},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout as e:
            raise AIConnectionError(f"Request to Meta API timed out after {self.timeout}s: {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise AIConnectionError(f"Failed to connect to Meta API: {e}") from e
        except Exception as e:
            raise AIProviderError(f"Unexpected connection failure with Meta API: {e}") from e

        # Handle HTTP status codes
        if response.status_code in (401, 403):
            raise AIAuthenticationError(
                f"Meta API authentication failed (HTTP {response.status_code}): {response.text}"
            )
        elif response.status_code == 429:
            raise AIRateLimitError(
                f"Meta API rate limit or quota exceeded (HTTP 429): {response.text}"
            )
        elif response.status_code >= 500:
            raise AIProviderError(
                f"Meta API server error (HTTP {response.status_code}): {response.text}"
            )
        elif response.status_code != 200:
            raise AIProviderError(
                f"Meta API request failed (HTTP {response.status_code}): {response.text}"
            )

        try:
            res_json = response.json()
            choices = res_json.get("choices", [])
            if not choices:
                raise AIResponseParsingError("Meta API returned no choices in response.")

            message = choices[0].get("message", {})
            content = message.get("content", "")
            if not content:
                raise AIResponseParsingError("Meta API choice contains empty message content.")

            parsed_data = self._clean_and_parse_json(content)

            # Retain raw source text for audit and verification
            parsed_data["raw_source_text"] = text

            return CommitmentExtractionResult.model_validate(parsed_data)

        except (AIResponseParsingError, json.JSONDecodeError) as e:
            raise AIResponseParsingError(f"Failed to parse Meta response as JSON: {e}") from e
        except Exception as e:
            raise AIResponseParsingError(f"Validation failed on model response: {e}") from e

    def _clean_and_parse_json(self, raw_text: str) -> Dict[str, Any]:
        """Strip markdown code block fences if present and decode JSON."""
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        return json.loads(cleaned)
