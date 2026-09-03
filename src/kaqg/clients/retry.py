"""Shared retry decorator for transient I/O failures.

Used by both the Neo4j and OpenRouter clients to wrap idempotent calls
with bounded exponential backoff.
"""
from __future__ import annotations

import functools
import logging
import random
import time
from typing import Any, Callable, Iterable, TypeVar

from kaqg.errors import ConnectionError, KAQGError

LOGGER = logging.getLogger("kaqg.retry")
T = TypeVar("T")

DEFAULT_RETRYABLE: tuple[type[BaseException], ...] = (ConnectionError, TimeoutError, OSError)


def retry(
    exceptions: Iterable[type[BaseException]] = DEFAULT_RETRYABLE,
    *,
    attempts: int = 3,
    backoff: float = 0.5,
    jitter: float = 0.1,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Return a decorator that retries ``fn`` on the given exceptions.

    Backoff is exponential: ``backoff * 2 ** (try - 1)`` plus uniform
    jitter in ``[-jitter, +jitter]`` seconds.
    """
    exc_tuple = tuple(exceptions)
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def inner(*args: Any, **kwargs: Any) -> T:
            last_exc: BaseException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exc_tuple as exc:  # noqa: PERF203 - retry loop
                    last_exc = exc
                    if attempt == attempts:
                        break
                    sleep_for = backoff * (2 ** (attempt - 1))
                    sleep_for += random.uniform(-jitter, jitter)
                    sleep_for = max(0.0, sleep_for)
                    LOGGER.warning(
                        "Retry %d/%d for %s after %.2fs (error: %s)",
                        attempt, attempts, fn.__qualname__, sleep_for, exc,
                    )
                    time.sleep(sleep_for)
            assert last_exc is not None
            raise KAQGError(
                f"{fn.__qualname__} failed after {attempts} attempts"
            ) from last_exc

        return inner

    return decorator