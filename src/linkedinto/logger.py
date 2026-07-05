"""Logging configuration for linkedinto."""

import logging
import sys
from typing import TextIO


def setup_logger(
    name: str = "linkedinto",
    level: int = logging.WARNING,
    stream: TextIO = sys.stderr,
) -> logging.Logger:
    """Configure and return a logger instance.

    Args:
        name: Logger name (default: "linkedinto").
        level: Logging level (default: WARNING).
        stream: Output stream (default: stderr).

    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(stream)
        # Leave handler.level at NOTSET so it inherits the logger's level
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
