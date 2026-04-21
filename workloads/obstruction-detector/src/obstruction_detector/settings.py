# This project was developed with assistance from AI tools.
"""obstruction-detector settings."""

from pydantic import Field

from common_lib.config import ServiceSettings


class ObstructionDetectorSettings(ServiceSettings):
    service_name: str = "obstruction-detector"

    # Kafka topics
    frames_topic: str = Field(default="warehouse.cameras.aisle3")
    alerts_topic: str = Field(default="fleet.safety.alerts")
    consumer_group: str = Field(default="obstruction-detector")

    # Cosmos Reason 2 endpoint (vLLM OpenAI-compatible)
    cosmos_endpoint_url: str = Field(
        default="http://cosmos-reason.cosmos.svc.cluster.local:8000/v1/chat/completions",
    )
    cosmos_model: str = Field(default="cosmos-reason-2")
    cosmos_request_timeout_s: float = Field(default=20.0)

    # Debounce: fire an alert only after this many consecutive same-verdict
    # frames (avoids single-frame flicker). `1` = emit on every transition.
    dwell_frames: int = Field(default=2, ge=1)

    # Aisle this detector instance covers. Phase-1 ships one detector per
    # (camera, aisle) pair; Phase-2 may consolidate if traffic volume warrants.
    aisle_id: str = Field(default="aisle-3")

    # Prompt the VLM sees. Validated against our 1920x1080 trial pair.
    default_prompt: str = Field(
        default=(
            "Is this aisle obstructed? Respond ONLY with a single JSON object of the form:\n"
            "{\"obstruction\": true|false, \"label\": \"<short noun phrase>\", "
            "\"confidence\": <0..1>, \"detail\": \"<one short sentence>\"}"
        )
    )
