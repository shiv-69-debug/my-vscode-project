"""Centralised logging setup."""

import logging
import sys

from config import config


def setup_logging() -> logging.Logger:
    """Configure application-wide logging."""
    logger = logging.getLogger("interview_app")
    logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # Optional file handler
    if config.log_file:
        file_handler = logging.FileHandler(config.log_file)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger
