"""One bounded provider operation, strict grounding, safe request-stage diagnostics."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from hashlib import sha256
import json
import logging
import re
from time import monotonic
from pydantic import ValidationError
from .contracts import ProposalRequest, Proposal

log = logging.getLogger(__name__)


class IntelligenceFailure(Exception):
    def __init__(self, code, stage, request_id, retryable=False):
        self.code, self.stage, self.request_id, self.retryable = code, stage, request_id, retryable
        super().__init__({"AI_TIMEOUT": "Extraction timed out. Your source is retained; retry explicitly.",
                          "AI_INVALID_OUTPUT": "The model response could not be validated. Review manually or retry.",
                          "AI_UNAVAILABLE": "Extraction is unavailable. Review manually or retry later.",
                          "VALIDATION_ERROR": "Review the source metadata and processing limits."}.get(code, code))


@contextmanager
def stage(name, request_id, diagnostics):
    start = monotonic()
    try:
        yield
    finally:
        entry = {"stage": name, "request_id": request_id, "duration_ms": round((monotonic()-start)*1000)}
        diagnostics.append(entry)
        # Only allowlisted fields, never raw text, provider exceptions or credentials.
        log.info("intelligence_stage %s", json.dumps(entry))


def _impossible_date(text):
    months = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
              "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
              "november": 11, "december": 12}
    for m in re.finditer(r"\b(" + "|".join(months) + r")\s+(\d{1,2}),?\s+(\d{4})\b", text.lower()):
        try:
            date(int(m[3]), months[m[1]], int(m[2]))
        except ValueError:
            return True
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        try:
            date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return True
    return False


def validate_grounding(result, request):
    evidence = {e.evidence_id: e for e in request.evidence}
    predecessors = {o["id"] for o in request.existing_obligations if isinstance(o.get("id"), str)}
    seen = set()
    for c in result.candidates:
        if c.candidate_id in seen:
            raise ValueError("Duplicate candidate identity.")
        seen.add(c.candidate_id)
        quotes = []
        for s in c.sources:
            source = evidence.get(s.evidence_id)
            if source is None:
                raise ValueError("Citation outside authorized source snapshot.")
            matches = [p for p in source.segments if s.quote in p.text
                       and all(getattr(s, k) == getattr(p, k) for k in ("page", "message_id", "start_ms", "end_ms"))]
            if not matches:
                raise ValueError("Citation text or location does not match source.")
            quotes.append(s.quote)
        if c.relation.predecessor_id is not None and c.relation.predecessor_id not in predecessors:
            raise ValueError("Predecessor outside authorized case snapshot.")
        exact = "\n".join(quotes)
        anchors={evidence[s.evidence_id].communication.date for s in c.sources}
        if c.temporal.anchor is not None and c.temporal.anchor not in exact and c.temporal.anchor not in anchors:
            raise ValueError("Candidate anchor does not match the supplied source metadata or wording.")
        if c.terms.amount_minor is not None:
            currency = c.terms.currency
            exponent = {"JPY": 0, "KRW": 0, "VND": 0, "BHD": 3, "JOD": 3, "KWD": 3, "OMR": 3, "TND": 3}.get(currency, 2)
            symbols = {"INR": ["₹", "INR", "Rs", "Rs."], "USD": ["USD", "$"],
                       "EUR": ["EUR", "€"], "GBP": ["GBP", "£"], "JPY": ["JPY", "¥"]}.get(currency, [currency])
            tokens = "|".join(re.escape(s) for s in symbols)
            found = re.findall(r"(?:"+tokens+r")\s*([0-9][0-9,]*(?:\.[0-9]+)?)", exact, re.I)
            found += re.findall(r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:"+tokens+r")\b", exact, re.I)
            if not any(Decimal(n.replace(",", "")) * (10 ** exponent) == c.terms.amount_minor for n in found):
                raise ValueError("Proposed amount/currency is not grounded in its cited quotation.")
        for fragment in (c.temporal.wording, c.temporal.duration, c.temporal.range, c.condition.trigger):
            if fragment is not None and fragment not in exact:
                raise ValueError("Temporal or condition wording must be verbatim.")
        if _impossible_date(exact):
            c.terms.due_at = None
            c.temporal.parse_status = "invalid"
            c.warnings.append("Impossible source date. Confirm the intended date; no normalization was applied.")
        if c.temporal.parse_status != "explicit" or c.condition.status == "unknown":
            c.terms.due_at = None
        if c.condition.trigger is not None:
            # A model cannot establish occurrence of a trigger. A's confirmed event is required.
            c.condition.status = "unknown"
            c.terms.due_at = None
        if c.relation.kind == "cancellation":
            c.terms.due_at = None
            c.warnings.append("Company cancellation claim: historical promise retained; your decision is required.")
        from .relations import check_relation
        check_relation(c, request)
        c.candidate_id = "c-" + sha256(json.dumps({"terms": c.terms.model_dump(),
                                                  "sources": [s.model_dump() for s in c.sources]},
                                                 sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
    unique = {}
    for c in result.candidates:
        unique.setdefault(c.candidate_id, c)
    if len(unique) != len(result.candidates):
        result.document_warnings.append("Repeated identical proposals from the same source were deduplicated.")
        result.candidates = list(unique.values())
    return Proposal.model_validate(result.model_dump())


class ProposalEngine:
    def __init__(self, provider):
        self.provider = provider

    def extract(self, request, diagnostics=None):
        diagnostics = diagnostics if diagnostics is not None else []
        request_id = request.get("request_id", "unvalidated") if isinstance(request, dict) else request.request_id
        if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", request_id):
            request_id = "unvalidated"
        try:
            with stage("input", request_id, diagnostics):
                req = request if isinstance(request, ProposalRequest) else ProposalRequest.model_validate(request)
        except (ValidationError, ValueError, KeyError, TypeError):
            raise IntelligenceFailure("VALIDATION_ERROR", "input", request_id) from None
        try:
            with stage("provider", request_id, diagnostics):
                started = monotonic()
                raw = self.provider.extract_proposals(req.model_dump(), timeout=req.timeout_seconds)
                if monotonic()-started > req.timeout_seconds:
                    raise TimeoutError()
            with stage("validation", request_id, diagnostics):
                result = Proposal.model_validate(raw)
                result = validate_grounding(result, req)
                # Stable identity derived from validated content; never trust provider IDs as authority.
                content = json.dumps(result.model_dump(exclude={"proposal_id"}), sort_keys=True, ensure_ascii=False)
                result.proposal_id = "p-" + sha256((req.case_id + content).encode()).hexdigest()[:24]
                return result.model_dump()
        except IntelligenceFailure:
            raise
        except (TimeoutError,):
            raise IntelligenceFailure("AI_TIMEOUT", "provider", request_id, True) from None
        except (ValidationError, ValueError, KeyError, TypeError):
            raise IntelligenceFailure("AI_INVALID_OUTPUT", "validation", request_id) from None
        except Exception as exc:
            from backend.app.ai.providers.base import AIResponseParsingError, AITimeoutError as ProviderTimeout
            if isinstance(exc, ProviderTimeout):
                raise IntelligenceFailure("AI_TIMEOUT", "provider", request_id, True) from None
            if isinstance(exc, AIResponseParsingError):
                raise IntelligenceFailure("AI_INVALID_OUTPUT", "parser", request_id) from None
            raise IntelligenceFailure("AI_UNAVAILABLE", "provider", request_id, True) from None
