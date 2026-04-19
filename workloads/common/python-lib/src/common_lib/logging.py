# This project was developed with assistance from AI tools.
"""Shared structlog configuration for industrial-ai-showcase Python services."""

import logging
import sys

import structlog


def configure_logging(service_name: str, level: str = "INFO") -> structlog.stdlib.BoundLogger:
    """Configure structlog + stdlib logging to emit JSON to stdout."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(stream=sys.stdout, level=log_level, format="%(message)s")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger().bind(service=service_name)
