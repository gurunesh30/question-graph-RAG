"""KAQG: Knowledge Augmented Question Generation pipeline.

A hybrid Python / Rust system that ingests educational syllabi, builds a
three-tiered knowledge graph in Neo4j, computes IRT difficulty coefficients
for every concept, and emits difficulty-calibrated MCQs.
"""

from kaqg.config import Settings, get_settings
from kaqg.errors import KAQGError

__all__ = ["KAQGError", "Settings", "get_settings"]
__version__ = "0.2.0"