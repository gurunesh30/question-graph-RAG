"""Pure IRT (Item Response Theory) difficulty math.

The KAQG spec defines a min-max normalisation that maps raw concept
degree counts into the IRT difficulty range :math:`b \\in [0.1, 1.0]`::

    b = 0.1 + (deg - min) / (max - min) * 0.9

These helpers are intentionally pure (no I/O, no globals) so they can be
unit-tested in isolation and reused by the offline e2e harness.
"""
from __future__ import annotations

from dataclasses import dataclass

from kaqg.errors import ValidationError

DEFAULT_MIN_DIFFICULTY: float = 0.1
DEFAULT_MAX_DIFFICULTY: float = 1.0
DEFAULT_DEGENERATE_VALUE: float = 0.55  # (min+max)/2


def clamp_difficulty(value: float,
                     min_d: float = DEFAULT_MIN_DIFFICULTY,
                     max_d: float = DEFAULT_MAX_DIFFICULTY) -> float:
    """Clamp ``value`` into the closed interval ``[min_d, max_d]``."""
    if min_d > max_d:
        raise ValidationError(f"min_difficulty ({min_d}) must be <= max_difficulty ({max_d})")
    return min(max_d, max(min_d, value))


def irt_difficulty(degree: int,
                   min_deg: int,
                   max_deg: int,
                   min_d: float = DEFAULT_MIN_DIFFICULTY,
                   max_d: float = DEFAULT_MAX_DIFFICULTY) -> float:
    """Spec 4.3 IRT formula with graceful handling of degenerate inputs.

    * If ``max_deg == min_deg`` (single-degree graph) we return the midpoint
      of the difficulty interval.
    * The result is always clamped into ``[min_d, max_d]``.
    """
    if max_deg == min_deg:
        return (min_d + max_d) / 2.0
    raw = min_d + (degree - min_deg) * (max_d - min_d) / (max_deg - min_deg)
    return clamp_difficulty(raw, min_d, max_d)


def fuse_centrality(degree: int, pagerank: float, weight: float = 10.0) -> float:
    """Combine degree and PageRank into a single ranking signal.

    PageRank values are typically << 1 while degree counts are >= 1, so a
    multiplier is applied to keep both signals visible in the score.
    """
    return float(degree) + weight * float(pagerank)


@dataclass(frozen=True, slots=True)
class IRTDifficulty:
    """Bundle of IRT-related constants for dependency injection.

    Pipelines receive an :class:`IRTDifficulty` instance instead of
    reading module-level globals, which keeps them testable.
    """

    min_difficulty: float = DEFAULT_MIN_DIFFICULTY
    max_difficulty: float = DEFAULT_MAX_DIFFICULTY

    def __post_init__(self) -> None:
        if not 0.0 <= self.min_difficulty < self.max_difficulty <= 1.0:
            raise ValidationError(
                f"IRTDifficulty bounds invalid: {self.min_difficulty}..{self.max_difficulty}"
            )

    def compute(self, degree: int, min_deg: int, max_deg: int) -> float:
        return irt_difficulty(degree, min_deg, max_deg, self.min_difficulty, self.max_difficulty)
