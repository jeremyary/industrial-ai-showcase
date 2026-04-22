# This project was developed with assistance from AI tools.
"""Tests for the wms-stub scenario catalog and dispatch logic."""

from unittest.mock import MagicMock

import pytest

from common_lib.events import FleetMission, MissionKind
from wms_stub.scenarios import AISLE_3_OBSTRUCTION, get_scenario, list_scenarios


def test_list_scenarios_contains_aisle3() -> None:
    """Scenario catalog includes the aisle-3 obstruction scenario."""
    assert "aisle-3-obstruction" in list_scenarios()


def test_get_scenario_returns_aisle3() -> None:
    """get_scenario returns the aisle-3 obstruction scenario by name."""
    s = get_scenario("aisle-3-obstruction")
    assert s.name == "aisle-3-obstruction"
    assert len(s.buttons) == 3


def test_get_scenario_unknown_raises() -> None:
    """Unknown scenario name raises KeyError."""
    with pytest.raises(KeyError, match="no-such-scenario"):
        get_scenario("no-such-scenario")


def test_aisle3_scenario_has_dispatch_button() -> None:
    """Aisle-3 scenario includes a Dispatch Mission button."""
    dispatch = [b for b in AISLE_3_OBSTRUCTION.buttons if b.action == "dispatch"]
    assert len(dispatch) == 1
    assert dispatch[0].label == "Dispatch Mission"


def test_aisle3_scenario_has_drop_pallet_button() -> None:
    """Aisle-3 scenario includes a Drop Pallet button."""
    drop = [b for b in AISLE_3_OBSTRUCTION.buttons if b.action == "drop-pallet"]
    assert len(drop) == 1
    assert drop[0].params["to_state"] == "obstructed"


def test_dispatch_creates_correct_mission() -> None:
    """FleetMission for dispatch uses fl-07, aisle-3, and DISPATCH kind."""
    mission = FleetMission(
        trace_id="test-trace",
        kind=MissionKind.DISPATCH,
        robot_id="fl-07",
        policy_version="vla-warehouse-v1.3",
        params={"route_aisle": "aisle-3", "destination": "dock-b"},
    )
    assert mission.kind == MissionKind.DISPATCH
    assert mission.robot_id == "fl-07"
    assert mission.params["route_aisle"] == "aisle-3"
    assert mission.params["destination"] == "dock-b"
