"""
Shared thread-pool executor registry for request-side blocking work.

Routes use this registry instead of owning module-level ThreadPoolExecutor
instances. Lifecycle is managed from FastAPI lifespan in app.main.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Lock

_shared_executor: ThreadPoolExecutor | None = None
_lock = Lock()


def set_shared_executor(executor: ThreadPoolExecutor) -> None:
    global _shared_executor
    _shared_executor = executor


def get_shared_executor() -> ThreadPoolExecutor:
    global _shared_executor
    if _shared_executor is None:
        with _lock:
            if _shared_executor is None:
                _shared_executor = ThreadPoolExecutor(
                    max_workers=4,
                    thread_name_prefix="backend-fallback",
                )
    return _shared_executor


def clear_shared_executor() -> None:
    global _shared_executor
    _shared_executor = None


__all__ = [
    "clear_shared_executor",
    "get_shared_executor",
    "set_shared_executor",
]
