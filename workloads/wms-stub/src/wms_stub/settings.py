# This project was developed with assistance from AI tools.
"""WMS-Stub settings — extends common_lib.ServiceSettings."""

from common_lib.config import ServiceSettings


class WmsStubSettings(ServiceSettings):
    service_name: str = "wms-stub"
    events_topic: str = "fleet.events"
