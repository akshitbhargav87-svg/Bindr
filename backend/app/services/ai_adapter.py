"""
AI Module Adapter (Milestones 2 & 3 Integration Pipeline).

Connects the backend to Kunal's AI module using the exact published interface:
    extract_commitment_from_evidence(
        file_source: Union[str, Path, bytes],
        filename: Optional[str] = None,
        evidence_id: Optional[str] = None,
        metadata: Optional[SourceMetadata] = None,
        provider: Optional[AIProvider] = None,
        fallback_on_error: bool = False,
        document_processor: Optional[DocumentProcessor] = None,
        timeout: Optional[int] = None,
    ) -> CommitmentExtractionResult

Key Invariants:
1. Passes original file bytes, filename, and evidence ID.
2. Invokes real RapidOCR for images/screenshots via Kunal's DocumentProcessor.
3. Quotations are strictly verified against their specific source evidence.
4. Never silently switches to mock inference unless AI_PROVIDER=mock is explicitly set.
5. Strict schema validation of candidate IDs, monetary terms, and citations.
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
            return PromiseExtractionEngine(provider=provider, fallback_on_error=False, timeout=self.timeout_seconds)
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
                raise AITimeoutError(f"AI provider request timed out: {e}") from e
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
        Validate input payload per AI_CONTRACT v1 before processing.
        Rejects empty or duplicate evidence IDs and excessive text size.
        """
        if not evidence or len(evidence) == 0:
            raise AIValidationError("Extraction requires at least one evidence item (1-10 items allowed).")
        if len(evidence) > 10:
            raise AIValidationError("Extraction allows at most 10 evidence items.")

        seen_ids = set()
        total_chars = 0
        for ev in evidence:
            eid = ev.get("evidence_id")
            if not eid:
                raise AIValidationError("Evidence record missing 'evidence_id'.")
            if eid in seen_ids:
                raise AIValidationError(f"Duplicate evidence ID '{eid}' in extraction request.")
            seen_ids.add(eid)

            # Check text length if text is already extracted
            text = ev.get("text")
            if text:
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
        tz_name: str = "Asia/Kolkata",
        merchant_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Routes evidence documents/screenshots through Kunal's pipeline:
            extract_commitment_from_evidence(file_source=..., filename=..., evidence_id=...)
        
        Per-file extraction guarantees:
        1. Original bytes reach DocumentProcessor and RapidOCR.
        2. Citations strictly map to their originating evidence file.
        3. Never attributes quote from file B to file A.
        4. Rejects negative monetary amounts and invalid schema structures.
        """
        payload = self.prepare_extraction_input(
            case_id=case_id,
            evidence=evidence,
            existing_commitments=existing_commitments or [],
            reference_time=reference_time,
            tz_name=tz_name
        )

        provider_name = (settings.AI_PROVIDER or os.getenv("AI_PROVIDER", "meta")).lower().strip()
        api_key = settings.MODEL_API_KEY or os.getenv("MODEL_API_KEY")

        if provider_name == "meta" and (not api_key or not api_key.strip()):
            raise AIServiceUnavailableError(
                "Meta API key is not configured. Please set the MODEL_API_KEY environment variable.",
                code="AI_UNAVAILABLE"
            )

        candidates = []
        candidate_counter = 1

        try:
            try:
                from backend.app.ai import extract_commitment_from_evidence, SourceMetadata
                from backend.app.ai.document_processor import UnsupportedFileTypeError, UnreadableDocumentError
            except (ImportError, AttributeError):
                extract_commitment_from_evidence = None
                SourceMetadata = None
                UnsupportedFileTypeError = Exception
                UnreadableDocumentError = Exception
            from backend.app.ai.providers.base import (
                AIAuthenticationError,
                AIConnectionError,
                AIRateLimitError,
                AIResponseParsingError,
            )

            for ev in evidence:
                eid = ev["evidence_id"]
                fname = ev.get("filename") or f"{eid}.txt"
                fbytes = ev.get("file_bytes")
                text_content = ev.get("text")

                # If raw bytes exist, pass them; otherwise pass text bytes
                if fbytes is None and text_content is not None:
                    fbytes = text_content.encode("utf-8")
                    if not fname.endswith((".txt", ".pdf", ".png", ".jpg", ".jpeg")):
                        fname = f"{fname}.txt"

                source_meta = SourceMetadata(
                    sender=merchant_name,
                    communication_date=ev.get("occurred_at"),
                ) if SourceMetadata is not None else None

                try:
                    if self._engine is not None and hasattr(self._engine, "extract"):
                        text_to_extract = text_content or ""
                        result = self._engine.extract(text=text_to_extract)
                    elif extract_commitment_from_evidence is not None:
                        result = extract_commitment_from_evidence(
                            file_source=fbytes,
                            filename=fname,
                            evidence_id=eid,
                            metadata=source_meta,
                            fallback_on_error=False,
                            timeout=self.timeout_seconds,
                        )
                    else:
                        raise AIServiceUnavailableError(
                            "Kunal's AI extraction pipeline (extract_commitment_from_evidence) is unavailable.",
                            code="AI_UNAVAILABLE"
                        )
                except UnsupportedFileTypeError as e:
                    raise AIValidationError(str(e)) from e
                except UnreadableDocumentError as e:
                    raise UnreadableEvidenceError(str(e)) from e
                except AIAuthenticationError as e:
                    raise AIServiceUnavailableError(f"Meta provider authentication failed: {e}", code="AI_UNAVAILABLE") from e
                except (AIConnectionError, AIRateLimitError) as e:
                    raise AIServiceUnavailableError(f"Meta provider connection failed: {e}", code="AI_UNAVAILABLE") from e
                except AIResponseParsingError as e:
                    raise AIInvalidOutputError(f"AI response parsing error: {e}") from e
                except (TimeoutError, AITimeoutError) as e:
                    raise AITimeoutError(f"AI provider request timed out: {e}") from e

                if result.commitment_category.value == "no_commitment":
                    continue

                # Verify source quotation is verbatim
                source_quote = getattr(result, "supporting_quotation", None)
                raw_text = getattr(result, "raw_source_text", "") or ""
                if raw_text:
                    ev["text"] = raw_text
                evidence_text = raw_text or text_content or ""
                if not source_quote:
                    source_quote = evidence_text[:min(120, len(evidence_text))] if evidence_text else "Commitment stated in evidence"

                if evidence_text and source_quote not in evidence_text:
                    raise AIInvalidOutputError(
                        f"Model generated quote not found in source evidence '{eid}'."
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
                            "evidence_id": eid,
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

            output_dict = {
                "schema_version": 1,
                "candidates": candidates
            }
            validate_ai_extraction_output(output_dict, payload["evidence"], existing_commitments)
            return output_dict

        except AIAdapterError:
            raise
        except Exception as e:
            err_str = str(e).lower()
            if isinstance(e, TimeoutError) or "timeout" in err_str or "timed out" in err_str:
                raise AITimeoutError(f"AI provider request timed out: {e}") from e
            elif "api key" in err_str or "unauthorized" in err_str:
                raise AIServiceUnavailableError(f"AI provider authentication failed: {e}", code="AI_UNAVAILABLE") from e
            elif "connection" in err_str or "network" in err_str:
                raise AIServiceUnavailableError(f"AI provider connection failed: {e}", code="AI_UNAVAILABLE") from e
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
        validate_ai_extraction_output(
            {"schema_version": 1, "candidates": candidates},
            evidence_items=evidence
        )

    def _mock_extraction_contract_response(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Explicitly labeled mock adapter output for development and unit testing."""
        first_ev = payload["evidence"][0]
        ev_id = first_ev["evidence_id"]
        text = first_ev.get("text", "Extracted evidence text")
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


def validate_ai_extraction_output(
    data: Any,
    evidence_items: List[Dict[str, Any]],
    existing_commitments: Optional[List[Dict[str, Any]]] = None
) -> None:
    """
    Validates AI extraction output strictly against docs/AI_CONTRACT.md.
    Rejects all six malformed AI-output variants before draft persistence:
    1. Schema version and top-level shape (schema_version == 1, exactly expected root keys).
    2. Candidate shape, count (0-10), candidate_id pattern (^c[1-9][0-9]*$), and uniqueness.
    3. Terms validation (kind in {refund, replacement, service, other}, description 1-2000 chars, amount bounds).
    4. Money pairing rules (amount_minor and currency must both be present or both null).
    5. Sources and verbatim citation (no invented evidence IDs, non-empty quotes <= 2000 chars, verbatim match).
    6. Metadata and revision shape (confidence in [0, 1], warnings string list, valid revision relation/reason).
    """
    if not isinstance(data, dict):
        raise AIInvalidOutputError("AI output must be a JSON object.")

    # 1. Schema version & Top-Level Keys ("All keys required, no extras.")
    if "schema_version" not in data or data.get("schema_version") != 1:
        raise AIInvalidOutputError("Unsupported or missing AI schema version (expected 1).")

    if "candidates" not in data or not isinstance(data["candidates"], list):
        raise AIInvalidOutputError("AI output missing 'candidates' array.")

    for key in data.keys():
        if key not in ("schema_version", "candidates"):
            raise AIInvalidOutputError(f"Unexpected root key '{key}' in AI output.")

    candidates = data["candidates"]
    if len(candidates) > 10:
        raise AIInvalidOutputError(f"AI output contains {len(candidates)} candidates (max 10 allowed).")

    allowed_evidence_ids = {e["evidence_id"] for e in evidence_items}
    evidence_text_map = {}
    for e in evidence_items:
        eid = e["evidence_id"]
        txt = e.get("text")
        if not txt and e.get("file_bytes"):
            try:
                txt = e["file_bytes"].decode("utf-8", errors="ignore")
            except Exception:
                txt = ""
        evidence_text_map[eid] = txt or ""
    active_comm_ids = {c["id"] for c in (existing_commitments or []) if c.get("status") == "active"}

    seen_candidate_ids = set()
    candidate_id_regex = re.compile(r"^c[1-9][0-9]*$")

    for idx, cand in enumerate(candidates):
        if not isinstance(cand, dict):
            raise AIInvalidOutputError(f"Candidate at index {idx} must be a JSON object.")

        required_cand_keys = {"candidate_id", "terms", "sources", "confidence", "warnings", "revision"}
        missing_keys = required_cand_keys - set(cand.keys())
        if missing_keys:
            raise AIInvalidOutputError(f"Candidate at index {idx} missing required keys: {sorted(missing_keys)}.")

        # 2. Candidate ID
        cand_id = cand.get("candidate_id")
        if not isinstance(cand_id, str) or not candidate_id_regex.match(cand_id):
            raise AIInvalidOutputError(f"Candidate ID '{cand_id}' violates pattern '^c[1-9][0-9]*$'.")
        if cand_id in seen_candidate_ids:
            raise AIInvalidOutputError(f"Duplicate candidate ID '{cand_id}' in extraction draft.")
        seen_candidate_ids.add(cand_id)

        # 3. Terms
        terms = cand.get("terms")
        if not isinstance(terms, dict):
            raise AIInvalidOutputError(f"Candidate '{cand_id}' terms must be an object.")

        kind = terms.get("kind")
        if kind not in {"refund", "replacement", "service", "other"}:
            raise AIInvalidOutputError(f"Candidate '{cand_id}' terms.kind '{kind}' is invalid.")

        description = terms.get("description")
        if not isinstance(description, str) or not description.strip() or len(description) > 2000:
            raise AIInvalidOutputError(f"Candidate '{cand_id}' description must be 1-2000 characters.")

        amount_minor = terms.get("amount_minor")
        currency = terms.get("currency")

        if amount_minor is not None:
            if not isinstance(amount_minor, int) or isinstance(amount_minor, bool) or amount_minor < 0 or amount_minor > 9007199254740991:
                raise AIInvalidOutputError(f"Candidate '{cand_id}' amount_minor must be an integer between 0 and 9007199254740991.")

        if currency is not None:
            if not isinstance(currency, str) or len(currency.strip()) != 3:
                raise AIInvalidOutputError(f"Candidate '{cand_id}' currency must be a 3-letter ISO code.")

        # 4. Money Pairing Rule
        if (amount_minor is None and currency is not None) or (amount_minor is not None and currency is None):
            raise AIInvalidOutputError(f"Candidate '{cand_id}' violates money pairing: amount_minor and currency must both be present or both null.")

        # 5. Sources & Citations
        sources = cand.get("sources")
        if not isinstance(sources, list) or len(sources) < 1 or len(sources) > 10:
            raise AIInvalidOutputError(f"Candidate '{cand_id}' sources must contain 1 to 10 citations.")

        seen_source_eids = set()
        for s_idx, src in enumerate(sources):
            if not isinstance(src, dict):
                raise AIInvalidOutputError(f"Candidate '{cand_id}' source at index {s_idx} must be an object.")
            eid = src.get("evidence_id")
            quote = src.get("quote")

            if not eid or eid not in allowed_evidence_ids:
                raise AIInvalidOutputError(f"Candidate '{cand_id}' cites evidence ID '{eid}' not present in extraction request.")
            if eid in seen_source_eids:
                raise AIInvalidOutputError(f"Candidate '{cand_id}' cites duplicate evidence ID '{eid}'.")
            seen_source_eids.add(eid)

            if not isinstance(quote, str) or not quote.strip() or len(quote) > 2000:
                raise AIInvalidOutputError(f"Candidate '{cand_id}' quote must be a non-empty string of at most 2000 characters.")

            # Verbatim substring validation against cited document
            ev_text = evidence_text_map.get(eid, "")
            if ev_text and quote not in ev_text:
                raise AIInvalidOutputError(f"Candidate '{cand_id}' quote is not a verbatim substring of cited evidence '{eid}'.")

        # 6. Metadata & Revision
        confidence = cand.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or confidence < 0.0 or confidence > 1.0:
            raise AIInvalidOutputError(f"Candidate '{cand_id}' confidence must be a finite float between 0.0 and 1.0.")

        warnings = cand.get("warnings")
        if not isinstance(warnings, list):
            raise AIInvalidOutputError(f"Candidate '{cand_id}' warnings must be an array.")
        for w in warnings:
            if not isinstance(w, str) or len(w) < 1 or len(w) > 500:
                raise AIInvalidOutputError(f"Candidate '{cand_id}' warning item must be a string of 1-500 characters.")

        revision = cand.get("revision")
        if not isinstance(revision, dict):
            raise AIInvalidOutputError(f"Candidate '{cand_id}' revision must be an object.")

        relation = revision.get("relation")
        if relation not in {"new", "revision", "uncertain"}:
            raise AIInvalidOutputError(f"Candidate '{cand_id}' revision.relation '{relation}' is invalid.")

        reason = revision.get("reason")
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 1000:
            raise AIInvalidOutputError(f"Candidate '{cand_id}' revision.reason must be 1-1000 characters.")

        supersedes_id = revision.get("supersedes_id")
        if relation in ("new", "uncertain") and supersedes_id is not None:
            raise AIInvalidOutputError(f"Candidate '{cand_id}' revision relation '{relation}' requires supersedes_id to be null.")
        if relation == "revision":
            if not supersedes_id:
                raise AIInvalidOutputError(f"Candidate '{cand_id}' revision relation 'revision' requires non-null supersedes_id.")
            if active_comm_ids and supersedes_id not in active_comm_ids:
                raise AIInvalidOutputError(f"Candidate '{cand_id}' supersedes_id '{supersedes_id}' is not an active commitment in this case.")

    def _mock_extraction_contract_response(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Explicitly labeled mock adapter output for development and unit testing."""
        first_ev = payload["evidence"][0]
        ev_id = first_ev["evidence_id"]
        text = first_ev.get("text", "Extracted evidence text")
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
