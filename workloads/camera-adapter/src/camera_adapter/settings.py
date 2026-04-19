# This project was developed with assistance from AI tools.
"""Camera adapter settings."""

from pydantic import Field

from common_lib.config import ServiceSettings


class CameraAdapterSettings(ServiceSettings):
    service_name: str = "camera-adapter"

    events_topic: str = "fleet.events"

    cosmos_endpoint_url: str = Field(
        default="http://cosmos-reason.cosmos.svc.cluster.local:8000/v1/chat/completions",
        description="Cosmos Reason (vLLM OpenAI-compatible) endpoint for scene reasoning.",
    )
    cosmos_model: str = Field(default="cosmos-reason-1")
    cosmos_request_timeout_s: float = Field(default=20.0)

    # Comma-separated RTSP URIs. Phase 1 default is empty — Isaac Sim doesn't
    # expose RTSP on the warehouse scene out of the box; frames can instead
    # be POSTed to /api/frame for testing. Phase 2 wires Isaac Sim cameras.
    rtsp_uris: str = Field(default="")
    frame_sample_hz: float = Field(default=1.0)

    # Default reasoning prompt. Overrideable per-frame via the POST payload.
    default_prompt: str = Field(
        default=(
            "You are watching a warehouse aisle camera. Reply with a compact JSON object "
            "{\"event_class\": str, \"location\": str, \"confidence\": float, \"detail\": str}. "
            "Use event_class='aisle.obstruction' for pallet/debris/person blocking an aisle; "
            "'scene.quiescent' if nothing notable. location like 'aisle-3' or 'zone-b'."
        )
    )
