# This project was developed with assistance from AI tools.
"""Fleet Manager entrypoint. Phase 1 v1: consume fleet.events, apply rules, emit fleet.missions."""

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI

from common_lib.events import FleetEvent
from common_lib.kafka import JsonConsumer, JsonProducer
from common_lib.logging import configure_logging
from fleet_manager import __version__
from fleet_manager.decisioning import RuleEngine, default_engine
from fleet_manager.settings import FleetManagerSettings

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger


async def _consume_loop(
    consumer: JsonConsumer[FleetEvent],
    producer: JsonProducer,
    engine: RuleEngine,
    missions_topic: str,
    log: "BoundLogger",
) -> None:
    loop = asyncio.get_running_loop()
    while True:
        event = await loop.run_in_executor(None, consumer.poll, 1.0)
        if event is None:
            await asyncio.sleep(0)
            continue
        log.info("event.received", event_id=str(event.event_id), event_class=event.event_class)
        mission = engine.evaluate(event)
        if mission is None:
            consumer.commit()
            continue
        producer.send(missions_topic, key=mission.robot_id, value=mission)
        producer.flush(timeout=2.0)
        consumer.commit()
        log.info(
            "mission.emitted",
            mission_id=str(mission.mission_id),
            robot_id=mission.robot_id,
            kind=mission.kind,
            triggered_by_event_id=str(mission.triggered_by_event_id),
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = FleetManagerSettings()
    log = configure_logging(settings.service_name, settings.log_level)
    log.info("startup", version=__version__, environment=settings.environment)

    producer = JsonProducer(settings.kafka_bootstrap_servers, client_id=settings.service_name)
    consumer = JsonConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.consumer_group_id,
        topic=settings.events_topic,
        model=FleetEvent,
    )
    engine = default_engine(policy_version=settings.policy_version)

    app.state.settings = settings
    app.state.log = log
    app.state.producer = producer
    app.state.consumer = consumer
    app.state.engine = engine

    task = asyncio.create_task(
        _consume_loop(consumer, producer, engine, settings.missions_topic, log)
    )
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        consumer.close()
        producer.flush(timeout=5.0)
        log.info("shutdown")


app = FastAPI(title="fleet-manager", version=__version__, lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}
