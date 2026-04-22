# This project was developed with assistance from AI tools.
"""WMS-Stub settings — extends common_lib.ServiceSettings."""

from pydantic import Field

from common_lib.config import ServiceSettings


class WmsStubSettings(ServiceSettings):
    service_name: str = "wms-stub"

    missions_topic: str = "fleet.missions"

    fake_camera_url: str = Field(
        default="",
        description="Base URL of the companion fake-camera HTTP API, e.g. http://fake-camera-route.apps.companion.local:80. Empty disables camera state switching.",
    )

    default_robot_id: str = "fl-07"
    default_route_aisle: str = "aisle-3"
    default_destination: str = "dock-b"
    policy_version: str = "vla-warehouse-v1.3"
