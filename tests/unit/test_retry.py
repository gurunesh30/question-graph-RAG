"""Unit tests for the retry decorator."""
from __future__ import annotations

import pytest

from kaqg.clients.retry import retry
from kaqg.errors import ConnectionError, KAQGError


def test_retries_then_raises_kaqg_error():
    calls = {"n": 0}

    @retry(exceptions=(ConnectionError,), attempts=3, backoff=0.0, jitter=0.0)
    def flaky() -> None:
        calls["n"] += 1
        raise ConnectionError("nope")

    with pytest.raises(KAQGError):
        flaky()
    assert calls["n"] == 3


def test_succeeds_after_transient_failures():
    calls = {"n": 0}

    @retry(exceptions=(ConnectionError,), attempts=3, backoff=0.0, jitter=0.0)
    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 2:
            raise ConnectionError("transient")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 2


def test_does_not_retry_other_exceptions():
    calls = {"n": 0}

    @retry(exceptions=(ConnectionError,), attempts=3, backoff=0.0, jitter=0.0)
    def boom() -> None:
        calls["n"] += 1
        raise ValueError("nope")

    with pytest.raises(ValueError):
        boom()
    assert calls["n"] == 1
