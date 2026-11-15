"""Bound pure-engine calls without retrying a paid request or holding unlimited threads."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import BoundedSemaphore
from backend.app.services.case_state import fail

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
    except Exception:
        fail(
            503,
            "AI_UNAVAILABLE",
            "Intelligence did not complete. Nothing was confirmed.",
        )
