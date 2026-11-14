"""
Gemini AI Provider implementation for structured commitment extraction.
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


class GeminiProvider(AIProvider):
    """
    Gemini extraction provider supporting Gemini 1.5 Flash / Pro and Gemini 2.0.
    Connects via the Google Generative Language API.
    """

    DEFAULT_MODEL = "gemini-1.5-flash"
    API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: int = 30,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name or os.getenv("GEMINI_MODEL", self.DEFAULT_MODEL)
        self.timeout = timeout

    def _validate_credentials(self) -> str:
        """Validate that an API key is present."""
        if not self.api_key or not self.api_key.strip():
            raise AIAuthenticationError(
                "Gemini API key is not configured. "
                "Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variable or pass api_key to GeminiProvider."
            )
        return self.api_key.strip()

    def extract_commitment(
        self,
        text: str,
        metadata: Optional[SourceMetadata] = None,
    ) -> CommitmentExtractionResult:
        """
        Send communication text to Gemini and parse the structured commitment result.
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

        url = self.API_URL_TEMPLATE.format(model=self.model_name, key=api_key)
        payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT_PROMISE_EXTRACTOR}]
            },
            "contents": [
                {
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.0,
            },
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout as e:
            raise AIConnectionError(f"Request to Gemini API timed out after {self.timeout}s: {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise AIConnectionError(f"Failed to connect to Gemini API: {e}") from e
        except Exception as e:
            raise AIProviderError(f"Unexpected connection failure with Gemini: {e}") from e

        # Handle HTTP status codes
        if response.status_code in (401, 403):
            raise AIAuthenticationError(
                f"Gemini authentication failed (HTTP {response.status_code}): {response.text}"
            )
        elif response.status_code == 429:
            raise AIRateLimitError(
                f"Gemini API rate limit or quota exceeded (HTTP 429): {response.text}"
            )
        elif response.status_code >= 500:
            raise AIProviderError(
                f"Gemini remote server error (HTTP {response.status_code}): {response.text}"
            )
        elif response.status_code != 200:
            raise AIProviderError(
                f"Gemini request failed (HTTP {response.status_code}): {response.text}"
            )

        try:
            res_json = response.json()
            candidates = res_json.get("candidates", [])
            if not candidates:
                raise AIResponseParsingError("Gemini returned no candidates in response.")

            candidate = candidates[0]
            parts = candidate.get("content", {}).get("parts", [])
            if not parts:
                raise AIResponseParsingError("Gemini candidate contains no content parts.")

            raw_text = parts[0].get("text", "")
            parsed_data = self._clean_and_parse_json(raw_text)

            # Attach raw source text for verification
            parsed_data["raw_source_text"] = text

            return CommitmentExtractionResult.model_validate(parsed_data)

        except (AIResponseParsingError, json.JSONDecodeError) as e:
            raise AIResponseParsingError(f"Failed to parse Gemini response as JSON: {e}") from e
        except Exception as e:
            raise AIResponseParsingError(f"Validation failed on model response: {e}") from e

    def _clean_and_parse_json(self, raw_text: str) -> Dict[str, Any]:
        """Strip markdown fences if present and decode JSON."""
        cleaned = raw_text.strip()
        # Remove ```json and ``` fences
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        return json.loads(cleaned)
