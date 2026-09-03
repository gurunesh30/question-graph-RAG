"""Verify the Neo4j AuraDB connection via the official Python driver.

Per spec 4.1 we need to ensure the `neo4j` package is in requirements.txt
and the driver can authenticate using the .env credentials.  This script:

  1. Builds a Driver instance.
  2. Executes a lightweight `RETURN 1 AS ok` round-trip.
  3. Reports the driver/server version and node counts per label.

Exit code 0 on success, non-zero on failure.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kg.neo4j_client import build_driver, DEFAULT_DB
from kg.neo4j_client import run_query, open_session


def _print_header(title: str) -> None:
    print(f"\n=== {title} ===")


def verify_connection() -> bool:
    try:
        driver = build_driver()
    except KeyError as exc:
        print(f"[verify] Missing environment variable: {exc}", file=sys.stderr)
        return False
    try:
        driver.verify_connectivity()
        print(f"[verify] Driver connected to {driver} (db='{DEFAULT_DB}')")
        with open_session(driver) as session:
            server = run_query(session, "CALL dbms.components() YIELD name, versions, edition "
                                        "RETURN name, versions, edition")
            if server:
                first = server[0]
                print(f"[verify] Server: {first.get('name')} "
                      f"{first.get('versions')} ({first.get('edition')})")

            counts = run_query(session,
                "MATCH (n) "
                "RETURN labels(n)[0] AS label, count(n) AS n "
                "ORDER BY n DESC")
            for row in counts:
                print(f"[verify] Nodes[{row['label']}]: {row['n']}")
        return True
    except Exception as exc:  # noqa: BLE001 — surface any driver error verbatim
        print(f"[verify] Connection failed: {exc}", file=sys.stderr)
        return False
    finally:
        driver.close()


def main(argv: Iterable[str]) -> int:
    _print_header("Neo4j Driver Verification")
    ok = verify_connection()
    print(f"\n[verify] {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))