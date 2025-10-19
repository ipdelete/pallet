"""Centralized logging configuration for Pallet framework.

Provides structured logging for both orchestrator (pallet) and agents.
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional

# Environment variables
DEBUG_MODE = os.getenv("PALLET_DEBUG", "0") == "1"
LOG_LEVEL = os.getenv("PALLET_LOG_LEVEL", "DEBUG" if DEBUG_MODE else "INFO")
ORAS_VERBOSE = os.getenv("PALLET_ORAS_VERBOSE", "0") == "1"
TRACE_REQUESTS = os.getenv("PALLET_TRACE_REQUESTS", "0") == "1"

# Log directory configuration
PALLET_LOG_DIR = Path("logs/pallet")
AGENTS_LOG_DIR = Path("logs/agents")

# Create log directories
PALLET_LOG_DIR.mkdir(parents=True, exist_ok=True)
AGENTS_LOG_DIR.mkdir(parents=True, exist_ok=True)

# Logging format with correlation ID support
DETAILED_FORMAT = (
    "[%(asctime)s] [%(levelname)-8s] [%(name)s] [%(filename)s:%(lineno)d] %(message)s"
)
SIMPLE_FORMAT = "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s"

# Use detailed format in debug mode
LOG_FORMAT = DETAILED_FORMAT if DEBUG_MODE else SIMPLE_FORMAT


def _get_file_handler(log_file: Path, level: int) -> logging.FileHandler:
    """Create a rotating file handler for the given log file."""
    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    return handler


def _get_console_handler(level: int) -> logging.StreamHandler:
    """Create a console handler for streaming logs."""
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    return handler


def configure_pallet_logging(
    log_level: Optional[str] = None, include_console: bool = True
) -> logging.Logger:
    """
    Configure logging for Pallet orchestrator and core modules.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        include_console: Whether to also log to console

    Returns:
        Configured logger instance
    """
    if log_level is None:
        log_level = LOG_LEVEL

    level = getattr(logging, log_level.upper(), logging.INFO)

    # Get or create logger
    logger = logging.getLogger("pallet")
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add file handler
    file_handler = _get_file_handler(PALLET_LOG_DIR / "pallet.log", level)
    logger.addHandler(file_handler)

    # Add console handler if requested
    if include_console:
        console_handler = _get_console_handler(level)
        logger.addHandler(console_handler)

    return logger


def configure_agent_logging(
    agent_name: str, log_level: Optional[str] = None, include_console: bool = True
) -> logging.Logger:
    """
    Configure logging for a specific agent.

    Args:
        agent_name: Name of the agent (e.g., "plan", "build", "test")
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        include_console: Whether to also log to console

    Returns:
        Configured logger instance
    """
    if log_level is None:
        log_level = LOG_LEVEL

    level = getattr(logging, log_level.upper(), logging.INFO)

    # Get or create logger
    logger = logging.getLogger(f"agent.{agent_name}")
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add file handler (agent-specific log file)
    file_handler = _get_file_handler(AGENTS_LOG_DIR / f"{agent_name}_agent.log", level)
    logger.addHandler(file_handler)

    # Add console handler if requested
    if include_console:
        console_handler = _get_console_handler(level)
        logger.addHandler(console_handler)

    return logger


def configure_module_logging(module_name: str) -> logging.Logger:
    """
    Configure logging for a specific module.

    This creates a child logger under "pallet" namespace that inherits
    pallet's handlers and configuration.

    Args:
        module_name: Module name (e.g., "orchestrator", "discovery")

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(f"pallet.{module_name}")
    return logger


def get_pallet_logger() -> logging.Logger:
    """Get the main pallet logger (creates if doesn't exist)."""
    return logging.getLogger("pallet")


def get_agent_logger(agent_name: str) -> logging.Logger:
    """Get logger for a specific agent."""
    return logging.getLogger(f"agent.{agent_name}")


# Create module-specific loggers for common modules
orchestrator_logger = configure_module_logging("orchestrator")
discovery_logger = configure_module_logging("discovery")
workflow_engine_logger = configure_module_logging("workflow_engine")
workflow_registry_logger = configure_module_logging("workflow_registry")


# Set up structured logging context support (minimal)
class StructuredLogContext:
    """Helper for adding context to log messages."""

    def __init__(self, **context):
        self.context = context

    def __str__(self):
        items = [f"{k}={v}" for k, v in self.context.items()]
        return " | ".join(items)


def setup_all_logging():
    """Initialize all logging (call once at application startup)."""
    # Configure pallet logger
    configure_pallet_logging(include_console=True)

    # Configure agent loggers
    configure_agent_logging("plan", include_console=False)
    configure_agent_logging("build", include_console=False)
    configure_agent_logging("test", include_console=False)

    # Set up root logger to propagate to pallet
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Log startup info
    logger = get_pallet_logger()
    logger.info("=" * 70)
    logger.info("Pallet Logging Initialized")
    logger.info("=" * 70)
    logger.info(f"Debug mode: {DEBUG_MODE}")
    logger.info(f"Log level: {LOG_LEVEL}")
    logger.info(f"Pallet logs: {PALLET_LOG_DIR / 'pallet.log'}")
    logger.info(f"Agent logs: {AGENTS_LOG_DIR}/<agent_name>_agent.log")
    if ORAS_VERBOSE:
        logger.info("ORAS verbose mode: ENABLED")
    if TRACE_REQUESTS:
        logger.info("Request tracing: ENABLED")
