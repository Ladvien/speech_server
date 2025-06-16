"""
Rich logging configuration for the TTS API
"""
import logging
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install

# Install rich traceback handler
install(show_locals=True)


def setup_logger(
    name: str, level: int = logging.INFO, console: Optional[Console] = None
) -> logging.Logger:
    """
    Setup a logger with Rich formatting

    Args:
        name: Logger name
        level: Logging level
        console: Rich console instance (optional)

    Returns:
        Configured logger
    """
    # Create console if not provided
    if console is None:
        console = Console()

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Create rich handler
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=True,
        enable_link_path=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        markup=True,
    )

    # Set format
    rich_handler.setFormatter(logging.Formatter(fmt="%(message)s", datefmt="[%X]"))

    # Add handler to logger
    logger.addHandler(rich_handler)

    # Prevent propagation to avoid duplicate logs
    logger.propagate = False

    return logger


def setup_uvicorn_logging(console: Optional[Console] = None):
    """
    Setup uvicorn logging with Rich formatting

    Args:
        console: Rich console instance (optional)
    """
    if console is None:
        console = Console()

    # Configure uvicorn loggers
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()

        rich_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            markup=True,
        )

        rich_handler.setFormatter(logging.Formatter(fmt="%(message)s", datefmt="[%X]"))

        logger.addHandler(rich_handler)
        logger.propagate = False


class TTSLogger:
    """
    Centralized logger for the TTS API with Rich formatting
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self._loggers = {}

    def get_logger(self, name: str, level: int = logging.INFO) -> logging.Logger:
        """
        Get or create a logger with Rich formatting

        Args:
            name: Logger name
            level: Logging level

        Returns:
            Configured logger
        """
        if name not in self._loggers:
            self._loggers[name] = setup_logger(name, level, self.console)
        return self._loggers[name]

    def setup_all_logging(self):
        """Setup all logging for the application"""
        # Setup main application logging
        self.get_logger("chatterbox_tts_api")

        # Setup uvicorn logging
        setup_uvicorn_logging(self.console)

        # Setup other third-party loggers
        for logger_name in ["httpx", "asyncio"]:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.WARNING)


# Global logger instance
tts_logger = TTSLogger()


# Convenience function
def get_logger(name: str) -> logging.Logger:
    """Get a logger with Rich formatting"""
    return tts_logger.get_logger(name)
