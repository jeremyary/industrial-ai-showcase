# This project was developed with assistance from AI tools.
"""fake-camera settings."""

from pydantic import Field

from common_lib.config import ServiceSettings


class FakeCameraSettings(ServiceSettings):
    service_name: str = "fake-camera"

    # Identity of the camera this process is impersonating — keys match
    # warehouse-topology.yaml cameras.*
    camera_id: str = Field(default="cam-aisle-3")
    aisle_id: str = Field(default="aisle-3")

    # Kafka target. Defaults assume direct-connect to hub's external
    # Route-exposed listener with TLS. In-cluster hub deployments can override
    # with fleet-kafka-bootstrap.fleet-ops.svc.cluster.local:9092 (plaintext).
    topic: str = Field(default="warehouse.cameras.aisle3")
    kafka_security_protocol: str = Field(default="SSL")
    kafka_ca_cert_path: str = Field(default="/etc/kafka/ca.crt")

    # Frame library — where the mounted/baked JPEGs live and which filenames
    # correspond to which logical state. Phase-1 has two states from
    # warehouse-topology.yaml: empty + obstructed.
    frames_dir: str = Field(default="/frames")
    frame_map_json: str = Field(
        default='{"empty": "aisle3_empty.jpg", "obstructed": "aisle3_pallet.jpg"}',
        description="JSON string: logical state -> filename under frames_dir.",
    )
    initial_state: str = Field(default="empty")

    # Publish rate
    publish_hz: float = Field(default=1.0, gt=0.0)

    # HTTP listen port for the control endpoint (/state)
    http_port: int = Field(default=8085)
