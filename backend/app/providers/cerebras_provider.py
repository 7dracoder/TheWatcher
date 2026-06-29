"""Gemma via Cerebras — OpenAI-compatible Chat Completions."""
from __future__ import annotations

import time
from typing import Optional

import httpx

from ..config import get_settings
from ..schemas import ModelRun
from .base import LLMProvider, extract_json


class CerebrasGemmaProvider(LLMProvider):
    name = "gemma"

    def __init__(self) -> None:
        s = get_settings()
        self.model = s.cerebras_model
        self.base_url = s.cerebras_base_url.rstrip("/")
        self.api_key = s.cerebras_api_key
        self.enabled = bool(self.api_key)

    async def run(
        self,
        *,
        system: str,
        user: str,
        image_data_uri: Optional[str] = None,
        reasoning_effort: str = "default",
    ) -> ModelRun:
        if not self.enabled:
            return ModelRun(
                provider="gemma",
                model=self.model,
                ok=False,
                mocked=True,
                raw_text="",
                error="CEREBRAS_API_KEY not set",
            )

        content: list[dict] | str
        if image_data_uri:
            content = [
                {"type": "text", "text": user},
                {"type": "image_url", "image_url": {"url": image_data_uri}},
            ]
        else:
            content = user

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            "temperature": 0.4,
        }
        if reasoning_effort != "default":
            payload["reasoning_effort"] = reasoning_effort

        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
            latency = int((time.perf_counter() - start) * 1000)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return ModelRun(
                provider="gemma",
                model=self.model,
                ok=True,
                latency_ms=latency,
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
                raw_text=text,
                parsed=extract_json(text),
            )
        except Exception as exc:  # noqa: BLE001 — surface any failure to the UI
            latency = int((time.perf_counter() - start) * 1000)
            return ModelRun(
                provider="gemma",
                model=self.model,
                ok=False,
                latency_ms=latency,
                raw_text="",
                error=f"{type(exc).__name__}: {exc}",
            )
