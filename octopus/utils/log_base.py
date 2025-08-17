import logging
import logging.handlers
import os
import sys

import structlog
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global initialization state
_logging_initialized = False
_default_log_level = logging.INFO


class ColoredFormatter(logging.Formatter):
    """Custom colored formatter for console output."""

    COLORS = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[95m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record):
        levelname = record.levelname
        message = super().format(record)
        color = self.COLORS.get(levelname, self.COLORS["RESET"])
        return color + message + self.COLORS["RESET"]


def setup_logging(
    level: int = logging.INFO,
    log_file: str | None = None,
    include_location: bool = True,
    enable_console_colors: bool = True,
    force_reconfigure: bool = False,
) -> None:
    """
    Configure structured logging for Octopus.

    Args:
        level: The logging level
        log_file: The log file path, default is None (auto-generated)
        include_location: Whether to include filename and line number
        enable_console_colors: Whether to enable colored console output
        force_reconfigure: Whether to force reconfiguration even if already configured
    """
    # Configure standard library logging
    root_logger = logging.getLogger()

    # Check if already configured
    if not force_reconfigure and root_logger.handlers:
        # Already configured, just update level if needed
        root_logger.setLevel(level)
        return

    root_logger.setLevel(level)

    # Remove existing handlers only if force_reconfigure is True
    if force_reconfigure:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    # Get log file path
    if log_file is None:
        # Get the project root (octopus/ directory)
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        log_dir = os.path.join(project_root, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "octopus.log")

    # Configure structlog processors for console output
    console_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if include_location:
        console_processors.append(
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            )
        )

    # Add console renderer
    console_processors.append(structlog.dev.ConsoleRenderer(colors=False))

    # Configure structlog for console output
    structlog.configure(
        processors=console_processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,  # type: ignore[arg-type]
        cache_logger_on_first_use=True,
    )

    # Add console handler with color support
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if enable_console_colors:
        console_handler.setFormatter(ColoredFormatter("%(message)s"))
    else:
        console_handler.setFormatter(logging.Formatter("%(message)s"))

    root_logger.addHandler(console_handler)

    # Add file handler with clean format (no color codes)
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)

        # Create a clean formatter for file output that removes color codes
        class CleanFormatter(logging.Formatter):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Pre-compile regex pattern to avoid import during shutdown
                import re
                self.ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
            
            def format(self, record):
                # Remove ANSI color codes from the message
                if hasattr(record, "msg"):
                    record.msg = self.ansi_escape.sub("", str(record.msg))
                return super().format(record)

        file_handler.setFormatter(CleanFormatter("%(message)s"))
        root_logger.addHandler(file_handler)

        logger = structlog.get_logger("setup")
        logger.info("Logging to file", log_file=log_file)

    except Exception as e:
        logger = structlog.get_logger("setup")
        logger.error("Failed to set up file logging", log_file=log_file, error=str(e))


def setup_enhanced_logging(
    level: str | int = "INFO",
    log_file: str | None = None,
    include_location: bool = True,
    enable_console_colors: bool = True,
    force_reconfigure: bool = False,
) -> None:
    """
    Enhanced logging setup function for main entry modules.

    This function is designed to be used in main entry modules as specified in workspace rules.
    It provides a simplified interface for setting up logging with sensible defaults.

    Args:
        level: The logging level as string or int
        log_file: The log file path, default is None (auto-generated)
        include_location: Whether to include filename and line number
        enable_console_colors: Whether to enable colored console output
        force_reconfigure: Whether to force reconfiguration even if already configured
    """
    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper())

    # Call the existing setup_logging function
    setup_logging(
        level=level,
        log_file=log_file,
        include_location=include_location,
        enable_console_colors=enable_console_colors,
        force_reconfigure=force_reconfigure,
    )


def _ensure_logging_initialized(level: int | None = None) -> None:
    """Ensure logging is initialized only once."""
    global _logging_initialized, _default_log_level

    if not _logging_initialized:
        init_level = level if level is not None else _default_log_level
        setup_logging(level=init_level, include_location=True)
        _logging_initialized = True


def set_default_log_level(level: int) -> None:
    """Set the default log level for automatic initialization."""
    global _default_log_level
    _default_log_level = level


def get_logger(name: str, level: int | None = None) -> structlog.BoundLogger:
    """
    Get a structlog logger with the specified name.

    Args:
        name: The name of the logger
        level: Optional logging level for initialization

    Returns:
        A structlog BoundLogger instance
    """
    _ensure_logging_initialized(level)
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities."""

    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger for this class."""
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__module__)
        return self._logger


# Pre-configured loggers for common components
protocol_logger = get_logger("octopus.protocol")
gateway_logger = get_logger("octopus.gateway")
receiver_logger = get_logger("octopus.receiver")
message_logger = get_logger("octopus.message")
agent_logger = get_logger("octopus.agent")
api_logger = get_logger("octopus.api")
common_logger = get_logger("octopus.common")

# Auto-initialize logging when this module is imported
_ensure_logging_initialized()


# Usage Examples:
#
# 1. Basic usage:
#    from octopus.utils.log_base import get_logger
#    logger = get_logger(__name__)
#    logger.info("Processing request", request_id="123", method="GET")
#
# 2. Using LoggerMixin:
#    from octopus.utils.log_base import LoggerMixin
#    class MyClass(LoggerMixin):
#        def my_method(self):
#            self.logger.info("Method called", param="value")
#
# 3. Using pre-configured loggers:
#    from octopus.utils.log_base import message_logger
#    message_logger.error("Failed to send message", error="timeout")
#
# 4. Exception logging:
#    try:
#        # some operation
#        pass
#    except Exception as e:
#        logger.exception("Operation failed", operation="data_processing")
