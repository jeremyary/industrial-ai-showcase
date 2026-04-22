# This project was developed with assistance from AI tools.
"""WMS-Stub entrypoint — demo control panel for the Phase-1 showcase.

Provides two categories of actions for the Showcase Console buttons:
  - Dispatch: sends a FleetMission (DISPATCH) to fleet.missions
  - Camera state: calls the companion fake-camera HTTP API to toggle
    the frame between "empty" and "obstructed"

The scenario catalog (GET /scenarios) tells the Console which buttons
to render and what actions they trigger.
"""

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from common_lib.events import FleetMission, MissionKind
from common_lib.kafka import JsonProducer
from common_lib.logging import configure_logging
from wms_stub import __version__
from wms_stub.scenarios import get_scenario, list_scenarios
from wms_stub.settings import WmsStubSettings

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = WmsStubSettings()
    log = configure_logging(settings.service_name, settings.log_level)
    log.info(
        "startup",
        version=__version__,
        missions_topic=settings.missions_topic,
        fake_camera_url=settings.fake_camera_url or "(disabled)",
    )

    producer = JsonProducer(settings.kafka_bootstrap_servers, client_id=settings.service_name)
    http_client = httpx.AsyncClient(timeout=5.0)

    app.state.settings = settings
    app.state.log = log
    app.state.producer = producer
    app.state.http = http_client
    try:
        yield
    finally:
        await http_client.aclose()
        producer.flush(timeout=5.0)
        log.info("shutdown")


app = FastAPI(title="wms-stub", version=__version__, lifespan=lifespan)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


# ---------------------------------------------------------------------------
# Scenario catalog (Console reads this to render buttons)
# ---------------------------------------------------------------------------

@app.get("/scenarios")
async def get_scenarios() -> dict[str, list[str]]:
    return {"scenarios": list_scenarios()}


@app.get("/scenarios/{name}")
async def get_scenario_detail(name: str) -> dict:
    try:
        s = get_scenario(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "name": s.name,
        "buttons": [{"label": b.label, "action": b.action, "params": b.params} for b in s.buttons],
    }


# ---------------------------------------------------------------------------
# Dispatch mission
# ---------------------------------------------------------------------------

class DispatchRequest(BaseModel):
    robot_id: str = Field(default="")
    route_aisle: str = Field(default="")
    destination: str = Field(default="")


@app.post("/dispatch")
async def dispatch_mission(req: DispatchRequest | None = None) -> dict[str, str]:
    settings: WmsStubSettings = app.state.settings
    log: "BoundLogger" = app.state.log
    producer: JsonProducer = app.state.producer

    robot_id = (req.robot_id if req and req.robot_id else settings.default_robot_id)
    route_aisle = (req.route_aisle if req and req.route_aisle else settings.default_route_aisle)
    destination = (req.destination if req and req.destination else settings.default_destination)
    trace_id = uuid4().hex

    mission = FleetMission(
        trace_id=trace_id,
        kind=MissionKind.DISPATCH,
        robot_id=robot_id,
        policy_version=settings.policy_version,
        params={
            "route_aisle": route_aisle,
            "destination": destination,
        },
    )
    producer.send(settings.missions_topic, key=robot_id, value=mission)
    producer.flush(timeout=2.0)

    log.info(
        "dispatch.sent",
        trace_id=trace_id,
        mission_id=str(mission.mission_id),
        robot_id=robot_id,
        route_aisle=route_aisle,
    )
    return {
        "status": "dispatched",
        "trace_id": trace_id,
        "mission_id": str(mission.mission_id),
        "robot_id": robot_id,
        "route_aisle": route_aisle,
    }


# ---------------------------------------------------------------------------
# Camera state toggle (fake-camera on companion)
# ---------------------------------------------------------------------------

class CameraStateRequest(BaseModel):
    state: str = Field(description="Target state: 'obstructed' or 'empty'.")


@app.post("/drop-pallet")
async def drop_pallet() -> dict[str, str]:
    return await _set_camera_state("obstructed")


@app.post("/clear-pallet")
async def clear_pallet() -> dict[str, str]:
    return await _set_camera_state("empty")


@app.post("/camera/state")
async def set_camera_state(req: CameraStateRequest) -> dict[str, str]:
    return await _set_camera_state(req.state)


async def _set_camera_state(target_state: str) -> dict[str, str]:
    settings: WmsStubSettings = app.state.settings
    log: "BoundLogger" = app.state.log
    http: httpx.AsyncClient = app.state.http

    if not settings.fake_camera_url:
        raise HTTPException(
            status_code=503,
            detail="FAKE_CAMERA_URL not configured — camera state switching unavailable.",
        )

    url = f"{settings.fake_camera_url.rstrip('/')}/state"
    try:
        resp = await http.post(url, json={"state": target_state})
        resp.raise_for_status()
        body = resp.json()
    except httpx.HTTPStatusError as exc:
        log.error("camera.state.http_error", url=url, status=exc.response.status_code)
        raise HTTPException(status_code=502, detail=f"fake-camera returned {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        log.error("camera.state.unreachable", url=url, error=str(exc))
        raise HTTPException(status_code=502, detail=f"fake-camera unreachable: {exc}") from exc

    log.info("camera.state.changed", target=target_state, response=body)
    return {"status": "ok", "camera_state": body.get("state", target_state)}
