# This project was developed with assistance from AI tools.
"""Scripted scenario definitions for the 5-min demo loop."""

from dataclasses import dataclass, field
from uuid import uuid4

from common_lib.events import EventClass, FleetEvent


@dataclass(frozen=True)
class ScheduledEvent:
    """An event fired at `fire_at_seconds` after scenario start."""

    fire_at_seconds: float
    event_class: EventClass
    location: str
    confidence: float
    affected_robot_id: str
    extra_payload: dict[str, str | float | int | bool] = field(default_factory=dict)

    def materialize(self, trace_id: str) -> FleetEvent:
        payload: dict[str, str | float | int | bool] = dict(self.extra_payload)
        payload["affected_robot_id"] = self.affected_robot_id
        return FleetEvent(
            trace_id=trace_id,
            event_class=self.event_class,
            source="wms-stub",
            location=self.location,
            confidence=self.confidence,
            payload=payload,
        )


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    events: tuple[ScheduledEvent, ...]


WAREHOUSE_BASELINE_AISLE3 = Scenario(
    name="warehouse-baseline-aisle3-obstruction",
    description=(
        "The canonical 5-min demo beat. At 45s a pallet drifts into aisle-3 where "
        "AMR-07 is scheduled to pass. Fleet Manager should emit a reroute mission; "
        "Mission Dispatcher should call the host VLA and echo telemetry back to hub."
    ),
    events=(
        ScheduledEvent(
            fire_at_seconds=45.0,
            event_class=EventClass.AISLE_OBSTRUCTION,
            location="aisle-3",
            confidence=0.91,
            affected_robot_id="amr-07",
            extra_payload={"obstruction_kind": "pallet", "side": "left"},
        ),
    ),
)


_CATALOG: dict[str, Scenario] = {WAREHOUSE_BASELINE_AISLE3.name: WAREHOUSE_BASELINE_AISLE3}


def get_scenario(name: str) -> Scenario:
    if name not in _CATALOG:
        raise KeyError(f"Unknown scenario: {name}. Known: {list(_CATALOG)}")
    return _CATALOG[name]


def list_scenarios() -> list[str]:
    return list(_CATALOG)


def new_trace_id() -> str:
    return uuid4().hex
