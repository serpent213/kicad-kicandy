"""Debug logging helper for development sessions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import hunter

_logger: logging.Logger | None = None
_hunter_trace: hunter.Tracer | None = None


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


def start_trace() -> None:
    """Start Hunter trace to /tmp/kicad-kicandy.trace, filtering to project code only."""
    global _hunter_trace
    if _hunter_trace is not None:
        return

    import hunter

    trace_file = Path("/tmp/kicad-kicandy.trace")
    stream = trace_file.open("a", buffering=1, encoding="utf-8")

    # Trace all function calls in non-stdlib code
    _hunter_trace = hunter.trace(
        ~hunter.Q(stdlib=True),
        action=hunter.CallPrinter(stream=stream, force_colors=True),
        threading_support=True,
    )

    logger = get_logger()
    logger.info("Hunter trace started → /tmp/kicad-kicandy.trace")


def stop_trace() -> None:
    """Stop Hunter trace if running."""
    global _hunter_trace
    if _hunter_trace is None:
        return

    import hunter

    hunter.stop()
    _hunter_trace = None

    logger = get_logger()
    logger.info("Hunter trace stopped")
