"""KAQG ingest client — invokes the Rust PDF/Neo4j ingest binary.

The Rust binary takes a ``KnowledgeGraph`` JSON payload on stdin and
returns a small status message on stdout.  This client hides the
subprocess mechanics behind a typed interface.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Iterable

from kaqg.config import Settings, get_settings
from kaqg.domain.models import KnowledgeGraph
from kaqg.errors import BinaryError, IngestionError

LOGGER = logging.getLogger("kaqg.ingest")


class IngestClient:
    """Run the Rust `kaqg_ingest` binary."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def binary(self) -> Path:
        return self._settings.ingest_binary

    # ------------------------------------------------------------------ PDF

    def extract_pdf(self, pdf_path: str | os.PathLike[str]) -> str:
        """Run the binary in PDF-extract mode and return the raw text."""
        binary = self.binary
        path = Path(pdf_path)
        if not binary.exists():
            raise BinaryError(
                f"Ingest binary not found at {binary}. Run `cargo build --release`."
            )
        if not path.exists():
            raise IngestionError(f"PDF not found: {path}")
        try:
            proc = subprocess.run(
                [str(binary), "--extract-pdf", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise BinaryError(f"Could not execute {binary}: {exc}") from exc
        if proc.returncode != 0:
            raise IngestionError(
                f"PDF extraction failed (rc={proc.returncode}): {proc.stderr}"
            )
        return proc.stdout

    # -------------------------------------------------------------- Neo4j

    def ingest(self, graph: KnowledgeGraph) -> str:
        """Pipe ``graph`` to the Rust binary for atomic Neo4j ingestion."""
        binary = self.binary
        if not binary.exists():
            raise BinaryError(
                f"Ingest binary not found at {binary}. Run `cargo build --release`."
            )
        env = os.environ.copy()
        env.setdefault("NEO4J_URI", self._settings.neo4j_uri)
        env.setdefault("NEO4J_USER", self._settings.neo4j_user)
        env.setdefault("NEO4J_PASSWORD", self._settings.neo4j_password)
        env.setdefault("NEO4J_DATABASE", self._settings.neo4j_database)
        try:
            proc = subprocess.run(
                [str(binary)],
                input=json.dumps(graph.to_payload()),
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
        except FileNotFoundError as exc:
            raise BinaryError(f"Could not execute {binary}: {exc}") from exc
        if proc.returncode != 0:
            raise IngestionError(
                f"Graph ingestion failed (rc={proc.returncode}): {proc.stderr}"
            )
        return proc.stdout
