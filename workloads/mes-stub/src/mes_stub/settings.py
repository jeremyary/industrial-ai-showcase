# This project was developed with assistance from AI tools.
"""MES-Stub settings — extends common_lib.ServiceSettings."""

from pydantic import Field

from common_lib.config import ServiceSettings


class MesStubSettings(ServiceSettings):
    service_name: str = "mes-stub"

    orders_topic: str = Field(
        default="mes.orders",
        description="Kafka topic for outbound MES production orders.",
    )

    default_factory: str = "factory-a"
    default_source: str = "dock-a"
    default_destination: str = "dock-b"

    stream_interval_s: float = Field(
        default=15.0,
        gt=0.0,
        description="Seconds between orders when streaming is active.",
    )
