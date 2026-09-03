"""
Structured logger for CRISP-DM Pipeline and Mining Engine.
"""

import logging
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with clean terminal tags and ANSI colors."""

    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        level_name = record.levelname
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        message = record.getMessage()

        # Check if terminal supports color
        if hasattr(sys.stderr, "isatty") and sys.stderr.isatty():
            return f"{color}[{level_name}]{self.RESET} {timestamp} - {message}"
        return f"[{level_name}] {timestamp} - {message}"


def get_logger(name: str = "crisp_dm", level: int = logging.INFO, log_file: Optional[str] = None) -> logging.Logger:
    """
    Get or create a configured logger instance.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)

    # Optional File Handler
    if log_file:
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def setup_logger(verbose: bool = False, quiet: bool = False, log_file: Optional[str] = None) -> logging.Logger:
    """Setup root application logger based on CLI verbosity flags."""
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    return get_logger(name="crisp_dm", level=level, log_file=log_file)
