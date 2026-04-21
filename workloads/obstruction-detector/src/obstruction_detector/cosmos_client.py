# This project was developed with assistance from AI tools.
"""Cosmos Reason 2-8B client — image + prompt → obstruction verdict.

Shape matches what workloads/obstruction-detector/trial.py validated against
the on-cluster Cosmos Reason 2-8B deployment. The Qwen3-VL reasoning parser
puts the model's answer in the `reasoning` field when a parser is active; we
fall through to `content` when it's not, which covers both configurations.
"""

from __future__ import annotations

import json
import re

import httpx
from pydantic import BaseModel, Field, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class ObstructionVerdict(BaseModel):
    obstruction: bool
    label: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    detail: str = ""


_JSON_RE = re.compile(r"\{[\s\S]*?\}", re.DOTALL)


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
    async def reason(self, image_b64: str, prompt: str) -> ObstructionVerdict:
        body = {
            "model": self._model,
            "temperature": 0.0,
            "max_tokens": 256,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        resp = await self._client.post(self._endpoint_url, json=body)
        resp.raise_for_status()
        payload = resp.json()
        msg = payload["choices"][0]["message"]
        raw = msg.get("reasoning") or msg.get("content") or ""
        return _parse_verdict(raw)


def _parse_verdict(text: str) -> ObstructionVerdict:
    match = _JSON_RE.search(text)
    if match is None:
        return ObstructionVerdict(obstruction=False, confidence=0.3, detail=text[:200])
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError:
        return ObstructionVerdict(obstruction=False, confidence=0.3, detail=text[:200])
    try:
        return ObstructionVerdict.model_validate(raw)
    except ValidationError:
        return ObstructionVerdict(obstruction=False, confidence=0.3, detail=str(raw)[:200])
