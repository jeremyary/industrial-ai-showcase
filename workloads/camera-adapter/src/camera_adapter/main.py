# This project was developed with assistance from AI tools.
"""Camera adapter entrypoint.

Phase 1: runs the frame → Cosmos Reason → Kafka pipeline. RTSP ingestion is
optional — if `RTSP_URIS` is empty, the service idles and accepts test frames
via `POST /api/frame` (base64-encoded JPEG body). Phase 2 wires live RTSP
from Isaac Sim's overhead warehouse cameras.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import Body, FastAPI, HTTPException
from pydantic import BaseModel, Field

from camera_adapter import __version__
from camera_adapter.cosmos_client import CosmosClient, SceneReasoning
from camera_adapter.settings import CameraAdapterSettings
from common_lib.events import EventClass, FleetEvent
from common_lib.kafka import JsonProducer
from common_lib.logging import configure_logging

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger


class FrameIn(BaseModel):
    image_b64: str = Field(description="Base64-encoded JPEG bytes.")
    location: str = Field(description="Logical location for the event, e.g. 'aisle-3'.")
    trace_id: str
    prompt: str | None = None


async def _emit_event(
    reasoning: SceneReasoning,
    frame: FrameIn,
    producer: JsonProducer,
    topic: str,
    log: "BoundLogger",
) -> FleetEvent:
    try:
        event_class = EventClass(reasoning.event_class)
    except ValueError:
        log.warning(
            "reasoning.unknown_class",
            class_=reasoning.event_class,
            detail=reasoning.detail[:80],
        )
        event_class = EventClass.SCENE_QUIESCENT

    event = FleetEvent(
        trace_id=frame.trace_id,
        event_class=event_class,
        source="camera-adapter",
        location=reasoning.location or frame.location,
        confidence=reasoning.confidence,
        payload={"detail": reasoning.detail[:200]},
    )
    producer.send(topic, key=event.location, value=event)
    producer.flush(timeout=2.0)
    log.info(
        "event.emitted",
        event_id=str(event.event_id),
        event_class=event_class,
        confidence=event.confidence,
        location=event.location,
    )
    return event


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = CameraAdapterSettings()
    log = configure_logging(settings.service_name, settings.log_level)
    log.info("startup", version=__version__, cosmos_endpoint=settings.cosmos_endpoint_url)

    producer = JsonProducer(settings.kafka_bootstrap_servers, client_id=settings.service_name)
    cosmos = CosmosClient(
        endpoint_url=settings.cosmos_endpoint_url,
        model=settings.cosmos_model,
        timeout_s=settings.cosmos_request_timeout_s,
    )

    app.state.settings = settings
    app.state.log = log
    app.state.producer = producer
    app.state.cosmos = cosmos

    # RTSP ingestion task — idle when no URIs configured.
    rtsp_uris = [u for u in settings.rtsp_uris.split(",") if u.strip()]
    tasks: list[asyncio.Task[None]] = []
    for uri in rtsp_uris:
        log.info("rtsp.not.implemented", uri=uri)
        # Phase 2 spawns one asyncio task per URI that uses PyAV to pull
        # key-frames and feeds each to the pipeline. Stubbed intentionally
        # for Phase 1 since Isaac Sim's warehouse scene doesn't emit RTSP.

    try:
        yield
    finally:
        for t in tasks:
            t.cancel()
        producer.flush(timeout=5.0)
        await cosmos.aclose()
        log.info("shutdown")


app = FastAPI(title="camera-adapter", version=__version__, lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


@app.post("/api/frame")
async def ingest_frame(frame: FrameIn = Body(...)) -> dict[str, str]:
    settings: CameraAdapterSettings = app.state.settings
    cosmos: CosmosClient = app.state.cosmos
    producer: JsonProducer = app.state.producer
    log: BoundLogger = app.state.log

    prompt = frame.prompt or settings.default_prompt

    try:
        reasoning = await cosmos.reason(frame.image_b64, prompt)
    except Exception as exc:
        log.exception("cosmos.call.failed", trace_id=frame.trace_id, error=str(exc))
        raise HTTPException(status_code=502, detail=f"Cosmos Reason call failed: {exc}") from exc

    event = await _emit_event(reasoning, frame, producer, settings.events_topic, log)
    return {
        "event_id": str(event.event_id),
        "event_class": event.event_class,
        "confidence": str(event.confidence),
    }
