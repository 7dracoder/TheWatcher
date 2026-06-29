"""Runs the 4-agent pipeline on Gemma, capturing per-agent metrics.

Each agent step runs on Gemma (via Cerebras); we capture latency / tokens /
parsed JSON and feed the parsed result into the next agent. The per-agent
runs are returned for the Gemma analysis panel. (The Gemini provider is kept
in place but dormant — see _run_agent to re-enable a side-by-side comparison.)
"""
from __future__ import annotations

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

    async def _run_agent(
        self,
        agent: str,
        system: str,
        user: str,
        image_data_uri: Optional[str] = None,
    ) -> AgentComparison:
        # Gemma-only analysis. (Gemini provider kept dormant — to re-enable a
        # side-by-side comparison, also run self.gemini.run(...) here and set
        # gemini=that result.)
        gemma_run = await self.gemma.run(
            system=system, user=user, image_data_uri=image_data_uri
        )
        return AgentComparison(agent=agent, gemma=gemma_run, gemini=None)

    @staticmethod
    def _primary(cmp: AgentComparison) -> Optional[dict[str, Any]]:
        """Use Gemma's parsed output."""
        run = cmp.gemma
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
        vcmp = await self._run_agent(
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
        tcmp = await self._run_agent(
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
        pcmp = await self._run_agent(
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
        rcmp = await self._run_agent(
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
