"""Logging utilities for AutoScribe."""

import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

# Create default console
default_console = Console(stderr=True)


def setup_logger(
    name: str = "autoscribe",
    level: int = logging.INFO,
    console: Console | None = None,
) -> logging.Logger:
    """Set up a logger with rich formatting."""
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers = []

    # Create console if not provided
    if console is None:
        console = default_console

    # Create rich handler
    handler = RichHandler(
        console=console,
        show_path=False,
        omit_repeated_times=False,
        rich_tracebacks=True,
    )
    handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


def get_logger(name: str = "autoscribe") -> logging.Logger:
    """Get an existing logger or create a new one."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger


def log_exception(
    logger: logging.Logger,
    exc: Exception,
    message: str | None = None,
    exit_code: int | None = None,
) -> None:
    """Log an exception and optionally exit."""
    if message:
        logger.error(f"{message}: {str(exc)}")
    else:
        logger.error(str(exc))

    if exit_code is not None:
        sys.exit(exit_code)


# Get default logger
logger = get_logger()


def info(message: str) -> None:
    """Log an info message."""
    logger.info(message)


def warning(message: str) -> None:
    """Log a warning message."""
    logger.warning(message)


def error(message: str) -> None:
    """Log an error message."""
    logger.error(message)


def success(message: str) -> None:
    """Log a success message."""
    logger.info(f"✓ {message}")


def debug(message: str) -> None:
    """Log a debug message."""
    logger.debug(message)
