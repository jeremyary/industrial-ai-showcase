# This project was developed with assistance from AI tools.
"""fake-camera entrypoint.

Two background responsibilities + one HTTP surface:
- `publish_loop` emits the currently-selected frame to Kafka at `publish_hz`.
- `/state` POST switches which frame is being emitted; `/state` GET returns current.
- `/healthz` + `/readyz` for K8s probes.

One fake-camera instance per logical camera — camera_id / aisle_id come from env
(see FakeCameraSettings), which should match warehouse-topology.yaml entries.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import threading
from contextlib import asynccontextmanager

from common_lib.kafka import JsonProducer
from common_lib.logging import configure_logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from fake_camera import __version__
from fake_camera.publisher import StateHolder, command_consumer_loop, publish_loop
from fake_camera.settings import FakeCameraSettings


class StateRequest(BaseModel):
    state: str = Field(description="Logical state name; must match a key in frame_map.")


def _load_frames(settings: FakeCameraSettings) -> dict[str, bytes]:
    frame_map = json.loads(settings.frame_map_json)
    frames_dir = pathlib.Path(settings.frames_dir)
    frames: dict[str, bytes] = {}
    for state, filename in frame_map.items():
        path = frames_dir / filename
        if not path.is_file():
            raise RuntimeError(f"frame missing for state {state!r}: {path}")
        frames[state] = path.read_bytes()
    return frames


def _kafka_extra_config(settings: FakeCameraSettings) -> dict[str, str | int | bool]:
    cfg: dict[str, str | int | bool] = {}
    if settings.kafka_security_protocol.upper() == "SSL":
        cfg["security.protocol"] = "SSL"
        cfg["ssl.ca.location"] = settings.kafka_ca_cert_path
        # Disable certificate verification warnings during Phase-1 validation;
        # production hardening: set ssl.endpoint.identification.algorithm=https
        # and rely on the broker's Route hostname SAN.
        cfg["ssl.endpoint.identification.algorithm"] = "none"
    return cfg


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = FakeCameraSettings()
    log = configure_logging(settings.service_name, settings.log_level)

    frames = _load_frames(settings)
    if settings.initial_state not in frames:
        raise RuntimeError(
            f"initial_state={settings.initial_state!r} not in frame_map keys {list(frames)}"
        )

    state = StateHolder(current=settings.initial_state)

    producer = JsonProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        client_id=settings.service_name,
        extra_config=_kafka_extra_config(settings),
    )

    log.info(
        "startup",
        version=__version__,
        camera_id=settings.camera_id,
        aisle_id=settings.aisle_id,
        topic=settings.topic,
        publish_hz=settings.publish_hz,
        states=list(frames.keys()),
        initial_state=settings.initial_state,
    )

    task = asyncio.create_task(publish_loop(settings, frames, state, producer, log))

    threading.Thread(
        target=command_consumer_loop,
        args=(settings, frames, state, _kafka_extra_config(settings), log),
        daemon=True,
        name="cmd-consumer",
    ).start()

    app.state.settings = settings
    app.state.log = log
    app.state.frames = frames
    app.state.state_holder = state
    app.state.task = task

    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
        producer.flush(timeout=5.0)
        log.info("shutdown")


app = FastAPI(title="fake-camera", version=__version__, lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    task = getattr(app.state, "task", None)
    if task is None or task.done():
        return {"status": "not-ready"}
    return {"status": "ready"}


@app.get("/state")
async def get_state() -> dict[str, str]:
    return {"state": app.state.state_holder.current}


@app.post("/state")
async def set_state(req: StateRequest) -> dict[str, str]:
    frames: dict[str, bytes] = app.state.frames
    if req.state not in frames:
        raise HTTPException(
            status_code=400,
            detail=f"unknown state {req.state!r}; known: {list(frames.keys())}",
        )
    state: StateHolder = app.state.state_holder
    previous, state.current = state.current, req.state
    app.state.log.info("state.changed", from_=previous, to=state.current)
    return {"state": state.current, "previous": previous}
