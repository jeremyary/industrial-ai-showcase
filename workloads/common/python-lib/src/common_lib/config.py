# This project was developed with assistance from AI tools.
"""Shared configuration base for industrial-ai-showcase Python services."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    """Base settings any service extends. Reads from env + ConfigMaps mounted as env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = Field(description="Name of the service, used in logs and OTel resources.")
    log_level: str = Field(default="INFO", description="Python logging level.")
    environment: str = Field(default="dev", description="dev | demo | prod.")

    kafka_bootstrap_servers: str = Field(
        default="fleet-kafka-bootstrap.fleet-ops.svc.cluster.local:9092",
        description="Kafka bootstrap servers. Phase 1 uses the plain listener; Phase 2 moves to TLS.",
    )
    kafka_security_protocol: str = Field(default="PLAINTEXT")

    otel_endpoint: str | None = Field(default=None, description="OTLP collector endpoint, e.g. http://tempo:4318.")
