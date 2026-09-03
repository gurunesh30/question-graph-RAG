"""Exception hierarchy for the KAQG pipeline.

All KAQG-specific errors descend from :class:`KAQGError`, so callers can
catch one base class while still distinguishing individual failure modes
when they want to.
"""
from __future__ import annotations


class KAQGError(Exception):
    """Base class for every KAQG-specific failure."""


class ConfigError(KAQGError):
    """Configuration is missing or invalid."""


class ConnectionError(KAQGError):
    """Failed to reach a remote service (Neo4j, OpenRouter, etc.)."""


class AuthenticationError(KAQGError):
    """Credentials were rejected by a remote service."""


class IngestionError(KAQGError):
    """Failed to parse or ingest an input (PDF, LLM JSON, etc.)."""


class GraphError(KAQGError):
    """Neo4j returned an unexpected state or query failed."""


class GenerationError(KAQGError):
    """LLM generation failed (timeout, malformed output, etc.)."""


class BinaryError(KAQGError):
    """A Rust binary (ingest or pagerank) failed to run or returned garbage."""


class ValidationError(KAQGError):
    """A domain object failed validation."""