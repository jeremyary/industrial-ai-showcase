# This project was developed with assistance from AI tools.
"""Tests for the rule-based decisioning engine."""

from common_lib.events import EventClass, FleetEvent, MissionKind
from fleet_manager.decisioning import AisleObstructionReroute, default_engine


def test_aisle_obstruction_rule_applies_above_threshold() -> None:
    event = FleetEvent(
        trace_id="t1",
        event_class=EventClass.AISLE_OBSTRUCTION,
        source="wms-stub",
        location="aisle-3",
        confidence=0.91,
    )
    rule = AisleObstructionReroute()
    assert rule.applies(event)


def test_aisle_obstruction_rule_skips_below_threshold() -> None:
    event = FleetEvent(
        trace_id="t1",
        event_class=EventClass.AISLE_OBSTRUCTION,
        source="wms-stub",
        location="aisle-3",
        confidence=0.5,
    )
    rule = AisleObstructionReroute()
    assert not rule.applies(event)


def test_default_engine_emits_reroute_mission() -> None:
    event = FleetEvent(
        trace_id="t1",
        event_class=EventClass.AISLE_OBSTRUCTION,
        source="wms-stub",
        location="aisle-3",
        confidence=0.91,
        payload={"affected_robot_id": "amr-07"},
    )
    engine = default_engine(policy_version="vla-warehouse-v1.3")
    mission = engine.evaluate(event)
    assert mission is not None
    assert mission.kind == MissionKind.REROUTE
    assert mission.robot_id == "amr-07"
    assert mission.trace_id == "t1"
    assert mission.policy_version == "vla-warehouse-v1.3"
    assert mission.triggered_by_event_id == event.event_id


def test_default_engine_skips_quiescent_events() -> None:
    event = FleetEvent(
        trace_id="t1",
        event_class=EventClass.SCENE_QUIESCENT,
        source="wms-stub",
        location="aisle-3",
        confidence=0.99,
    )
    engine = default_engine()
    assert engine.evaluate(event) is None
