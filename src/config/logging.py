"""Centralized logging configuration using Loguru.

This module configures structured logging with environment-aware settings:
- Development: DEBUG level with colored output
- Production: INFO level with structured JSON-like output
"""

import sys
from typing import Literal

from loguru import logger

import src.config.env as env


# Define log levels
LogLevel = Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def get_log_level() -> str:
    """Get appropriate log level based on environment."""
    if env.DEVELOPMENT:
        return "DEBUG"
    return env.LOG_LEVEL.upper() if env.LOG_LEVEL else "INFO"


def setup_logging() -> None:
    """Configure Loguru logger with environment-specific settings.

    This removes the default handler and adds custom handlers based on
    the current environment (development/staging/production).
    """
    # Remove default handler
    logger.remove()

    log_level = get_log_level()

    if env.DEVELOPMENT:
        # Development: Colored console output with DEBUG level
        logger.add(
            sys.stderr,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
    else:
        # Production: Structured output without colors
        logger.add(
            sys.stderr,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            colorize=False,
            backtrace=False,
            diagnose=False,
            serialize=False,  # Set to True for JSON output
        )

    # Log startup configuration
    logger.info(f"Logging configured - Level: {log_level} | Environment: {env.ENVIRONMENT}")


def get_logger(name: str):
    """Get a logger instance bound to a specific module.

    Args:
        name: Usually __name__ from the calling module

    Returns:
        A bound logger instance

    Example:
        from src.config.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Hello from module")
    """
    return logger.bind(name=name)


# Auto-configure on import
setup_logging()
