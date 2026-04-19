# This project was developed with assistance from AI tools.
"""HTTP client for the host-native VLA serving endpoint (per ADR-026)."""

from typing import Any

import httpx
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class VlaAction(BaseModel):
    """Response shape from POST /act on the host VLA server."""

    action: list[float] = Field(description="7-DOF action vector: dx, dy, dz, droll, dpitch, dyaw, dgrasp.")
    model_version: str
    trace_id: str


class VlaClient:
    """Thin httpx-based client with retry on transient network errors."""

    def __init__(self, endpoint_url: str, timeout_s: float = 10.0) -> None:
        self._endpoint_url = endpoint_url
        self._client = httpx.AsyncClient(timeout=timeout_s)

    async def aclose(self) -> None:
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.2, max=2.0),
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        reraise=True,
    )
    async def act(
        self, image_b64: str, instruction: str, trace_id: str
    ) -> VlaAction:
        payload: dict[str, Any] = {
            "image": image_b64,
            "instruction": instruction,
            "trace_id": trace_id,
        }
        response = await self._client.post(self._endpoint_url, json=payload)
        response.raise_for_status()
        return VlaAction.model_validate(response.json())
