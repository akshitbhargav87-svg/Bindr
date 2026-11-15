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
import math
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from time import monotonic
from uuid import uuid4
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

    def extract_proposals_v2(self, request, *, provider=None, diagnostics=None):
        """Data-only v2 seam: proposals only, no auth, database or storage effects.

        A must authorize the snapshot before calling. A test provider must be injected
        explicitly; v2 never silently changes a real request to mock inference.
        """
        from backend.app.services.intelligence.extraction import ProposalEngine
        from backend.app.ai.proposals import StructuredProposalProvider
        platform_request = request if isinstance(request, dict) and 'context' in request else None
        if platform_request is not None:
            from backend.app.services.intelligence.platform_profile import extraction_request
            request = extraction_request(platform_request)
        if provider is None:
            adapter = self
            class ConfiguredProvider:
                def extract_proposals(self, payload, timeout):
                    return StructuredProposalProvider(adapter._get_engine().provider).extract_proposals(payload, timeout)
            provider = ConfiguredProvider()
        result = ProposalEngine(provider).extract(request, diagnostics)
        if platform_request is not None:
            from backend.app.services.intelligence.platform_profile import extraction_response
            return extraction_response(result, platform_request)
        return result

    def answer_case_v2(self, request):
        """Answer only from A's already authorized bounded source snapshot."""
        from backend.app.services.intelligence.platform_profile import answer_request
        return answer_request(request)

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
                    raise AIServiceUnavailableError("AI provider authentication is unavailable.", code="AI_UNAVAILABLE") from e
                elif isinstance(e, (AIConnectionError, AIRateLimitError)):
                    raise AIServiceUnavailableError("AI provider service is unavailable.", code="AI_UNAVAILABLE") from e
                elif isinstance(e, AIResponseParsingError):
                    raise AIInvalidOutputError("AI provider returned malformed output.") from e
            except ImportError:
                pass

            err_str = str(e).lower()
            if isinstance(e, TimeoutError) or "timeout" in err_str or "timed out" in err_str:
                raise AITimeoutError("AI provider request timed out.") from e
            elif "api key" in err_str or "unauthorized" in err_str:
                raise AIServiceUnavailableError("AI provider authentication is unavailable.", code="AI_UNAVAILABLE") from e
            elif "connection" in err_str or "network" in err_str:
                raise AIServiceUnavailableError("AI provider connection failed.", code="AI_UNAVAILABLE") from e
            else:
                raise AIServiceUnavailableError("AI provider initialization failed.", code="AI_UNAVAILABLE") from e

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
        total_extracted_chars = 0
        started, trace_id = monotonic(), uuid4().hex

        try:
            try:
                from backend.app.ai import SourceMetadata
                from backend.app.ai.batch import extract_all_from_evidence as extract_commitment_from_evidence
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
                remaining = self.timeout_seconds - (monotonic() - started)
                if remaining <= 0:
                    raise AITimeoutError("The extraction request budget elapsed. Originals are retained.")
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
                    extra={"request_id": trace_id},
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
                            provider=self._get_engine().provider,
                            fallback_on_error=False,
                            timeout=max(1, int(remaining)),
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
                    raise AIServiceUnavailableError("AI provider authentication is unavailable.", code="AI_UNAVAILABLE") from e
                except (AIConnectionError, AIRateLimitError) as e:
                    if "timed out" in str(e).lower() or "timeout" in str(e).lower():
                        raise AITimeoutError("AI provider request timed out.") from e
                    raise AIServiceUnavailableError("AI provider connection failed.", code="AI_UNAVAILABLE") from e
                except AIResponseParsingError as e:
                    raise AIInvalidOutputError("AI response parsing failed.") from e
                except (TimeoutError, AITimeoutError) as e:
                    raise AITimeoutError("AI provider request timed out.") from e

                batch_results = result if isinstance(result, list) else [result]
                result = batch_results[0]
                raw_text = getattr(result, "raw_source_text", "") or text_content or ""
                if not raw_text.strip():
                    raise UnreadableEvidenceError("No readable text could be extracted from the evidence.")
                ev["text"] = raw_text
                total_extracted_chars += len(raw_text)
                if total_extracted_chars > 50000:
                    raise AIValidationError("Total evidence text exceeds 50,000 characters limit.")
                for result in batch_results:
                    if result.commitment_category.value == "no_commitment":
                        continue

                    # Verify source quotation is verbatim
                    source_quote = getattr(result, "supporting_quotation", None)
                    raw_text = getattr(result, "raw_source_text", "") or ""
                    if raw_text:
                        ev["text"] = raw_text
                    evidence_text = raw_text or text_content or ""
                    if not source_quote:
                        raise AIInvalidOutputError("A commitment candidate requires an exact source quotation.")

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
                        try:
                            decimal_amount = Decimal(str(result.amount))
                            if not decimal_amount.is_finite():
                                raise AIInvalidOutputError("Extracted amount must be finite.")
                            amt_minor = int((decimal_amount * 100).quantize(Decimal("1")))
                        except (InvalidOperation, ValueError, OverflowError) as exc:
                            raise AIInvalidOutputError("Extracted amount is invalid.") from exc
                        if amt_minor < 0 or amt_minor > 9007199254740991:
                            raise AIInvalidOutputError("Extracted amount_minor out of allowable range (0 - 9007199254740991).")

                    curr = getattr(result, "currency", None)
                    curr = {"₹": "INR", "RS": "INR", "RS.": "INR", "$": "USD", "€": "EUR", "£": "GBP"}.get((curr or "").strip().upper(), curr)
                    if curr:
                        curr = curr.strip().upper()
                        if not re.fullmatch(r"[A-Z]{3}", curr):
                            curr = None

                    # Amount and currency pairing rule
                    if (amt_minor is None and curr is not None) or (amt_minor is not None and curr is None):
                        amt_minor = None
                        curr = None

                    kind_val = result.commitment_category.value
                    if kind_val not in {"refund", "replacement", "service", "other"}:
                        kind_val = "other"

                    warnings = list(result.missing_or_ambiguous_fields or [])
                    warnings.append("AI suggestions require your review; confidence is not calibrated.")
                    if provider_name == "mock":
                        warnings.append("Offline rule-based extraction; no live AI provider was used.")
                    due_at = _confirmed_deadline(result, ev.get("occurred_at"), warnings)
                    revision = {"relation": "new", "supersedes_id": None, "reason": "Initial commitment candidate"}
                    active = [c for c in (existing_commitments or []) if c.get("status") == "active"]
                    if active:
                        revision = {"relation": "uncertain", "supersedes_id": None, "reason": "Existing promises are on record; confirm whether this message revises one or adds a separate promise."}
                    cand_id = f"c{candidate_counter}"
                    candidate_counter += 1

                    candidates.append({
                        "candidate_id": cand_id,
                        "terms": {
                            "kind": kind_val,
                            "description": result.commitment_description[:2000].strip(),
                            "amount_minor": amt_minor,
                            "currency": curr,
                            "due_at": due_at
                        },
                        "sources": [
                            {
                                "evidence_id": eid,
                                "quote": source_quote
                            }
                        ],
                        "confidence": 0.0,
                        "warnings": list(dict.fromkeys(warnings)),
                        "revision": revision
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
            from backend.app.services.intelligence.extraction import IntelligenceFailure
            if isinstance(e, IntelligenceFailure):
                error_type = {"AI_TIMEOUT": AITimeoutError, "AI_INVALID_OUTPUT": AIInvalidOutputError,
                              "VALIDATION_ERROR": AIValidationError}.get(e.code, AIServiceUnavailableError)
                raise error_type(str(e)) from None
            err_str = str(e).lower()
            if isinstance(e, TimeoutError) or "timeout" in err_str or "timed out" in err_str:
                raise AITimeoutError("AI provider request timed out.") from e
            elif "api key" in err_str or "unauthorized" in err_str:
                raise AIServiceUnavailableError("AI provider authentication failed.", code="AI_UNAVAILABLE") from e
            elif "connection" in err_str or "network" in err_str:
                raise AIServiceUnavailableError("AI provider connection failed.", code="AI_UNAVAILABLE") from e
            elif "parse" in err_str or "json" in err_str or "schema" in err_str:
                raise AIInvalidOutputError("AI provider returned malformed output.") from e
            else:
                raise AIServiceUnavailableError("AI provider request failed.", code="AI_UNAVAILABLE") from e

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


def _confirmed_deadline(result, occurred_at, warnings):
    """Resolve only explicit timezone-aware instants or anchored elapsed durations.

    Date-only deadlines, business-day calendars and unknown communication dates
    remain editable suggestions requiring human confirmation (AI_CONTRACT v1).
    """
    from backend.app.services.intelligence.extraction import _impossible_date
    source = getattr(result, "raw_source_text", "") or ""
    if _impossible_date(source):
        warnings.append("Impossible source date. Confirm the intended date; no normalization was applied.")
        return None
    if re.search(r"\bif\b.*\b(?:confirm|approv|receiv)", source, re.I | re.S):
        warnings.append("Conditional trigger is unconfirmed. A message date cannot establish that it occurred.")
        return None
    deadline = getattr(result, "deadline", None)
    if deadline is None:
        warnings.append("No confirmed deadline; add a date during review.")
        return None
    kind = getattr(deadline.deadline_type, "value", deadline.deadline_type)
    raw = deadline.absolute_date if kind == "absolute_date" else None
    try:
        if raw and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})", raw):
            instant = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return instant.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if kind == "duration" and occurred_at and deadline.duration_unit in {"hours", "calendar_days", "weeks"}:
            # A range's upper bound is only a suggestion, clearly explained.
            amount = deadline.duration_value_max or deadline.duration_value
            if amount is not None and math.isfinite(amount) and 0 <= amount <= 3650:
                anchor = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
                if anchor.tzinfo is not None:
                    delta = timedelta(**{{"hours": "hours", "calendar_days": "days", "weeks": "weeks"}[deadline.duration_unit]: amount})
                    if deadline.duration_value_max is not None:
                        warnings.append("Deadline uses the stated range's upper bound; confirm during review.")
                    return (anchor + delta).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, OverflowError, TypeError):
        pass
    if kind != "none":
        text = deadline.raw_deadline_text or raw or "Stated timeframe"
        warnings.append(f"Confirm deadline and timezone: {text}"[:500])
    else:
        warnings.append("No confirmed deadline; add a date during review.")
    return None


def validate_ai_extraction_output(data, evidence_items, existing_commitments=None):
    """Reject malformed adapter output before any draft is persisted."""
    def fail(message):
        raise AIInvalidOutputError(message)
    def shape(value, keys, label):
        if not isinstance(value, dict) or set(value) != set(keys):
            fail(f"{label} must contain exactly the required keys.")
    shape(data, {"schema_version", "candidates"}, "AI output")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        fail("Unsupported AI schema version.")
    candidates = data["candidates"]
    if not isinstance(candidates, list) or len(candidates) > 10:
        fail("Candidates must be an array of at most 10 items.")
    texts = {}
    for ev in evidence_items:
        text = ev.get("text")
        if text is None and ev.get("file_bytes") and ev.get("media_type", "text/plain") == "text/plain":
            try:
                text = ev["file_bytes"].decode("utf-8")
            except UnicodeDecodeError:
                text = ""
        texts[ev["evidence_id"]] = text or ""
    active_ids = {c["id"] for c in (existing_commitments or []) if c.get("status") == "active"}
    seen = set()
    for cand in candidates:
        shape(cand, {"candidate_id", "terms", "sources", "confidence", "warnings", "revision"}, "Candidate")
        cid = cand["candidate_id"]
        if not isinstance(cid, str) or not re.fullmatch(r"c[1-9][0-9]*", cid) or cid in seen:
            fail("Invalid or duplicate candidate ID.")
        seen.add(cid)
        terms = cand["terms"]
        shape(terms, {"kind", "description", "amount_minor", "currency", "due_at"}, "Terms")
        if terms["kind"] not in {"refund", "replacement", "service", "other"}:
            fail("Invalid commitment kind.")
        if not isinstance(terms["description"], str) or not 1 <= len(terms["description"].strip()) <= 2000:
            fail("Invalid commitment description.")
        amount, currency = terms["amount_minor"], terms["currency"]
        if amount is not None and (type(amount) is not int or not 0 <= amount <= 9007199254740991):
            fail("amount_minor must be a nonnegative safe integer.")
        if currency is not None and (not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency)):
            fail("Currency must be an uppercase ISO code.")
        if (amount is None) != (currency is None):
            fail("Amount and currency must both be present or both null.")
        due = terms["due_at"]
        if due is not None:
            if not isinstance(due, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", due):
                fail("due_at must be a UTC timestamp or null.")
            try:
                datetime.fromisoformat(due.replace("Z", "+00:00"))
            except ValueError:
                fail("Invalid calendar timestamp.")
        sources = cand["sources"]
        if not isinstance(sources, list) or not 1 <= len(sources) <= 10:
            fail("Candidate requires 1-10 sources.")
        source_ids = set()
        for source in sources:
            shape(source, {"evidence_id", "quote"}, "Source")
            eid, quote = source["evidence_id"], source["quote"]
            if not isinstance(eid, str) or eid not in texts or eid in source_ids:
                fail("Source must reference unique evidence from this extraction.")
            source_ids.add(eid)
            if not isinstance(quote, str) or not 1 <= len(quote) <= 2000 or not quote.strip():
                fail("Source quote must be nonempty and at most 2000 characters.")
            if not texts[eid] or quote not in texts[eid]:
                fail("Quote is not a verbatim substring of its cited evidence.")
        score = cand["confidence"]
        if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
            fail("Confidence must be finite and between 0 and 1.")
        warnings = cand["warnings"]
        if not isinstance(warnings, list) or any(not isinstance(w, str) or not 1 <= len(w) <= 500 for w in warnings):
            fail("Invalid warning array.")
        rev = cand["revision"]
        shape(rev, {"relation", "supersedes_id", "reason"}, "Revision")
        if rev["relation"] not in {"new", "revision", "uncertain"}:
            fail("Invalid revision relation.")
        if not isinstance(rev["reason"], str) or not 1 <= len(rev["reason"].strip()) <= 1000:
            fail("Invalid revision explanation.")
        if rev["relation"] == "revision":
            if not isinstance(rev["supersedes_id"], str) or rev["supersedes_id"] not in active_ids:
                fail("Revision must reference an active commitment in this case.")
        elif rev["supersedes_id"] is not None:
            fail("New or uncertain revision must not name a predecessor.")


ai_adapter = AIModuleAdapter()
