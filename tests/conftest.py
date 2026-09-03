"""Shared pytest fixtures for the KAQG test suite."""
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def fixture_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def offline_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure deterministic env vars and disable network I/O.

    Tests that want to exercise the real Neo4j / OpenRouter paths should
    opt in by setting ``KAQG_LIVE=1`` and the matching credentials.
    """
    monkeypatch.setenv("NEO4J_URI", "bolt://test")
    monkeypatch.setenv("NEO4J_USER", "test")
    monkeypatch.setenv("NEO4J_PASSWORD", "test")
    monkeypatch.setenv("NEO4J_DATABASE", "test")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("KAQG_LOG_LEVEL", "WARNING")
