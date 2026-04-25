# This project was developed with assistance from AI tools.
"""MES-Stub entrypoint — SAP PP/DS-shaped order emitter for the brownfield demo beat.

Publishes MesOrder events to `mes.orders`. Two modes:
  - On-demand: Console or curl triggers POST /emit
  - Streaming: POST /stream/start emits an order every N seconds
"""

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field

from common_lib.events import MesOrder, MesOrderPriority
from common_lib.kafka import JsonProducer
from common_lib.logging import configure_logging
from mes_stub import __version__
from mes_stub.orders import TEMPLATES
from mes_stub.settings import MesStubSettings

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger


_stream_task: asyncio.Task | None = None  # type: ignore[type-arg]
_stream_idx: int = 0


def _next_order(settings: MesStubSettings, factory: str | None = None) -> MesOrder:
    global _stream_idx
    tpl = TEMPLATES[_stream_idx % len(TEMPLATES)]
    _stream_idx += 1
    return MesOrder(
        trace_id=uuid4().hex,
        material=tpl.material,
        quantity=tpl.quantity,
        source_location=tpl.source_location,
        destination_location=tpl.destination_location,
        priority=MesOrderPriority.NORMAL,
        factory=factory or settings.default_factory,
    )


async def _stream_loop(
    producer: JsonProducer,
    settings: MesStubSettings,
    log: "BoundLogger",
) -> None:
    while True:
        order = _next_order(settings)
        producer.send(settings.orders_topic, key=order.factory, value=order)
        producer.flush(timeout=2.0)
        log.info(
            "order.streamed",
            order_id=str(order.order_id),
            material=order.material,
            factory=order.factory,
        )
        await asyncio.sleep(settings.stream_interval_s)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = MesStubSettings()
    log = configure_logging(settings.service_name, settings.log_level)
    log.info("startup", version=__version__, orders_topic=settings.orders_topic)

    producer = JsonProducer(settings.kafka_bootstrap_servers, client_id=settings.service_name)

    app.state.settings = settings
    app.state.log = log
    app.state.producer = producer
    try:
        yield
    finally:
        global _stream_task
        if _stream_task and not _stream_task.done():
            _stream_task.cancel()
            try:
                await _stream_task
            except asyncio.CancelledError:
                pass
            _stream_task = None
        producer.flush(timeout=5.0)
        log.info("shutdown")


app = FastAPI(title="mes-stub", version=__version__, lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


class EmitRequest(BaseModel):
    material: str = Field(default="")
    quantity: int = Field(default=0, gt=-1)
    source_location: str = Field(default="")
    destination_location: str = Field(default="")
    priority: MesOrderPriority = MesOrderPriority.NORMAL
    factory: str = Field(default="")


@app.post("/emit")
async def emit_order(req: EmitRequest | None = None) -> dict[str, str]:
    """Emit a single MES order. Uses template defaults if fields are empty."""
    settings: MesStubSettings = app.state.settings
    log: "BoundLogger" = app.state.log
    producer: JsonProducer = app.state.producer

    if req and req.material:
        order = MesOrder(
            trace_id=uuid4().hex,
            material=req.material,
            quantity=req.quantity or 1,
            source_location=req.source_location or settings.default_source,
            destination_location=req.destination_location or settings.default_destination,
            priority=req.priority,
            factory=req.factory or settings.default_factory,
        )
    else:
        order = _next_order(settings, factory=(req.factory if req and req.factory else None))

    producer.send(settings.orders_topic, key=order.factory, value=order)
    producer.flush(timeout=2.0)

    log.info(
        "order.emitted",
        order_id=str(order.order_id),
        material=order.material,
        factory=order.factory,
    )
    return {
        "status": "emitted",
        "order_id": str(order.order_id),
        "material": order.material,
        "factory": order.factory,
    }


@app.post("/stream/start")
async def stream_start() -> dict[str, str]:
    """Start emitting orders at a steady interval."""
    global _stream_task
    if _stream_task and not _stream_task.done():
        return {"status": "already_running"}

    settings: MesStubSettings = app.state.settings
    log: "BoundLogger" = app.state.log
    producer: JsonProducer = app.state.producer

    _stream_task = asyncio.create_task(_stream_loop(producer, settings, log))
    log.info("stream.started", interval_s=settings.stream_interval_s)
    return {"status": "started", "interval_s": str(settings.stream_interval_s)}


@app.post("/stream/stop")
async def stream_stop() -> dict[str, str]:
    """Stop the steady order stream."""
    global _stream_task
    if _stream_task and not _stream_task.done():
        _stream_task.cancel()
        try:
            await _stream_task
        except asyncio.CancelledError:
            pass
        _stream_task = None
        app.state.log.info("stream.stopped")
        return {"status": "stopped"}
    return {"status": "not_running"}
