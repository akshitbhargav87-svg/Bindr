"""
AI Module Adapter (Milestone 2 & 3 Integration Boundary).

Adheres to docs/AI_CONTRACT.md and docs/API_CONTRACT.md:
- Provides a clean, isolated interface between backend services and Kunal's AI extraction module.
- Preserves evidence IDs, filenames, page references, and original bytes.
- Validates source quotations strictly against their specific originating evidence file.
- Strictly forbids implicit mock inference; only uses mock provider when AI_PROVIDER=mock.
- Translates provider errors and timeouts to standard codes (AI_UNAVAILABLE, AI_TIMEOUT, AI_INVALID_OUTPUT).
- Rejects invented candidate IDs, negative amounts, and misattributed sources before persistence.
"""

from __future__ import annotations

import os
import re
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from backend.app.core.config import settings

logger = logging.getLogger("backend.app.services.ai_adapter")


class AIAdapterError(Exception):
    """Base exception for AI Adapter errors."""
    code: str = "AI_INTERNAL_ERROR"

    def __init__(self, message: str, code: Optional[str] = None):
        super().__init__(message)
        if code:
            self.code = code


class AITimeoutError(AIAdapterError):
    code = "AI_TIMEOUT"


class AIServiceUnavailableError(AIAdapterError):
    code = "AI_UNAVAILABLE"


class AIInvalidOutputError(AIAdapterError):
    code = "AI_INVALID_OUTPUT"


class AIValidationError(AIAdapterError):
    code = "VALIDATION_ERROR"


class UnreadableEvidenceError(AIAdapterError):
    code = "UNREADABLE_EVIDENCE"


def extract_text_from_file_bytes(data: bytes, media_type: str, filename: Optional[str] = None) -> str:
    """
    Extract readable text from evidence bytes without brittle regexes or blind byte decoding.
    Per API_CONTRACT:
    - Supports text/plain UTF-8 text.
    - If Kunal's AI OCR pipeline is available, delegates images and PDFs to it.
    - Otherwise raises UnreadableEvidenceError (422) for non-text documents.
    """
    if not data or len(data) == 0:
        raise UnreadableEvidenceError("Evidence file is empty (0 bytes).")

    if media_type == "text/plain":
        try:
            text = data.decode("utf-8").strip()
            if text:
                return text
        except UnicodeDecodeError:
            raise UnreadableEvidenceError("Text evidence contains invalid UTF-8 encoding.")

    # Check if Kunal's RapidOCR / evidence pipeline module is available
    try:
        from backend.app.ai import ocr
        if hasattr(ocr, "extract_text_from_file"):
            text = ocr.extract_text_from_file(data, media_type=media_type, filename=filename)
            if text and text.strip():
                return text.strip()
    except (ImportError, AttributeError):
        pass

    raise UnreadableEvidenceError(
        f"No readable text could be extracted from evidence with media_type '{media_type}'. "
        "Scanned documents and images require RapidOCR module integration."
    )


class AIModuleAdapter:
    """
    Adapter orchestrating calls to Kunal's AI engine adhering to AI_CONTRACT v1.
    """

    def __init__(self, timeout_seconds: int = 45):
        self.timeout_seconds = timeout_seconds
        self._engine = None

    def _get_engine(self):
        """
        Instantiate Kunal's PromiseExtractionEngine with the configured provider.
        Respects AI_PROVIDER ('meta' or 'mock'), MODEL_API_KEY, META_MODEL, and META_BASE_URL.
        CRITICAL: Does NOT silently fall back to mock when in 'meta' mode.
        """
        if self._engine is not None:
            return self._engine

        provider_name = (settings.AI_PROVIDER or os.getenv("AI_PROVIDER", "meta")).lower().strip()
        api_key = settings.MODEL_API_KEY or os.getenv("MODEL_API_KEY")
        base_url = settings.META_BASE_URL or os.getenv("META_BASE_URL", "https://api.meta.ai/v1")
        model_name = settings.META_MODEL or os.getenv("META_MODEL", "muse-spark-1.3")

        # In production Meta mode, if MODEL_API_KEY is missing, raise AIServiceUnavailableError immediately
        if provider_name == "meta":
            if not api_key or not api_key.strip():
                raise AIServiceUnavailableError(
                    "Meta API key is not configured. Please set the MODEL_API_KEY environment variable.",
                    code="AI_UNAVAILABLE"
                )

        try:
            from backend.app.ai.providers.factory import get_ai_provider
            from backend.app.ai.engine import PromiseExtractionEngine

            kwargs = {}
            if provider_name == "meta":
                kwargs["timeout"] = self.timeout_seconds

            provider = get_ai_provider(
                provider_name=provider_name,
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                **kwargs
            )
            return PromiseExtractionEngine(provider=provider, fallback_on_error=False)
        except AIAdapterError:
            raise
        except Exception as e:
            try:
                from backend.app.ai.providers.base import (
                    AIAuthenticationError,
                    AIConnectionError,
                    AIRateLimitError,
                    AIResponseParsingError,
                )
                if isinstance(e, AIAuthenticationError):
                    raise AIServiceUnavailableError(f"Meta provider authentication failed: {e}", code="AI_UNAVAILABLE") from e
                elif isinstance(e, (AIConnectionError, AIRateLimitError)):
                    raise AIServiceUnavailableError(f"Meta provider service error: {e}", code="AI_UNAVAILABLE") from e
                elif isinstance(e, AIResponseParsingError):
                    raise AIInvalidOutputError(f"AI provider returned malformed output: {e}") from e
            except ImportError:
                pass

            err_str = str(e).lower()
            if isinstance(e, TimeoutError) or "timeout" in err_str or "timed out" in err_str:
                raise AITimeoutError(f"Meta provider timed out: {e}") from e
            elif "api key" in err_str or "unauthorized" in err_str:
                raise AIServiceUnavailableError(f"Meta provider authentication failed: {e}", code="AI_UNAVAILABLE") from e
            elif "connection" in err_str or "network" in err_str:
                raise AIServiceUnavailableError(f"Meta provider connection failed: {e}", code="AI_UNAVAILABLE") from e
            else:
                raise AIServiceUnavailableError(f"Failed to initialize AI provider '{provider_name}': {e}", code="AI_UNAVAILABLE") from e

    def prepare_extraction_input(
        self,
        case_id: str,
        evidence: List[Dict[str, Any]],
        existing_commitments: List[Dict[str, Any]],
        reference_time: Optional[str] = None,
        tz_name: str = "Asia/Kolkata"
    ) -> Dict[str, Any]:
        """
        Validate and format input payload per AI_CONTRACT v1.
        Preserves evidence IDs, filenames, page references, and original bytes.
        """
        if not evidence or len(evidence) == 0:
            raise AIValidationError("Extraction requires at least one evidence item (1-10 items allowed).")
        if len(evidence) > 10:
            raise AIValidationError("Extraction allows at most 10 evidence items.")

        total_chars = 0
        seen_ids = set()
        for ev in evidence:
            eid = ev.get("evidence_id")
            if not eid:
                raise AIValidationError("Evidence record missing 'evidence_id'.")
            if eid in seen_ids:
                raise AIValidationError(f"Duplicate evidence ID '{eid}' in extraction request.")
            seen_ids.add(eid)

            text = ev.get("text", "")
            if not text or not text.strip():
                raise AIValidationError(f"Evidence '{eid}' contains empty text.")
            total_chars += len(text)

        if total_chars > 50000:
            raise AIValidationError(f"Total evidence text exceeds 50,000 characters limit ({total_chars} chars).")

        now_utc = reference_time or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return {
            "schema_version": 1,
            "case_id": case_id,
            "reference_time": now_utc,
            "timezone": tz_name,
            "evidence": evidence,
            "existing_commitments": existing_commitments or []
        }

    def extract_commitments(
        self,
        case_id: str,
        evidence: List[Dict[str, Any]],
        existing_commitments: Optional[List[Dict[str, Any]]] = None,
        reference_time: Optional[str] = None,
        tz_name: str = "Asia/Kolkata"
    ) -> Dict[str, Any]:
        """
        Execute promise extraction against evidence text.
        
        CRITICAL INVARIANTS:
        1. Candidates require explicit human review; never persisted automatically.
        2. Quotations MUST be verified against their specific originating evidence file.
        3. Never attribute a quote from file B to file A.
        4. Rejects negative monetary amounts and invalid candidate schemas.
        """
        payload = self.prepare_extraction_input(
            case_id=case_id,
            evidence=evidence,
            existing_commitments=existing_commitments or [],
            reference_time=reference_time,
            tz_name=tz_name
        )

        # 1. Attempt Kunal's pipeline interface if available
        try:
            from backend.app.ai import extract_commitment_from_evidence
            pipeline_result = extract_commitment_from_evidence(
                evidence=evidence,
                existing_commitments=existing_commitments or [],
                reference_time=payload["reference_time"],
                timezone=tz_name
            )
            if pipeline_result and isinstance(pipeline_result, dict) and "candidates" in pipeline_result:
                self._validate_and_sanitize_candidates(pipeline_result["candidates"], evidence)
                return pipeline_result
        except (ImportError, AttributeError):
            pass

        # 2. Extract per evidence item to guarantee accurate 1:1 quote attribution
        engine = self._get_engine()
        candidates = []
        candidate_counter = 1

        try:
            for ev in evidence:
                ev_id = ev["evidence_id"]
                ev_text = ev["text"]

                result = engine.extract(text=ev_text)
                if result.commitment_category.value == "no_commitment":
                    continue

                source_quote = getattr(result, "supporting_quotation", None) or getattr(result, "source_quote", None)
                if not source_quote:
                    # Default snippet from this exact file
                    source_quote = ev_text[:min(120, len(ev_text))]

                # Verbatim source quote validation against this SPECIFIC file
                if source_quote not in ev_text:
                    raise AIInvalidOutputError(
                        f"Model generated quote not found in source evidence '{ev_id}'."
                    )

                if len(source_quote) > 2000:
                    raise AIInvalidOutputError("Extracted source quote exceeds 2000 characters limit.")

                amt_minor = None
                if getattr(result, "amount", None) is not None:
                    if result.amount < 0:
                        raise AIInvalidOutputError("Model extracted a negative monetary amount.")
                    amt_minor = int(round(result.amount * 100))
                    if amt_minor < 0 or amt_minor > 9007199254740991:
                        raise AIInvalidOutputError("Extracted amount_minor out of allowable range (0 - 9007199254740991).")

                curr = getattr(result, "currency", None)
                if curr:
                    curr = curr.strip().upper()
                    if len(curr) != 3:
                        curr = None

                # Amount and currency pairing rule
                if (amt_minor is None and curr is not None) or (amt_minor is not None and curr is None):
                    amt_minor = None
                    curr = None

                kind_val = result.commitment_category.value
                if kind_val not in {"refund", "replacement", "service", "other"}:
                    kind_val = "other"

                cand_id = f"c{candidate_counter}"
                candidate_counter += 1

                candidates.append({
                    "candidate_id": cand_id,
                    "terms": {
                        "kind": kind_val,
                        "description": result.commitment_description[:2000].strip(),
                        "amount_minor": amt_minor,
                        "currency": curr,
                        "due_at": None
                    },
                    "sources": [
                        {
                            "evidence_id": ev_id,
                            "quote": source_quote
                        }
                    ],
                    "confidence": 0.95,
                    "warnings": result.missing_or_ambiguous_fields or [],
                    "revision": {
                        "relation": "new",
                        "supersedes_id": None,
                        "reason": "Initial commitment candidate"
                    }
                })

            return {
                "schema_version": 1,
                "candidates": candidates
            }

        except AIAdapterError:
            raise
        except Exception as e:
            try:
                from backend.app.ai.providers.base import (
                    AIAuthenticationError,
                    AIConnectionError,
                    AIRateLimitError,
                    AIResponseParsingError,
                )
                if isinstance(e, AIResponseParsingError):
                    raise AIInvalidOutputError(f"AI provider returned malformed output: {e}") from e
                if isinstance(e, (AIAuthenticationError, AIConnectionError, AIRateLimitError)):
                    raise AIServiceUnavailableError(f"AI provider service error: {e}", code="AI_UNAVAILABLE") from e
            except ImportError:
                pass

            err_str = str(e).lower()
            if isinstance(e, TimeoutError) or "timeout" in err_str or "timed out" in err_str:
                raise AITimeoutError(f"AI provider request timed out: {e}") from e
            elif "auth" in err_str or "key" in err_str or "unauthorized" in err_str:
                raise AIServiceUnavailableError(f"AI provider authentication failed: {e}", code="AI_UNAVAILABLE") from e
            elif "parse" in err_str or "json" in err_str or "schema" in err_str:
                raise AIInvalidOutputError(f"AI provider returned malformed output: {e}") from e
            else:
                raise AIServiceUnavailableError(f"AI provider error: {e}", code="AI_UNAVAILABLE") from e

    def _validate_and_sanitize_candidates(
        self,
        candidates: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]]
    ):
        """Validate candidate schema, candidate IDs, money values, and source attribution."""
        evidence_map = {e["evidence_id"]: e["text"] for e in evidence}
        valid_id_pattern = re.compile(r"^c[1-9][0-9]*$")

        for cand in candidates:
            cand_id = cand.get("candidate_id", "")
            if not valid_id_pattern.match(cand_id):
                raise AIInvalidOutputError(f"Candidate ID '{cand_id}' violates contract pattern '^c[1-9][0-9]*$'.")

            # Check money values
            terms = cand.get("terms", {})
            amt = terms.get("amount_minor")
            if amt is not None and (not isinstance(amt, int) or amt < 0 or amt > 9007199254740991):
                raise AIInvalidOutputError(f"Candidate '{cand_id}' contains invalid amount_minor: {amt}.")

            # Validate each source quote against its specific file
            sources = cand.get("sources", [])
            if not sources:
                raise AIInvalidOutputError(f"Candidate '{cand_id}' has no source citations.")

            for src in sources:
                eid = src.get("evidence_id")
                quote = src.get("quote", "")
                if eid not in evidence_map:
                    raise AIInvalidOutputError(f"Candidate '{cand_id}' cites evidence '{eid}' not in request.")
                if quote not in evidence_map[eid]:
                    raise AIInvalidOutputError(
                        f"Candidate '{cand_id}' quote is not a verbatim substring of cited evidence '{eid}'."
                    )

    def _mock_extraction_contract_response(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Explicitly labeled mock adapter output for development and unit testing."""
        first_ev = payload["evidence"][0]
        ev_id = first_ev["evidence_id"]
        text = first_ev["text"]
        snippet = text[:min(60, len(text))]

        return {
            "schema_version": 1,
            "candidates": [
                {
                    "candidate_id": "c1",
                    "terms": {
                        "kind": "refund",
                        "description": f"Extracted candidate promise: '{snippet}'",
                        "amount_minor": None,
                        "currency": None,
                        "due_at": None
                    },
                    "sources": [
                        {
                            "evidence_id": ev_id,
                            "quote": snippet
                        }
                    ],
                    "confidence": 0.90,
                    "warnings": ["Human confirmation required before saving"],
                    "revision": {
                        "relation": "new",
                        "supersedes_id": None,
                        "reason": "Development mock candidate"
                    }
                }
            ]
        }


ai_adapter = AIModuleAdapter()
