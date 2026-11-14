"""
Mock AI Provider for synthetic testing, offline test runs, and test suites.
"""

from __future__ import annotations

import re
from typing import Optional, List, Dict, Any

from backend.app.ai.providers.base import (
    AIProvider,
    AIAuthenticationError,
    AIConnectionError,
    AIRateLimitError,
    AIResponseParsingError,
)
from backend.app.ai.schemas import (
    CommitmentExtractionResult,
    CommitmentCategory,
    CommitmentType,
    DeadlineInfo,
    DeadlineType,
    SourceMetadata,
)


class MockAIProvider(AIProvider):
    """
    Deterministic mock provider for unit tests and local development.
    Can be configured to return specific synthetic scenarios or simulate failures.
    """

    def __init__(
        self,
        simulate_failure: Optional[str] = None,
        custom_responses: Optional[Dict[str, CommitmentExtractionResult]] = None,
    ):
        """
        Args:
            simulate_failure: Set to 'auth', 'connection', 'rate_limit', or 'parsing' to simulate API failures.
            custom_responses: Map of text snippets to pre-configured results.
        """
        self.simulate_failure = simulate_failure
        self.custom_responses = custom_responses or {}

    def extract_commitment(
        self,
        text: str,
        metadata: Optional[SourceMetadata] = None,
    ) -> CommitmentExtractionResult:
        """Process text using deterministic rule-based matching and synthetic scenarios."""

        # Handle simulated failure modes for testing error handlers
        if self.simulate_failure == "auth":
            raise AIAuthenticationError("Simulated Gemini authentication failure: invalid API key.")
        elif self.simulate_failure == "connection":
            raise AIConnectionError("Simulated network timeout connecting to AI provider.")
        elif self.simulate_failure == "rate_limit":
            raise AIRateLimitError("Simulated API rate limit exceeded (429).")
        elif self.simulate_failure == "parsing":
            raise AIResponseParsingError("Simulated malformed LLM JSON response.")

        # Check for custom pre-registered responses
        for trigger_text, response in self.custom_responses.items():
            if trigger_text.lower() in text.lower():
                res = response.model_copy(deep=True)
                res.raw_source_text = text
                return res

        lower = text.lower()

        # Scenario 1: Refund with a deadline
        if "refund" in lower and any(word in lower for word in ["business days", "days", "credited", "approved"]):
            # Extract company name if present
            company = self._detect_company(text, metadata)
            amount, currency = self._extract_amount_currency(text)
            deadline = self._extract_duration_deadline(text)

            # Find quotation
            quote = self._find_first_matching_sentence(
                text, ["refund", "credited", "approved", "account within"]
            )

            is_vague = any(v in lower for v in ["usually", "might", "typically", "estimate", "approx"])

            return CommitmentExtractionResult(
                company_name=company,
                commitment_category=CommitmentCategory.REFUND,
                commitment_description=f"Refund of {amount if amount else 'funds'} will be credited to your account.",
                amount=amount,
                currency=currency,
                communication_date=metadata.communication_date if metadata else None,
                deadline=deadline,
                commitment_type=CommitmentType.INFERRED if is_vague else CommitmentType.EXPLICIT,
                is_vague_estimate=is_vague,
                supporting_quotation=quote,
                missing_or_ambiguous_fields=[] if not is_vague else ["exact_date"],
                user_confirmation_required=is_vague,
                raw_source_text=text,
            )

        # Scenario 2: Replacement promise
        if "replacement" in lower or "replace" in lower:
            company = self._detect_company(text, metadata)
            deadline = self._extract_duration_deadline(text)
            quote = self._find_first_matching_sentence(text, ["replacement", "replace", "dispatch", "ship"])

            is_vague = any(v in lower for v in ["might", "looking into", "hope to", "estimate"])

            return CommitmentExtractionResult(
                company_name=company,
                commitment_category=CommitmentCategory.REPLACEMENT,
                commitment_description="Company promised to dispatch a replacement unit.",
                amount=None,
                currency=None,
                communication_date=metadata.communication_date if metadata else None,
                deadline=deadline,
                commitment_type=CommitmentType.INFERRED if is_vague else CommitmentType.EXPLICIT,
                is_vague_estimate=is_vague,
                supporting_quotation=quote,
                missing_or_ambiguous_fields=[] if not is_vague else ["shipment_timeline"],
                user_confirmation_required=is_vague,
                raw_source_text=text,
            )

        # Scenario 3: Ambiguous / Vague communication
        if any(v in lower for v in ["might be able", "usually takes", "look into", "consider", "some credit"]):
            company = self._detect_company(text, metadata)
            quote = self._find_first_matching_sentence(
                text, ["might", "usually", "consider", "credit", "review"]
            )
            return CommitmentExtractionResult(
                company_name=company,
                commitment_category=CommitmentCategory.OTHER,
                commitment_description="Unconfirmed possibility of credit or review; no binding commitment made.",
                amount=None,
                currency=None,
                communication_date=metadata.communication_date if metadata else None,
                deadline=DeadlineInfo(
                    deadline_type=DeadlineType.NONE,
                    raw_deadline_text=None,
                ),
                commitment_type=CommitmentType.INFERRED,
                is_vague_estimate=True,
                supporting_quotation=quote,
                missing_or_ambiguous_fields=["amount", "deadline", "commitment_validity"],
                user_confirmation_required=True,
                raw_source_text=text,
            )

        # Scenario 4: No explicit promise (ticket closed, acknowledgement, newsletters)
        return CommitmentExtractionResult(
            company_name=self._detect_company(text, metadata),
            commitment_category=CommitmentCategory.NO_COMMITMENT,
            commitment_description="No commitment found in communication.",
            amount=None,
            currency=None,
            communication_date=metadata.communication_date if metadata else None,
            deadline=DeadlineInfo(deadline_type=DeadlineType.NONE),
            commitment_type=CommitmentType.NONE,
            is_vague_estimate=False,
            supporting_quotation=None,
            missing_or_ambiguous_fields=[],
            user_confirmation_required=False,
            raw_source_text=text,
        )

    def _detect_company(self, text: str, metadata: Optional[SourceMetadata]) -> Optional[str]:
        if metadata and metadata.sender:
            return metadata.sender

        # Check known common synthetic company markers
        known_companies = ["Acme Corp", "CloudStream", "MegaStore", "FastShip", "Apex Logistics", "TechCorp"]
        for c in known_companies:
            if c.lower() in text.lower():
                return c

        match = re.search(r"team\s+at\s+([A-Za-z0-9\s]+?)(?:\.|\n|$)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_amount_currency(self, text: str) -> tuple[Optional[float], Optional[str]]:
        match = re.search(r"(\$|€|£|USD|EUR|GBP)\s*([0-9]+(?:\.[0-9]{2})?)", text)
        if match:
            curr, amt = match.groups()
            curr_map = {"$": "USD", "€": "EUR", "£": "GBP"}
            return float(amt), curr_map.get(curr, curr)

        match_after = re.search(r"([0-9]+(?:\.[0-9]{2})?)\s*(USD|EUR|GBP|dollars)", text, re.IGNORECASE)
        if match_after:
            amt, curr = match_after.groups()
            return float(amt), curr.upper()

        return None, None

    def _extract_duration_deadline(self, text: str) -> DeadlineInfo:
        # e.g., within 5-7 business days
        match_range = re.search(r"within\s+(\d+)\s*[-to]+\s*(\d+)\s*(business\s+days|calendar\s+days|days|hours|weeks)", text, re.IGNORECASE)
        if match_range:
            v_min, v_max, unit_raw = match_range.groups()
            unit = "business_days" if "business" in unit_raw.lower() else ("calendar_days" if "calendar" in unit_raw.lower() else "calendar_days")
            return DeadlineInfo(
                deadline_type=DeadlineType.DURATION,
                duration_value=float(v_min),
                duration_value_max=float(v_max),
                duration_unit=unit,
                raw_deadline_text=match_range.group(0),
            )

        match_single = re.search(r"within\s+(\d+)\s*(business\s+days|calendar\s+days|days|hours|weeks)", text, re.IGNORECASE)
        if match_single:
            val, unit_raw = match_single.groups()
            unit = "business_days" if "business" in unit_raw.lower() else ("calendar_days" if "calendar" in unit_raw.lower() else "calendar_days")
            return DeadlineInfo(
                deadline_type=DeadlineType.DURATION,
                duration_value=float(val),
                duration_unit=unit,
                raw_deadline_text=match_single.group(0),
            )

        match_abs = re.search(r"(?:by|on)\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|\w+\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4}?)", text, re.IGNORECASE)
        if match_abs:
            return DeadlineInfo(
                deadline_type=DeadlineType.ABSOLUTE_DATE,
                absolute_date=match_abs.group(1).strip(),
                raw_deadline_text=match_abs.group(0).strip(),
            )

        return DeadlineInfo(deadline_type=DeadlineType.NONE)

    def _find_first_matching_sentence(self, text: str, keywords: List[str]) -> Optional[str]:
        # Split text into sentences or lines
        lines = re.split(r"(?<=[.!?\n])\s+", text)
        for line in lines:
            line_str = line.strip()
            if any(k.lower() in line_str.lower() for k in keywords):
                return line_str
        return None
