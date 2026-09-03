"""Structured logging for the KAQG pipeline.

A single :func:`get_logger` helper gives every module a child logger of
``kaqg`` so log levels can be controlled centrally via ``KAQG_LOG_LEVEL``
or :func:`kaqg.config.Settings.log_level`.
"""
from __future__ import annotations

import logging
import sys
from typing import Final

_LOGGER_NAME: Final[str] = "kaqg"
_FORMAT: Final[str] = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Configure the root ``kaqg`` logger once.

    Safe to call multiple times — subsequent calls only adjust the level
    and re-attach handlers if missing.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level.upper())
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler(stream=sys.stderr)
        handler.setFormatter(logging.Formatter(_FORMAT))
        logger.addHandler(handler)
    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Return a child logger of the package logger."""
    if not name.startswith(_LOGGER_NAME):
        name = f"{_LOGGER_NAME}.{name}"
    return logging.getLogger(name)