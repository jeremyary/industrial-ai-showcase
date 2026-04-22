# This project was developed with assistance from AI tools.
"""Waypoint planner — interpolates poses along a route and emits telemetry.

Phase 1 topology is hard-coded from warehouse-topology.yaml. Phase 2 loads
the topology file at startup and builds routes dynamically.

Tick rate is configurable via WAYPOINT_HZ (default 5 Hz). Each tick publishes
a FleetTelemetry message with the current interpolated pose.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from common_lib.events import FleetTelemetry

if TYPE_CHECKING:
    from common_lib.kafka import JsonProducer
    from structlog.stdlib import BoundLogger

COORDS: dict[str, tuple[float, float, float]] = {
    "dock-a": (-12.0, 0.0, 0.0),
    "dock-b": (15.0, 0.0, 0.0),
    "aisle-3-west": (-9.0, 0.0, 0.0),
    "aisle-3-east": (13.0, 0.0, 0.0),
    "aisle-4-west": (-9.0, 4.0, 0.0),
    "aisle-4-east": (13.0, 4.0, 0.0),
}

ROUTES: dict[str, list[str]] = {
    "aisle-3": ["dock-a", "aisle-3-west", "aisle-3-east", "dock-b"],
    "aisle-4": ["dock-a", "aisle-4-west", "aisle-4-east", "dock-b"],
}

APPROACH_POINTS = {"aisle-3-west", "aisle-4-west"}


@dataclass
class Waypoint:
    x: float
    y: float
    z: float
    is_approach_point: bool = False
    name: str = ""


def _build_waypoints(route_name: str, speed_mps: float, hz: float) -> list[Waypoint]:
    """Generate interpolated waypoints along a named route."""
    names = ROUTES.get(route_name, ROUTES["aisle-3"])
    waypoints: list[Waypoint] = []
    step_dist = speed_mps / hz

    for i in range(len(names) - 1):
        start = COORDS[names[i]]
        end = COORDS[names[i + 1]]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dz = end[2] - start[2]
        seg_len = math.sqrt(dx * dx + dy * dy + dz * dz)
        steps = max(1, int(seg_len / step_dist))

        for s in range(steps):
            t = s / steps
            waypoints.append(Waypoint(
                x=start[0] + dx * t,
                y=start[1] + dy * t,
                z=start[2] + dz * t,
                is_approach_point=(s == steps - 1 and names[i + 1] in APPROACH_POINTS),
                name=names[i + 1] if s == steps - 1 else "",
            ))

    final = COORDS[names[-1]]
    waypoints.append(Waypoint(x=final[0], y=final[1], z=final[2], name=names[-1]))
    return waypoints


@dataclass
class RouteExecution:
    """Manages the execution of a route with pause-at-approach-point semantics."""

    robot_id: str
    trace_id: str
    mission_id: str
    route_name: str
    waypoints: list[Waypoint]
    index: int = 0
    paused: bool = False
    cancelled: bool = False
    clearance_event: asyncio.Event = field(default_factory=asyncio.Event)

    def grant_clearance(self) -> None:
        self.paused = False
        self.clearance_event.set()

    def cancel(self) -> None:
        self.cancelled = True
        self.clearance_event.set()


async def execute_route(
    execution: RouteExecution,
    producer: JsonProducer,
    telemetry_topic: str,
    hz: float,
    log: BoundLogger,
) -> bool:
    """Drive a robot along waypoints, pausing at approach-points.

    Returns True if the route completed, False if cancelled (e.g. reroute).
    """
    interval = 1.0 / hz
    log.info(
        "route.started",
        robot_id=execution.robot_id,
        route=execution.route_name,
        waypoints=len(execution.waypoints),
    )

    while execution.index < len(execution.waypoints):
        if execution.cancelled:
            log.info("route.cancelled", robot_id=execution.robot_id)
            return False

        wp = execution.waypoints[execution.index]

        producer.send(
            telemetry_topic,
            key=execution.robot_id,
            value=FleetTelemetry(
                trace_id=execution.trace_id,
                robot_id=execution.robot_id,
                mission_id=execution.mission_id,
                pose={"x": wp.x, "y": wp.y, "z": wp.z},
            ),
        )
        producer.flush(timeout=0.0)

        if wp.is_approach_point:
            execution.paused = True
            log.info(
                "route.approach_point",
                robot_id=execution.robot_id,
                waypoint=wp.name,
                x=wp.x, y=wp.y,
            )
            execution.clearance_event.clear()
            await execution.clearance_event.wait()
            if execution.cancelled:
                return False
            log.info("route.clearance_received", robot_id=execution.robot_id)

        execution.index += 1
        await asyncio.sleep(interval)

    log.info("route.completed", robot_id=execution.robot_id, route=execution.route_name)
    return True


def plan_route(
    robot_id: str,
    trace_id: str,
    mission_id: str,
    route_aisle: str,
    speed_mps: float = 2.0,
    hz: float = 5.0,
) -> RouteExecution:
    """Create a RouteExecution for a given aisle route."""
    waypoints = _build_waypoints(route_aisle, speed_mps, hz)
    return RouteExecution(
        robot_id=robot_id,
        trace_id=trace_id,
        mission_id=str(mission_id),
        route_name=route_aisle,
        waypoints=waypoints,
    )
