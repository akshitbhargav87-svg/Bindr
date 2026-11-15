"""Multi-result bridge preserving the legacy document API and its single-result callers."""
from .engine import PromiseExtractionEngine
from .providers.base import AIProvider, AIResponseParsingError
from .providers.base import AITimeoutError
from time import monotonic


def extract_all_from_evidence(*, provider, **kwargs):
    # Resolve the published document boundary at call time so existing injected
    # processors/inference implementations remain compatible.
    from backend.app.ai import extract_commitment_from_evidence
    results = []
    started, budget = monotonic(), kwargs.get("timeout") or 45

    class CaptureProvider(AIProvider):
        def extract_commitment(self, text, metadata=None):
            remaining = budget - (monotonic() - started)
            if remaining <= 0:
                raise AITimeoutError("Document processing exhausted the extraction budget.")
            if hasattr(provider, "timeout"):
                provider.timeout = max(1, int(remaining))
            many = getattr(provider, "extract_commitments", None)
            batch = many(text, metadata) if many else [provider.extract_commitment(text, metadata)]
            if monotonic() - started > budget:
                raise AITimeoutError("Extraction exceeded its processing budget.")
            if not isinstance(batch, list) or not 1 <= len(batch) <= 50:
                raise AIResponseParsingError("Expected 1–50 extraction results, including explicit no-commitment.")
            validator = PromiseExtractionEngine(provider=provider)
            for result in batch:
                results.append(validator._post_process_result(result, text, metadata))
            return results[0]

    first = extract_commitment_from_evidence(provider=CaptureProvider(), **kwargs)
    for result in results:
        result.evidence_metadata = first.evidence_metadata
    return results or [first]
