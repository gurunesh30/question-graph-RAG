"""Neo4j client for the KAQG pipeline.

Wraps the official ``neo4j`` Python driver behind a small, type-safe
interface.  Handles connection management, retries on transient errors,
and conversion of driver errors into KAQG exceptions.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterable, Iterator

from neo4j import Driver, GraphDatabase, Session
from neo4j.exceptions import AuthError, ServiceUnavailable

from kaqg.clients.retry import retry
from kaqg.config import Settings, get_settings
from kaqg.errors import AuthenticationError, ConnectionError, GraphError

LOGGER = logging.getLogger("kaqg.neo4j")


class Neo4jClient:
    """Stateless wrapper around a Neo4j driver.

    Instances are cheap to construct but the underlying driver is
    expensive — keep one client per process and reuse it.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._driver: Driver | None = None

    # ------------------------------------------------------------------ IO

    def connect(self) -> None:
        """Open the driver if it isn't already."""
        if self._driver is not None:
            return
        self._settings.validate()
        try:
            self._driver = GraphDatabase.driver(
                self._settings.neo4j_uri,
                auth=(self._settings.neo4j_user, self._settings.neo4j_password),
            )
        except Exception as exc:  # noqa: BLE001
            raise ConnectionError(
                f"Could not construct Neo4j driver for {self._settings.neo4j_uri}: {exc}"
            ) from exc
        self.verify()

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    @retry()
    def verify(self) -> None:
        """Round-trip a connection check (auto-retried on transient errors)."""
        if self._driver is None:
            raise ConnectionError("Driver not connected — call connect() first")
        try:
            self._driver.verify_connectivity()
        except AuthError as exc:
            raise AuthenticationError(f"Neo4j authentication failed: {exc}") from exc
        except ServiceUnavailable as exc:
            raise ConnectionError(f"Neo4j unavailable: {exc}") from exc

    # ----------------------------------------------------------------- CRUD

    def session(self) -> "Neo4jSession":
        """Return a session context manager bound to the configured database."""
        if self._driver is None:
            self.connect()
        assert self._driver is not None  # for type-checkers
        return Neo4jSession(self._driver.session(database=self._settings.neo4j_database))

    def execute_read(self, cypher: str, **params: Any) -> list[dict[str, Any]]:
        with self.session() as session:
            return session.execute_read(cypher, **params)

    def execute_write(self, cypher: str, **params: Any) -> list[dict[str, Any]]:
        with self.session() as session:
            return session.execute_write(cypher, **params)

    # ---------------------------------------------------------- introspection

    def __enter__(self) -> "Neo4jClient":
        self.connect()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()


class Neo4jSession:
    """Context manager that runs a single read or write transaction.

    Wraps a ``neo4j.Session`` so callers never need to call ``.close()``
    or remember to use ``session.begin_transaction()``.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    @retry()
    def execute_read(self, cypher: str, **params: Any) -> list[dict[str, Any]]:
        try:
            result = self._session.run(cypher, **params)
            return [record.data() for record in result]
        except ServiceUnavailable as exc:
            raise ConnectionError(f"Neo4j read failed: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise GraphError(f"Read query failed: {exc}") from exc

    @retry()
    def execute_write(self, cypher: str, **params: Any) -> list[dict[str, Any]]:
        try:
            result = self._session.run(cypher, **params)
            return [record.data() for record in result]
        except ServiceUnavailable as exc:
            raise ConnectionError(f"Neo4j write failed: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise GraphError(f"Write query failed: {exc}") from exc

    def close(self) -> None:
        try:
            self._session.close()
        except Exception:  # noqa: BLE001
            LOGGER.debug("Ignoring error while closing session", exc_info=True)

    def __enter__(self) -> "Neo4jSession":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()


# ----------------------------------------------------------------- legacy shim
# Older modules call ``open_session()`` as a free function.  Re-export it
# so refactored pipelines can still use the helper if they prefer.
@contextmanager
def open_session() -> Iterator[Neo4jSession]:
    client = Neo4jClient()
    client.connect()
    try:
        with client.session() as session:
            yield session
    finally:
        client.close()
