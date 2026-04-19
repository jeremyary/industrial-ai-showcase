# This project was developed with assistance from AI tools.
"""Cosmos Reason HTTP client via vLLM's OpenAI-compatible chat completions."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class SceneReasoning(BaseModel):
    event_class: str
    location: str = "unknown"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    detail: str = ""


class CosmosClient:
    def __init__(self, endpoint_url: str, model: str, timeout_s: float = 20.0) -> None:
        self._endpoint_url = endpoint_url
        self._model = model
        self._client = httpx.AsyncClient(timeout=timeout_s)

    async def aclose(self) -> None:
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=3.0),
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        reraise=True,
    )
    async def reason(self, image_b64: str, prompt: str) -> SceneReasoning:
        """POST a single-image chat completion; parse the reply as SceneReasoning JSON."""
        body: dict[str, Any] = {
            "model": self._model,
            "temperature": 0.0,
            "max_tokens": 200,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                    ],
                }
            ],
        }
        resp = await self._client.post(self._endpoint_url, json=body)
        resp.raise_for_status()
        payload = resp.json()
        content = payload["choices"][0]["message"]["content"]
        return _parse_response(content)


_JSON_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)


def _parse_response(text: str) -> SceneReasoning:
    """Extract the first JSON object from the model's reply and coerce to SceneReasoning.

    Models emit surrounding prose or markdown fences; keep parsing lenient.
    """
    match = _JSON_RE.search(text)
    if match is None:
        return SceneReasoning(event_class="scene.quiescent", confidence=0.3, detail=text[:200])
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError:
        return SceneReasoning(event_class="scene.quiescent", confidence=0.3, detail=text[:200])
    try:
        return SceneReasoning.model_validate(raw)
    except ValidationError:
        return SceneReasoning(event_class="scene.quiescent", confidence=0.3, detail=str(raw)[:200])
