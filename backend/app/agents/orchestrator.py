"""Runs the 4-agent pipeline, executing each step on BOTH Gemma and Gemini.

For every agent we fire both providers concurrently, capture metrics, then
pick a "primary" parsed result (Gemma preferred, Gemini fallback) to feed the
next agent. The per-agent comparisons are returned for the side-by-side UI.
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from ..providers.base import LLMProvider
from ..providers.cerebras_provider import CerebrasGemmaProvider
from ..providers.gemini_provider import GeminiProvider
from ..schemas import (
    AgentComparison,
    Camera,
    Intersection,
    ModelRun,
    PathPrediction,
    PathRisk,
    PredictionResult,
    RiskResult,
    TrackerResult,
    VisionResult,
    WatchRequest,
    WatchResponse,
)
from . import prompts


class Orchestrator:
    def __init__(self) -> None:
        self.gemma: LLMProvider = CerebrasGemmaProvider()
        self.gemini: LLMProvider = GeminiProvider()

    async def _dual_run(
        self,
        agent: str,
        system: str,
        user: str,
        image_data_uri: Optional[str] = None,
    ) -> AgentComparison:
        gemma_run, gemini_run = await asyncio.gather(
            self.gemma.run(system=system, user=user, image_data_uri=image_data_uri),
            self.gemini.run(system=system, user=user, image_data_uri=image_data_uri),
        )
        return AgentComparison(agent=agent, gemma=gemma_run, gemini=gemini_run)

    @staticmethod
    def _primary(cmp: AgentComparison) -> Optional[dict[str, Any]]:
        """Prefer Gemma's parsed output, fall back to Gemini's."""
        for run in (cmp.gemma, cmp.gemini):
            if run and run.ok and run.parsed:
                return run.parsed
        return None

    async def run(
        self, req: WatchRequest, camera: Camera, incidents: list[str]
    ) -> WatchResponse:
        log: list[str] = []
        comparisons: list[AgentComparison] = []
        image = req.image_data_uri or camera.sample_image

        # 1. Vision
        vcmp = await self._dual_run(
            "vision",
            prompts.VISION_SYSTEM,
            prompts.vision_user(req.object_description, req.mode),
            image_data_uri=image,
        )
        comparisons.append(vcmp)
        vision = _safe(VisionResult, self._primary(vcmp)) or VisionResult(
            object_label=req.object_description,
            context="(no model output — using description as-is)",
        )
        log.append(f"Vision Agent: {vision.object_label} — {vision.context}")

        # 2. Tracker
        tcmp = await self._dual_run(
            "tracker",
            prompts.TRACKER_SYSTEM,
            prompts.tracker_user(camera, vision.context),
        )
        comparisons.append(tcmp)
        tracker = _safe(TrackerResult, self._primary(tcmp)) or TrackerResult(
            camera_id=camera.id,
            lat=camera.lat,
            lng=camera.lng,
            intersection=Intersection(roads=camera.roads),
        )
        log.append(
            f"Tracker Agent: mapped to {tracker.lat:.4f},{tracker.lng:.4f} "
            f"({', '.join(tracker.intersection.roads) or 'unknown roads'})"
        )

        # 3. Prediction
        pcmp = await self._dual_run(
            "prediction",
            prompts.PREDICTION_SYSTEM,
            prompts.prediction_user(
                tracker.intersection.model_dump(), vision.context
            ),
        )
        comparisons.append(pcmp)
        prediction = _safe(PredictionResult, self._primary(pcmp)) or PredictionResult(
            paths=[
                PathPrediction(direction="north", probability=0.5),
                PathPrediction(direction="east", probability=0.3),
                PathPrediction(direction="stop", probability=0.2),
            ]
        )
        log.append(
            "Prediction Agent: "
            + ", ".join(
                f"{p.direction} {int(p.probability * 100)}%" for p in prediction.paths
            )
        )

        # 4. Risk
        rcmp = await self._dual_run(
            "risk",
            prompts.RISK_SYSTEM,
            prompts.risk_user(
                [p.model_dump() for p in prediction.paths], incidents
            ),
        )
        comparisons.append(rcmp)
        risk = _safe(RiskResult, self._primary(rcmp)) or RiskResult(
            path_risks=[
                PathRisk(direction=p.direction, risk_score=0.4, reason="baseline")
                for p in prediction.paths
            ]
        )
        if risk.path_risks:
            worst = max(risk.path_risks, key=lambda r: r.risk_score)
            log.append(
                f"Risk Agent: highest risk {worst.direction} "
                f"({int(worst.risk_score * 100)}%) — {worst.reason}"
            )

        return WatchResponse(
            camera_id=camera.id,
            mode=req.mode,
            vision=vision,
            tracker=tracker,
            prediction=prediction,
            risk=risk,
            comparisons=comparisons,
            log=log,
        )


def _safe(model_cls, data: Optional[dict]):
    """Validate dict into a pydantic model, swallowing schema mismatches."""
    if not data:
        return None
    try:
        return model_cls.model_validate(data)
    except Exception:  # noqa: BLE001
        return None
