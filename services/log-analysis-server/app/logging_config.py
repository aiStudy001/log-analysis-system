"""
Structured Logging Configuration

Configures JSON-formatted logs with request ID correlation for better debugging and monitoring.
"""
import logging
import sys
from pythonjsonlogger import jsonlogger


def setup_logging(log_level: str = "INFO"):
    """
    Configure structured JSON logging for the application

    Features:
    - JSON-formatted logs for easy parsing
    - Request ID correlation
    - Timestamp, level, logger name, message
    - Sanitization of sensitive data

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create JSON formatter
    log_format = "%(timestamp)s %(level)s %(name)s %(message)s %(request_id)s"
    formatter = CustomJsonFormatter(log_format)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add stdout handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Set specific log levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.info("✅ Structured logging configured")


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with additional fields and sanitization

    Adds:
    - timestamp: ISO 8601 formatted timestamp
    - level: Log level name
    - request_id: Request ID from context (if available)
    """

    def add_fields(self, log_record, record, message_dict):
        """
        Add custom fields to log record

        Args:
            log_record: Dictionary to be formatted as JSON
            record: LogRecord instance
            message_dict: Dict with message and additional fields
        """
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO 8601 format
        if not log_record.get("timestamp"):
            log_record["timestamp"] = self.formatTime(record, self.datefmt)

        # Add level name
        if log_record.get("level"):
            log_record["level"] = record.levelname
        elif log_record.get("levelname"):
            log_record["level"] = log_record.pop("levelname")
        else:
            log_record["level"] = record.levelname

        # Add request ID if available
        if not log_record.get("request_id"):
            # Try to get request_id from extra fields
            request_id = getattr(record, "request_id", None)
            log_record["request_id"] = request_id or "n/a"

        # Sanitize sensitive information
        if "message" in log_record:
            log_record["message"] = self._sanitize_message(log_record["message"])

    def _sanitize_message(self, message: str) -> str:
        """
        Remove sensitive information from log messages

        Args:
            message: Original log message

        Returns:
            Sanitized message
        """
        import re

        if not isinstance(message, str):
            return message

        # Sanitize common sensitive patterns
        patterns = [
            # API keys
            (r"(api[_-]?key|token|secret)[=:\s]+['\"]?([a-zA-Z0-9_-]+)['\"]?", r"\1=[REDACTED]"),
            # Passwords
            (r"(password|passwd|pwd)[=:\s]+['\"]?([^\s'\"]+)['\"]?", r"\1=[REDACTED]"),
            # Connection strings
            (r"postgresql://[^:]+:([^@]+)@", r"postgresql://user:[REDACTED]@"),
            # File paths (keep filename only)
            (r'File "(/[^"]+/)?([^/]+)"', r'File "[REDACTED]/\2"'),
        ]

        sanitized = message
        for pattern, replacement in patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        return sanitized


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
