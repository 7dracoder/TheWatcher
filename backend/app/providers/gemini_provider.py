"""Gemini via Google Generative Language REST API.

If GEMINI_API_KEY is missing, returns a deterministic *mock* run so the
side-by-side comparison UI still renders (clearly flagged mocked=true).
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional

import httpx

from ..config import get_settings
from ..schemas import ModelRun
from .base import LLMProvider, extract_json


def _split_data_uri(data_uri: str) -> tuple[str, str]:
    # data:image/jpeg;base64,XXXX
    try:
        header, b64 = data_uri.split(",", 1)
        mime = header.split(";")[0].replace("data:", "") or "image/jpeg"
        return mime, b64
    except ValueError:
        return "image/jpeg", ""


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self) -> None:
        s = get_settings()
        self.model = s.gemini_model
        self.api_key = s.gemini_api_key
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
            return self._mock(user)

        parts: list[dict] = [{"text": user}]
        if image_data_uri:
            mime, b64 = _split_data_uri(image_data_uri)
            parts.append({"inline_data": {"mime_type": mime, "data": b64}})

        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0.4},
        }
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                # Retry transient rate-limit / overload responses with backoff.
                for attempt in range(3):
                    resp = await client.post(
                        url, params={"key": self.api_key}, json=payload
                    )
                    if resp.status_code in (429, 503) and attempt < 2:
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    break
            latency = int((time.perf_counter() - start) * 1000)
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
            return ModelRun(
                provider="gemini",
                model=self.model,
                ok=True,
                latency_ms=latency,
                prompt_tokens=usage.get("promptTokenCount"),
                completion_tokens=usage.get("candidatesTokenCount"),
                total_tokens=usage.get("totalTokenCount"),
                raw_text=text,
                parsed=extract_json(text),
            )
        except Exception as exc:  # noqa: BLE001
            latency = int((time.perf_counter() - start) * 1000)
            return ModelRun(
                provider="gemini",
                model=self.model,
                ok=False,
                latency_ms=latency,
                error=f"{type(exc).__name__}: {exc}",
            )

    def _mock(self, user: str) -> ModelRun:
        return ModelRun(
            provider="gemini",
            model=self.model,
            ok=False,
            mocked=True,
            raw_text="",
            error="GEMINI_API_KEY not set — add it to enable the Gemini column.",
        )
