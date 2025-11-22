"""Debug logging helper for development sessions."""

from __future__ import annotations

import logging
from pathlib import Path

_logger: logging.Logger | None = None


def get_logger() -> logging.Logger:
    """Return a configured debug logger that writes to /tmp/kicad-kicandy.log."""
    global _logger
    if _logger is not None:
        return _logger

    _logger = logging.getLogger("kicandy")
    _logger.setLevel(logging.DEBUG)

    log_file = Path("/tmp/kicad-kicandy.log")
    handler = logging.FileHandler(log_file, mode="a")
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)

    _logger.addHandler(handler)
    _logger.info("Debug logging initialized")

    return _logger
