"""Live Neo4j integration tests (skipped if KAQG_LIVE != '1')."""
from __future__ import annotations

import os

import pytest

from kaqg.clients.neo4j import Neo4jClient
from kaqg.domain.cypher import NODE_COUNTS_QUERY, PING_QUERY, SERVER_INFO_QUERY


LIVE = os.environ.get("KAQG_LIVE") == "1"


@pytest.mark.integration
@pytest.mark.skipif(not LIVE, reason="set KAQG_LIVE=1 to enable live integration tests")
def test_neo4j_round_trip() -> None:
    client = Neo4jClient()
    client.connect()
    try:
        with client.session() as session:
            ping = session.execute_read(PING_QUERY)
            assert ping and ping[0]["ok"] == 1
            info = session.execute_read(SERVER_INFO_QUERY)
            assert info and info[0]["name"]
            counts = session.execute_read(NODE_COUNTS_QUERY)
            assert isinstance(counts, list)
    finally:
        client.close()
