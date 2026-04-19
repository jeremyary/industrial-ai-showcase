# This project was developed with assistance from AI tools.
"""Mission Dispatcher entrypoint.

Phase 1 v1: consume fleet.missions, call host-local VLA endpoint per ADR-026,
emit fleet.ops.events + fleet.telemetry.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI

from common_lib.events import FleetMission, FleetOpsEvent, FleetTelemetry, OpsEventKind
from common_lib.kafka import JsonConsumer, JsonProducer
from common_lib.logging import configure_logging
from mission_dispatcher import __version__
from mission_dispatcher.settings import MissionDispatcherSettings
from mission_dispatcher.vla_client import VlaClient

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger


# Placeholder observation used before sim integration lands in plan item 3.
# Swapped for a real base64-encoded camera frame once Isaac Sim is wired.
_PLACEHOLDER_IMAGE_B64 = ""


async def _dispatch_loop(
    consumer: JsonConsumer[FleetMission],
    producer: JsonProducer,
    vla: VlaClient,
    ops_topic: str,
    telemetry_topic: str,
    log: "BoundLogger",
) -> None:
    loop = asyncio.get_running_loop()
    while True:
        mission = await loop.run_in_executor(None, consumer.poll, 1.0)
        if mission is None:
            await asyncio.sleep(0)
            continue
        log.info(
            "mission.received",
            mission_id=str(mission.mission_id),
            kind=mission.kind,
            robot_id=mission.robot_id,
        )
        producer.send(
            ops_topic,
            key=mission.robot_id,
            value=FleetOpsEvent(
                trace_id=mission.trace_id,
                mission_id=mission.mission_id,
                kind=OpsEventKind.MISSION_RECEIVED,
            ),
        )

        try:
            producer.send(
                ops_topic,
                key=mission.robot_id,
                value=FleetOpsEvent(
                    trace_id=mission.trace_id,
                    mission_id=mission.mission_id,
                    kind=OpsEventKind.VLA_CALL_STARTED,
                ),
            )
            action = await vla.act(
                image_b64=_PLACEHOLDER_IMAGE_B64,
                instruction=f"{mission.kind}: {mission.params.get('reason', 'execute')}",
                trace_id=mission.trace_id,
            )
            log.info(
                "vla.action.received",
                mission_id=str(mission.mission_id),
                model_version=action.model_version,
                action_dim=len(action.action),
            )
            producer.send(
                ops_topic,
                key=mission.robot_id,
                value=FleetOpsEvent(
                    trace_id=mission.trace_id,
                    mission_id=mission.mission_id,
                    kind=OpsEventKind.VLA_CALL_COMPLETED,
                    detail=action.model_version,
                ),
            )
            producer.send(
                telemetry_topic,
                key=mission.robot_id,
                value=FleetTelemetry(
                    trace_id=mission.trace_id,
                    robot_id=mission.robot_id,
                    mission_id=mission.mission_id,
                    pose={"dx": action.action[0], "dy": action.action[1]},
                ),
            )
            producer.send(
                ops_topic,
                key=mission.robot_id,
                value=FleetOpsEvent(
                    trace_id=mission.trace_id,
                    mission_id=mission.mission_id,
                    kind=OpsEventKind.MISSION_COMPLETED,
                ),
            )
        except Exception as exc:  # noqa: BLE001 — loop must not die on one bad mission
            log.exception("vla.call.failed", mission_id=str(mission.mission_id), error=str(exc))
            producer.send(
                ops_topic,
                key=mission.robot_id,
                value=FleetOpsEvent(
                    trace_id=mission.trace_id,
                    mission_id=mission.mission_id,
                    kind=OpsEventKind.VLA_CALL_FAILED,
                    detail=str(exc)[:200],
                ),
            )
            producer.send(
                ops_topic,
                key=mission.robot_id,
                value=FleetOpsEvent(
                    trace_id=mission.trace_id,
                    mission_id=mission.mission_id,
                    kind=OpsEventKind.MISSION_FAILED,
                    detail=str(exc)[:200],
                ),
            )

        producer.flush(timeout=2.0)
        consumer.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = MissionDispatcherSettings()
    log = configure_logging(settings.service_name, settings.log_level)
    log.info("startup", version=__version__, vla_endpoint=settings.vla_endpoint_url)

    extra_kafka: dict[str, str | int | bool] = {}
    if settings.kafka_security_protocol.upper() in {"SSL", "SASL_SSL"}:
        extra_kafka["security.protocol"] = settings.kafka_security_protocol
        extra_kafka["ssl.endpoint.identification.algorithm"] = (
            settings.kafka_ssl_endpoint_identification_algorithm
        )
        extra_kafka["enable.ssl.certificate.verification"] = (
            settings.kafka_enable_ssl_certificate_verification
        )

    producer = JsonProducer(
        settings.kafka_bootstrap_servers,
        client_id=settings.service_name,
        extra_config=extra_kafka or None,
    )
    consumer = JsonConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.consumer_group_id,
        topic=settings.missions_topic,
        model=FleetMission,
        extra_config=extra_kafka or None,
    )
    vla = VlaClient(settings.vla_endpoint_url, timeout_s=settings.vla_request_timeout_s)

    app.state.settings = settings
    app.state.log = log
    app.state.producer = producer
    app.state.consumer = consumer
    app.state.vla = vla

    task = asyncio.create_task(
        _dispatch_loop(
            consumer, producer, vla, settings.ops_events_topic, settings.telemetry_topic, log
        )
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
        await vla.aclose()
        log.info("shutdown")


app = FastAPI(title="mission-dispatcher", version=__version__, lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}
