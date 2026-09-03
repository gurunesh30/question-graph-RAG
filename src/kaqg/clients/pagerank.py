"""PageRank client — Python wrapper around the Rust PageRank binary."""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Iterable

from kaqg.config import Settings, get_settings
from kaqg.errors import BinaryError

LOGGER = logging.getLogger("kaqg.pagerank")


class PageRankClient:
    """Compute PageRank scores by invoking the local Rust micro-service."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def binary(self) -> Path:
        return self._settings.pagerank_binary

    def rank(self, edges: Iterable[dict]) -> dict[int, float]:
        """Return ``{node_id: score}`` for every node referenced in ``edges``.

        The Rust binary expects a JSON object of the form
        ``{"edges": [{"src": int, "dst": int}, ...]}`` on stdin and
        returns ``{"ranks": [{"id": int, "score": float}, ...]}`` on stdout.
        """
        binary = self.binary
        if not binary.exists():
            raise BinaryError(
                f"PageRank binary not found at {binary}. "
                "Run `cargo build --release` inside rust_kg_engine/."
            )
        payload = {"edges": list(edges)}
        try:
            proc = subprocess.run(
                [str(binary)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise BinaryError(f"Could not execute {binary}: {exc}") from exc

        if proc.returncode != 0:
            raise BinaryError(
                f"PageRank binary failed (rc={proc.returncode}): {proc.stderr}"
            )
        if not proc.stdout.strip():
            return {}
        try:
            parsed = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise BinaryError(
                f"PageRank binary returned non-JSON output: {proc.stdout[:200]}"
            ) from exc
        return {int(r["id"]): float(r["score"]) for r in parsed.get("ranks", [])}
