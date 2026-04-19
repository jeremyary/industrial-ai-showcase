# This project was developed with assistance from AI tools.
"""Shared Python utilities for the industrial-ai-showcase workloads.

Import submodules explicitly (e.g. `from common_lib.events import FleetEvent`,
`from common_lib.kafka import JsonProducer`) so optional heavy deps (confluent-kafka,
structlog) aren't dragged in transitively.
"""

__version__ = "0.1.0"
