"""Command-line interface for the KAQG pipeline.

The CLI is built on argparse subcommands so each stage is independently
runnable and individually testable.  Every subcommand configures logging
and prints a human-readable status line.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Callable, Sequence

from kaqg import __version__
from kaqg.config import get_settings
from kaqg.domain.models import QuestionBank
from kaqg.errors import KAQGError
from kaqg.export import write_auto
from kaqg.logging import configure_logging
from kaqg.pipelines.generation import GenerationPipeline, GenerationRequest
from kaqg.pipelines.ingestion import IngestionPipeline
from kaqg.pipelines.retrieval import RetrievalPipeline, RetrievalRequest
from kaqg.pipelines.scoring import ScoringPipeline

LOGGER = logging.getLogger("kaqg.cli")

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_RUNTIME = 1


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_ingest(args: argparse.Namespace) -> int:
    settings = get_settings()
    with IngestionPipeline(settings) as pipe:
        result = pipe.run(args.pdf)
    print(
        f"[ingest] {result.pdf_path.name}: {result.char_count} chars -> "
        f"{result.triple_count} triples"
    )
    return EXIT_OK


def cmd_score(args: argparse.Namespace) -> int:
    settings = get_settings()
    with ScoringPipeline(settings) as pipe:
        result = pipe.run()
    print(f"[score] Updated {result.updated} concept nodes")
    return EXIT_OK


def cmd_generate(args: argparse.Namespace) -> int:
    settings = get_settings()
    with RetrievalPipeline(settings) as retrieval:
        subgraphs = retrieval.run(RetrievalRequest(
            difficulty=args.difficulty,
            count=args.count,
        ))
    if not subgraphs:
        print(f"[generate] No subgraphs matched difficulty={args.difficulty!r}")
        return EXIT_OK
    with GenerationPipeline(settings) as generation:
        questions = generation.generate_many(subgraphs, GenerationRequest(
            difficulty=args.difficulty,
            count=args.count,
            use_mock=args.mock,
        ))
    bank = QuestionBank(
        difficulty=args.difficulty,
        questions=tuple(questions),
        mode="mock" if args.mock else "live",
    )
    out_path = write_auto(bank, args.output)
    print(f"[generate] Wrote {len(questions)} questions ({bank.mode}) to {out_path}")
    return EXIT_OK


def cmd_verify(args: argparse.Namespace) -> int:
    """Round-trip a Neo4j connection and print per-label node counts."""
    from kaqg.clients.neo4j import Neo4jClient
    from kaqg.domain.cypher import NODE_COUNTS_QUERY, PING_QUERY, SERVER_INFO_QUERY

    settings = get_settings()
    client = Neo4jClient(settings)
    try:
        client.connect()
        with client.session() as session:
            ping = session.execute_read(PING_QUERY)
            assert ping and ping[0]["ok"] == 1, f"unexpected ping response: {ping}"
            info = session.execute_read(SERVER_INFO_QUERY)
            if info:
                row = info[0]
                print(f"[verify] Server: {row['name']} {row['versions']} ({row['edition']})")
            counts = session.execute_read(NODE_COUNTS_QUERY)
            for row in counts:
                print(f"[verify] Nodes[{row['label']}]: {row['n']}")
    finally:
        client.close()
    return EXIT_OK


def cmd_e2e(args: argparse.Namespace) -> int:
    """End-to-end pipeline: ingestion -> score -> retrieval -> generation."""
    settings = get_settings()
    started = time.perf_counter()
    with IngestionPipeline(settings) as ingestion:
        ingestion_result = ingestion.run(args.pdf)
    with ScoringPipeline(settings) as scoring:
        scoring_result = scoring.run()
    with RetrievalPipeline(settings) as retrieval:
        subgraphs = retrieval.run(RetrievalRequest(
            difficulty=args.difficulty,
            count=args.count,
        ))
    with GenerationPipeline(settings) as generation:
        questions = generation.generate_many(subgraphs, GenerationRequest(
            difficulty=args.difficulty,
            count=args.count,
            use_mock=args.mock,
        ))
    bank = QuestionBank(
        difficulty=args.difficulty,
        questions=tuple(questions),
        mode="mock" if args.mock else "live",
        source_pdf=str(args.pdf),
    )
    out_path = write_auto(bank, args.output)
    print(
        f"[e2e] {ingestion_result.triple_count} triples -> "
        f"{scoring_result.updated} scored -> {len(questions)} questions "
        f"in {time.perf_counter() - started:.2f}s"
    )
    print(f"[e2e] Wrote question bank to {out_path}")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kaqg",
        description="Knowledge Augmented Question Generation (KAQG) pipeline.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--log-level", default=None,
        help="Override KAQG_LOG_LEVEL (e.g. DEBUG, INFO, WARNING).",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    p_ingest = sub.add_parser("ingest", help="PDF -> Knowledge Graph -> Neo4j")
    p_ingest.add_argument("pdf", type=Path, help="Path to the syllabus PDF")
    p_ingest.set_defaults(func=cmd_ingest)

    p_score = sub.add_parser("score", help="Compute centrality + IRT difficulty")
    p_score.set_defaults(func=cmd_score)

    p_gen = sub.add_parser("generate", help="Generate an MCQ question bank")
    p_gen.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="medium")
    p_gen.add_argument("--count", type=int, default=5)
    p_gen.add_argument("--output", type=Path, default=Path("questions.json"))
    p_gen.add_argument("--mock", action="store_true", help="Use the deterministic mock")
    p_gen.set_defaults(func=cmd_generate)

    p_verify = sub.add_parser("verify", help="Verify the Neo4j connection")
    p_verify.set_defaults(func=cmd_verify)

    p_e2e = sub.add_parser("e2e", help="Full pipeline: ingest -> score -> generate")
    p_e2e.add_argument("pdf", type=Path, help="Path to the syllabus PDF")
    p_e2e.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="medium")
    p_e2e.add_argument("--count", type=int, default=3)
    p_e2e.add_argument("--output", type=Path, default=Path("e2e_questions.json"))
    p_e2e.add_argument("--mock", action="store_true")
    p_e2e.set_defaults(func=cmd_e2e)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = get_settings()
    configure_logging(args.log_level or settings.log_level)
    try:
        return args.func(args)
    except KAQGError as exc:
        LOGGER.error("%s: %s", type(exc).__name__, exc)
        return EXIT_RUNTIME
    except KeyboardInterrupt:
        LOGGER.warning("Interrupted by user")
        return EXIT_RUNTIME


if __name__ == "__main__":
    sys.exit(main())
