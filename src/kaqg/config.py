"""Typed runtime configuration for the KAQG pipeline.

Settings are loaded once from the process environment (with .env fallback)
and exposed via a frozen dataclass.  ``get_settings()`` caches a singleton
so callers can read configuration without paying re-parsing cost.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from kaqg.errors import ConfigError

# Load .env exactly once at import time.  Idempotent.
load_dotenv()


def _coerce(name: str, value: str | None, default: Any, caster: type) -> Any:
    if value is None or value == "":
        return default
    try:
        return caster(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(
            f"Invalid value for env var {name!r}: {value!r} cannot be parsed as {caster.__name__}"
        ) from exc


@dataclass(frozen=True)
class Settings:
    """Immutable process-wide configuration.

    All values default from environment variables so the same object works
    for production, tests, and CLI overrides.
    """

    # ---- Neo4j ----
    neo4j_uri: str = field(default_factory=lambda: os.environ.get("NEO4J_URI", ""))
    neo4j_user: str = field(default_factory=lambda: os.environ.get("NEO4J_USER", ""))
    neo4j_password: str = field(default_factory=lambda: os.environ.get("NEO4J_PASSWORD", ""))
    neo4j_database: str = field(
        default_factory=lambda: os.environ.get("NEO4J_DATABASE", "neo4j")
    )

    # ---- OpenRouter ----
    openrouter_api_key: str = field(
        default_factory=lambda: os.environ.get("OPENROUTER_API_KEY", "")
    )
    openrouter_model: str = field(
        default_factory=lambda: os.environ.get("KAQG_MODEL", "openai/gpt-4o-mini")
    )
    request_timeout: float = field(
        default_factory=lambda: _coerce(
            "KAQG_REQUEST_TIMEOUT", os.environ.get("KAQG_REQUEST_TIMEOUT"), 60.0, float
        )
    )

    # ---- Rust binaries ----
    ingest_binary: Path = field(
        default_factory=lambda: Path(
            os.environ.get(
                "KAQG_INGEST_BINARY",
                "./rust_kg_engine/target/release/kaqg_ingest",
            )
        )
    )
    pagerank_binary: Path = field(
        default_factory=lambda: Path(
            os.environ.get(
                "KAQG_PAGERANK_BINARY",
                "./rust_kg_engine/target/release/kaqg_pagerank",
            )
        )
    )

    # ---- Pipeline tuning ----
    log_level: str = field(default_factory=lambda: os.environ.get("KAQG_LOG_LEVEL", "INFO"))
    retry_attempts: int = field(
        default_factory=lambda: _coerce(
            "KAQG_RETRY_ATTEMPTS", os.environ.get("KAQG_RETRY_ATTEMPTS"), 3, int
        )
    )
    retry_backoff: float = field(
        default_factory=lambda: _coerce(
            "KAQG_RETRY_BACKOFF", os.environ.get("KAQG_RETRY_BACKOFF"), 0.5, float
        )
    )

    # ---- IRT bounds (spec 4.3) ----
    min_difficulty: float = 0.1
    max_difficulty: float = 1.0

    # ---- Difficulty bands (spec 5.2) ----
    difficulty_bands: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "easy": (0.0, 0.4),
            "medium": (0.4, 0.7),
            "hard": (0.7, 1.01),
        }
    )

    def validate(self) -> None:
        """Raise ConfigError if required values are missing."""
        missing = [
            f.name
            for f in fields(self)
            if f.name in {"neo4j_uri", "neo4j_user", "neo4j_password", "openrouter_api_key"}
            and not getattr(self, f.name)
        ]
        if missing:
            raise ConfigError(
                f"Missing required configuration: {', '.join(missing)}. "
                "Set them in your environment or .env file."
            )
        if not 0.0 <= self.min_difficulty < self.max_difficulty <= 1.0:
            raise ConfigError("min_difficulty/max_difficulty must lie in [0,1] with min<max.")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached process-wide Settings singleton."""
    settings = Settings()
    settings.validate()
    return settings


def reset_settings_cache() -> None:
    """Test helper: clear the cached singleton so env changes take effect."""
    get_settings.cache_clear()
