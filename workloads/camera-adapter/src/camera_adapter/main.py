# This project was developed with assistance from AI tools.
"""FastAPI entrypoint for camera-adapter. Phase 1 scaffold — RTSP ingestion + Cosmos Reason client + Kafka producer land in follow-up commits."""

from fastapi import FastAPI

from camera_adapter import __version__

app = FastAPI(title="camera-adapter", version=__version__)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
