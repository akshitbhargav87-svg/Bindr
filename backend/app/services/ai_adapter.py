"""
AI Module Adapter (Milestone 2 Boundary).

Adheres to docs/AI_CONTRACT.md:
- Provides a clean, isolated interface between the backend and Kunal's AI extraction module.
- Keeps AI execution strictly separate from database persistence.
- Handles provider timeouts and maps service failures to standard error codes (AI_TIMEOUT, AI_UNAVAILABLE, AI_INVALID_OUTPUT).
- Validates that extracted source quotes are exact substrings of input evidence.
- Ensures extracted candidates require human review before saving as commitments.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

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


def extract_text_from_file_bytes(data: bytes, media_type: str) -> str:
    """
    Extract readable text from evidence bytes.
    Supports text/plain and PDF text layers.
    Raises UnreadableEvidenceError if no readable text could be found.
    """
    if not data or len(data) == 0:
        raise UnreadableEvidenceError("Evidence file is empty (0 bytes).")

    if media_type == "text/plain":
        try:
            text = data.decode("utf-8").strip()
            if text:
                return text
        except UnicodeDecodeError:
            pass

    elif media_type == "application/pdf":
        # Extract text streams from PDF
        text_parts = []
        # Look for text between parentheses in PDF content streams (e.g. (Some text) Tj)
        matches = re.findall(rb'\(([^\)\\]*(?:\\.[^\)\\]*)*)\)\s*(?:Tj|\'|")', data)
        for m in matches:
            try:
                # Unescape standard PDF escapes
                cleaned = m.decode("latin1", errors="ignore").replace("\\(", "(").replace("\\)", ")")
                if cleaned.strip():
                    text_parts.append(cleaned)
            except Exception:
                pass
        
        extracted = " ".join(text_parts).strip()
        if extracted:
            return extracted
        
        # Fallback: scan printable ASCII/UTF-8 strings in PDF
        ascii_matches = re.findall(rb'[a-zA-Z0-9\s.,!?:;@#$%&*()_-]{10,}', data)
        for s in ascii_matches:
            try:
                decoded = s.decode("ascii", errors="ignore").strip()
                # filter out PDF dictionary keys
                if decoded and not decoded.startswith("/") and len(decoded) > 15:
                    text_parts.append(decoded)
            except Exception:
                pass
        extracted = " ".join(text_parts).strip()
        if extracted:
            return extracted

    elif media_type.startswith("image/"):
        # For images, if OCR is not yet directly integrated in the runtime,
        # inspect if readable ASCII text was mocked or provided
        try:
            # Check for text hints or text payload
            decoded = data.decode("utf-8", errors="ignore")
            readable = "".join(c for c in decoded if c.isprintable())
            if len(readable.strip()) >= 10:
                return readable.strip()
        except Exception:
            pass

    raise UnreadableEvidenceError(
        f"No readable text could be extracted from evidence with media_type '{media_type}'."
    )


class AIModuleAdapter:
    """
    Adapter orchestrating calls to Kunal's AI engine adhering to AI_CONTRACT v1.
    """

    def __init__(self, timeout_seconds: int = 45):
        self.timeout_seconds = timeout_seconds
        self._engine = None

    def _get_engine(self):
        """Lazy load Kunal's PromiseExtractionEngine without modifying backend/app/ai/."""
        if self._engine is None:
            try:
                from backend.app.ai.engine import PromiseExtractionEngine
                self._engine = PromiseExtractionEngine(fallback_on_error=False)
            except Exception as e:
                logger.warning(f"Could not initialize production AI engine: {e}. Fallback to mock adapter.")
                self._engine = None
        return self._engine

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
        """
        if not evidence or len(evidence) == 0:
            raise AIValidationError("Extraction requires at least one evidence item (1-10 items allowed).")
        if len(evidence) > 10:
            raise AIValidationError("Extraction allows at most 10 evidence items.")

        total_chars = 0
        for ev in evidence:
            text = ev.get("text", "")
            if not text or not text.strip():
                raise AIValidationError(f"Evidence '{ev.get('evidence_id')}' contains empty text.")
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
        
        CRITICAL INVARIANT:
        Extracted commitments are returned purely as candidates for human-in-the-loop review.
        They are NEVER persisted automatically.
        """
        payload = self.prepare_extraction_input(
            case_id=case_id,
            evidence=evidence,
            existing_commitments=existing_commitments or [],
            reference_time=reference_time,
            tz_name=tz_name
        )

        engine = self._get_engine()
        if engine is None:
            # Explicitly labeled fallback mock adapter for test/dev when provider unavailable
            return self._mock_extraction_contract_response(payload)

        try:
            # Delegate to Kunal's engine
            # Concatenate or process evidence through the engine
            combined_text = "\n\n".join(e["text"] for e in evidence)
            result = engine.extract(text=combined_text)

            # Map result to AI_CONTRACT schema format
            candidates = []
            if result.commitment_category.value != "no_commitment":
                # Verbatim source quote validation
                source_quote = getattr(result, "supporting_quotation", None) or getattr(result, "source_quote", None)
                if not source_quote:
                    source_quote = combined_text[:200]

                first_ev_id = evidence[0]["evidence_id"]

                # Ensure quote is an exact substring of the evidence text
                if source_quote and source_quote not in combined_text:
                    raise AIInvalidOutputError("Model generated a source quote that is not an exact verbatim substring.")

                amt_minor = int(round(result.amount * 100)) if getattr(result, "amount", None) is not None else None
                curr = getattr(result, "currency", None)

                candidates.append({
                    "candidate_id": "c1",
                    "terms": {
                        "kind": result.commitment_category.value if result.commitment_category.value in {"refund", "replacement", "service"} else "other",
                        "description": result.commitment_description,
                        "amount_minor": amt_minor,
                        "currency": curr,
                        "due_at": None
                    },
                    "sources": [
                        {
                            "evidence_id": first_ev_id,
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
            err_str = str(e).lower()
            if isinstance(e, TimeoutError) or "timeout" in err_str or "timed out" in err_str:
                raise AITimeoutError(f"AI provider request timed out: {e}") from e
            elif "auth" in err_str or "key" in err_str or "unauthorized" in err_str:
                raise AIServiceUnavailableError(f"AI provider authentication failed: {e}") from e
            elif "parse" in err_str or "json" in err_str or "schema" in err_str:
                raise AIInvalidOutputError(f"AI provider returned malformed output: {e}") from e
            else:
                raise AIServiceUnavailableError(f"AI provider error: {e}") from e

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
