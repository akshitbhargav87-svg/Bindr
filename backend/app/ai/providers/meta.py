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
    MODEL_OUTPUT_FIELDS = frozenset({
        "company_name",
        "commitment_category",
        "commitment_description",
        "amount",
        "currency",
        "communication_date",
        "deadline",
        "commitment_type",
        "is_vague_estimate",
        "supporting_quotation",
        "missing_or_ambiguous_fields",
        "user_confirmation_required",
    })
    DEADLINE_FIELDS = frozenset({
        "deadline_type",
        "duration_value",
        "duration_value_max",
        "duration_unit",
        "absolute_date",
        "raw_deadline_text",
    })

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.api_key = api_key if api_key is not None else os.getenv("MODEL_API_KEY")
        self.base_url = (base_url or os.getenv("META_BASE_URL", self.DEFAULT_BASE_URL)).rstrip("/")
        self.model_name = model_name or os.getenv("META_MODEL", self.DEFAULT_MODEL)
        # Resolve timeout: explicit param > META_TIMEOUT env var > default 30s
        self.timeout = timeout if timeout is not None else int(os.getenv("META_TIMEOUT", "30"))

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
            parsed_data = self._normalize_and_validate_output(parsed_data, text)

            # Retain raw source text for audit and verification
            parsed_data["raw_source_text"] = text

            return CommitmentExtractionResult.model_validate(parsed_data)

        except (AIResponseParsingError, json.JSONDecodeError) as e:
            raise AIResponseParsingError(f"Failed to parse Meta response as JSON: {e}") from e
        except Exception as e:
            raise AIResponseParsingError(f"Validation failed on model response: {e}") from e

    def _normalize_and_validate_output(
        self,
        parsed_data: Dict[str, Any],
        source_text: str,
    ) -> Dict[str, Any]:
        """Validate model output before schema defaults can hide missing fields."""
        if not isinstance(parsed_data, dict):
            raise AIResponseParsingError("Meta response must be a JSON object.")

        data = dict(parsed_data)
        flat_deadline_fields = self.DEADLINE_FIELDS.intersection(data)
        if "deadline" in data:
            if flat_deadline_fields:
                raise AIResponseParsingError(
                    "Meta response must not mix nested and top-level deadline fields."
                )
            deadline = data["deadline"]
        else:
            if not flat_deadline_fields:
                raise AIResponseParsingError("Meta response is missing the required deadline object.")
            deadline = {
                field: data.pop(field)
                for field in self.DEADLINE_FIELDS
                if field in data
            }
            data["deadline"] = deadline

        missing_fields = self.MODEL_OUTPUT_FIELDS.difference(data)
        unexpected_fields = set(data).difference(self.MODEL_OUTPUT_FIELDS)
        if missing_fields:
            raise AIResponseParsingError(
                f"Meta response is missing required fields: {', '.join(sorted(missing_fields))}."
            )
        if unexpected_fields:
            raise AIResponseParsingError(
                f"Meta response contains unsupported fields: {', '.join(sorted(unexpected_fields))}."
            )
        if not isinstance(deadline, dict):
            raise AIResponseParsingError("Meta response deadline must be an object.")

        missing_deadline_fields = self.DEADLINE_FIELDS.difference(deadline)
        unexpected_deadline_fields = set(deadline).difference(self.DEADLINE_FIELDS)
        if missing_deadline_fields:
            raise AIResponseParsingError(
                "Meta response deadline is missing required fields: "
                f"{', '.join(sorted(missing_deadline_fields))}."
            )
        if unexpected_deadline_fields:
            raise AIResponseParsingError(
                "Meta response deadline contains unsupported fields: "
                f"{', '.join(sorted(unexpected_deadline_fields))}."
            )

        category = data["commitment_category"]
        commitment_type = data["commitment_type"]
        deadline_type = deadline["deadline_type"]
        if category == "no_commitment" and commitment_type != "none":
            raise AIResponseParsingError(
                "Meta response contradicts no_commitment category and commitment_type."
            )
        if category != "no_commitment" and commitment_type == "none":
            raise AIResponseParsingError(
                "Meta response has a commitment category but commitment_type is none."
            )
        if data["is_vague_estimate"] and commitment_type != "inferred":
            raise AIResponseParsingError(
                "A vague estimate must have commitment_type inferred."
            )
        if (
            (commitment_type == "inferred" or data["is_vague_estimate"]
             or data["missing_or_ambiguous_fields"])
            and not data["user_confirmation_required"]
        ):
            raise AIResponseParsingError(
                "Meta response must require user confirmation for inferred or ambiguous results."
            )
        if category == "no_commitment" and (
            data["amount"] is not None
            or data["supporting_quotation"] is not None
            or deadline_type != "none"
        ):
            raise AIResponseParsingError(
                "A no_commitment result cannot include promise amount, quotation, or deadline."
            )

        if deadline_type == "duration":
            if (
                deadline["duration_value"] is None
                or not deadline["duration_unit"]
                or deadline["absolute_date"] is not None
            ):
                raise AIResponseParsingError(
                    "A duration deadline requires a value and unit, and cannot include an absolute date."
                )
            maximum = deadline["duration_value_max"]
            if maximum is not None and maximum < deadline["duration_value"]:
                raise AIResponseParsingError(
                    "Deadline duration maximum cannot be less than its minimum."
                )
        elif deadline_type == "absolute_date":
            if (
                not deadline["absolute_date"]
                or deadline["duration_value"] is not None
                or deadline["duration_value_max"] is not None
                or deadline["duration_unit"] is not None
            ):
                raise AIResponseParsingError(
                    "An absolute-date deadline requires only an absolute date, not duration fields."
                )
        elif deadline_type == "none":
            if any(deadline[field] is not None for field in self.DEADLINE_FIELDS - {"deadline_type"}):
                raise AIResponseParsingError(
                    "A deadline_type of none cannot contain deadline details."
                )
        else:
            raise AIResponseParsingError(
                f"Unsupported deadline_type '{deadline_type}'."
            )

        quotation = data["supporting_quotation"]
        if quotation is not None and (
            not isinstance(quotation, str) or not quotation or quotation not in source_text
        ):
            raise AIResponseParsingError(
                "Meta response supporting_quotation must be an exact source-text substring."
            )

        return data

    def _clean_and_parse_json(self, raw_text: str) -> Dict[str, Any]:
        """Strip markdown code block fences if present and decode JSON."""
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        return json.loads(cleaned)
