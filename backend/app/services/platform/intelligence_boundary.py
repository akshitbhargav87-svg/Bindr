"""Bound pure-engine calls without retrying a paid request or holding unlimited threads."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import BoundedSemaphore
from backend.app.services.case_state import fail
from backend.app.services.ai_adapter import AIAdapterError
from backend.app.services.intelligence.extraction import IntelligenceFailure

# Only these public codes/messages may cross the pure-engine boundary. Never
# forward provider exception text, evidence, request IDs or arbitrary attributes.
_ENGINE_FAILURES = {
    "AI_TIMEOUT": (504, "Intelligence exceeded the request deadline. Nothing was confirmed."),
    "AI_INVALID_OUTPUT": (502, "The intelligence response could not be validated. Nothing was confirmed."),
    "AI_UNAVAILABLE": (503, "Intelligence did not complete. Nothing was confirmed."),
    "VALIDATION_ERROR": (422, "Review the source metadata and processing limits. Nothing was confirmed."),
}

_executor = ThreadPoolExecutor(
    max_workers=2, thread_name_prefix="bindr-intelligence-v2"
)
_slots = BoundedSemaphore(2)


def invoke(method, request, timeout=60):
    if not _slots.acquire(blocking=False):
        fail(503, "AI_BUSY", "Intelligence is busy. Keep your draft and try later.")
    try:
        future = _executor.submit(method, request)
    except BaseException:
        _slots.release()
        raise
    future.add_done_callback(lambda _: _slots.release())
    try:
        return future.result(timeout=timeout)
    except TimeoutError:
        future.cancel()
        # A running pure call cannot be killed safely. Its slot stays occupied until it
        # exits. No database/session/storage handles were passed to it; no late writes.
        fail(
            504,
            "AI_TIMEOUT",
            "Intelligence exceeded the request deadline. Nothing was confirmed.",
        )
    except (IntelligenceFailure, AIAdapterError) as exc:
        status, message = _ENGINE_FAILURES.get(exc.code, _ENGINE_FAILURES["AI_UNAVAILABLE"])
        fail(status, exc.code if exc.code in _ENGINE_FAILURES else "AI_UNAVAILABLE", message)
    except Exception:
        fail(
            503,
            "AI_UNAVAILABLE",
            "Intelligence did not complete. Nothing was confirmed.",
        )
