# This project was developed with assistance from AI tools.
"""Pydantic models for Kafka event payloads.

Single source of truth for `fleet.events`, `fleet.missions`, `fleet.telemetry`,
and `fleet.ops.events` schemas. Phase 1 uses JSON on the wire; Phase 2 migrates
to Avro with Schema Registry — these models become the generation source.
"""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def _now() -> datetime:
    return datetime.now(UTC)


class EventClass(str, Enum):
    """Scene-reasoning event classes emitted by camera-adapter/WMS-stub.

    Phase 1 covers only the obstruction beat from the 5-min demo.
    Additional classes land when later demo beats earn them.
    """

    AISLE_OBSTRUCTION = "aisle.obstruction"
    SCENE_QUIESCENT = "scene.quiescent"


class FleetEvent(BaseModel):
    """Camera/scene event emitted by camera-adapter (live) or wms-stub (scripted)."""

    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    trace_id: str = Field(description="OpenTelemetry trace ID for end-to-end correlation.")
    event_class: EventClass
    source: str = Field(description="Logical source: 'camera-adapter' or 'wms-stub'.")
    location: str = Field(description="Scene-local location identifier, e.g. 'aisle-3', 'zone-b'.")
    confidence: float = Field(ge=0.0, le=1.0)
    emitted_at: datetime = Field(default_factory=_now)
    payload: dict[str, str | float | int | bool] = Field(default_factory=dict)


class MissionKind(str, Enum):
    REROUTE = "reroute"
    PICKUP = "pickup"
    DROPOFF = "dropoff"
    STANDBY = "standby"


class FleetMission(BaseModel):
    """Mission dispatched from fleet-manager to mission-dispatcher."""

    model_config = ConfigDict(frozen=True)

    mission_id: UUID = Field(default_factory=uuid4)
    trace_id: str
    kind: MissionKind
    robot_id: str = Field(description="Target robot identifier, e.g. 'amr-07'.")
    triggered_by_event_id: UUID | None = Field(default=None, description="Upstream event, if any.")
    policy_version: str = Field(description="VLA policy version to execute this mission with.")
    params: dict[str, str | float | int | bool] = Field(default_factory=dict)
    emitted_at: datetime = Field(default_factory=_now)


class OpsEventKind(str, Enum):
    MISSION_RECEIVED = "mission.received"
    MISSION_STARTED = "mission.started"
    MISSION_COMPLETED = "mission.completed"
    MISSION_FAILED = "mission.failed"
    VLA_CALL_STARTED = "vla.call.started"
    VLA_CALL_COMPLETED = "vla.call.completed"
    VLA_CALL_FAILED = "vla.call.failed"


class FleetOpsEvent(BaseModel):
    """Operational transitions emitted by mission-dispatcher during execution."""

    model_config = ConfigDict(frozen=True)

    ops_event_id: UUID = Field(default_factory=uuid4)
    trace_id: str
    mission_id: UUID
    kind: OpsEventKind
    detail: str | None = None
    emitted_at: datetime = Field(default_factory=_now)


class FleetTelemetry(BaseModel):
    """Robot telemetry fed back to hub observability."""

    model_config = ConfigDict(frozen=True)

    telemetry_id: UUID = Field(default_factory=uuid4)
    trace_id: str
    robot_id: str
    mission_id: UUID | None = None
    pose: dict[str, float] = Field(default_factory=dict, description="x,y,z,roll,pitch,yaw.")
    battery_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    anomaly_score: float | None = Field(default=None, ge=0.0, le=1.0)
    emitted_at: datetime = Field(default_factory=_now)
