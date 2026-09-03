"""Neo4j connection helper for the KAQG pipeline.

Centralises driver construction so every module reads identical connection
settings from the environment.  Uses the official Python `neo4j` driver in
read/write transactions, with `bolt+s` from AuraDB.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from dotenv import load_dotenv
from neo4j import Driver, GraphDatabase, Session

load_dotenv()

DEFAULT_DB = os.getenv("NEO4J_DATABASE", "neo4j")


def build_driver() -> Driver:
    uri = os.environ["NEO4J_URI"]
    user = os.environ["NEO4J_USER"]
    password = os.environ["NEO4J_PASSWORD"]
    return GraphDatabase.driver(uri, auth=(user, password))


@contextmanager
def open_session(driver: Driver | None = None) -> Iterator[Session]:
    """Open a Neo4j session and guarantee it is released."""
    owns_driver = False
    if driver is None:
        driver = build_driver()
        owns_driver = True
    session = driver.session(database=DEFAULT_DB)
    try:
        yield session
    finally:
        session.close()
        if owns_driver:
            driver.close()


def run_query(session: Session, cypher: str, **params):
    """Run a read/write Cypher query and return the result list."""
    result = session.run(cypher, **params)
    return [record.data() for record in result]