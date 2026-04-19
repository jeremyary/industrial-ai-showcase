# This project was developed with assistance from AI tools.
"""WMS-Stub entrypoint — scripted scenario emitter for the 5-min demo loop."""

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException

from common_lib.kafka import JsonProducer
from common_lib.logging import configure_logging
from wms_stub import __version__
from wms_stub.scenarios import Scenario, get_scenario, list_scenarios, new_trace_id
from wms_stub.settings import WmsStubSettings

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger

_running_scenarios: dict[str, asyncio.Task[None]] = {}


async def _run_scenario(
    scenario: Scenario,
    trace_id: str,
    producer: JsonProducer,
    topic: str,
    log: "BoundLogger",
) -> None:
    log.info("scenario.started", scenario=scenario.name, trace_id=trace_id)
    start = asyncio.get_running_loop().time()
    for scheduled in scenario.events:
        delay = scheduled.fire_at_seconds - (asyncio.get_running_loop().time() - start)
        if delay > 0:
            await asyncio.sleep(delay)
        event = scheduled.materialize(trace_id)
        producer.send(topic, key=event.location, value=event)
        producer.flush(timeout=2.0)
        log.info(
            "scenario.event.fired",
            scenario=scenario.name,
            event_id=str(event.event_id),
            event_class=event.event_class,
            location=event.location,
        )
    log.info("scenario.completed", scenario=scenario.name, trace_id=trace_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = WmsStubSettings()
    log = configure_logging(settings.service_name, settings.log_level)
    log.info("startup", version=__version__)

    producer = JsonProducer(settings.kafka_bootstrap_servers, client_id=settings.service_name)
    app.state.settings = settings
    app.state.log = log
    app.state.producer = producer
    try:
        yield
    finally:
        for task in _running_scenarios.values():
            task.cancel()
        producer.flush(timeout=5.0)
        log.info("shutdown")


app = FastAPI(title="wms-stub", version=__version__, lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/scenarios")
async def get_scenarios() -> dict[str, list[str]]:
    return {"scenarios": list_scenarios()}


@app.post("/scenarios/{name}/run")
async def run_scenario(name: str) -> dict[str, str]:
    try:
        scenario = get_scenario(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if name in _running_scenarios and not _running_scenarios[name].done():
        raise HTTPException(status_code=409, detail=f"Scenario {name} already running.")

    trace_id = new_trace_id()
    task = asyncio.create_task(
        _run_scenario(scenario, trace_id, app.state.producer, app.state.settings.events_topic, app.state.log)
    )
    _running_scenarios[name] = task
    return {"status": "started", "trace_id": trace_id, "scenario": name}


@app.post("/scenarios/{name}/cancel")
async def cancel_scenario(name: str) -> dict[str, str]:
    task = _running_scenarios.get(name)
    if task is None or task.done():
        raise HTTPException(status_code=404, detail=f"No running scenario {name}.")
    task.cancel()
    return {"status": "cancelled", "scenario": name}
