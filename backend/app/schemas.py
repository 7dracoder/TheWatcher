"""Pydantic schemas shared across agents and API routes."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---- Agent I/O ---------------------------------------------------------
class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class VisionResult(BaseModel):
    object_label: str
    bounding_box: Optional[BoundingBox] = None
    context: str = ""


class Intersection(BaseModel):
    roads: list[str] = Field(default_factory=list)
    lanes: list[str] = Field(default_factory=list)


class TrackerResult(BaseModel):
    camera_id: str
    lat: float
    lng: float
    intersection: Intersection = Field(default_factory=Intersection)


class PathPrediction(BaseModel):
    direction: str
    probability: float


class PredictionResult(BaseModel):
    paths: list[PathPrediction] = Field(default_factory=list)


class PathRisk(BaseModel):
    direction: str
    risk_score: float
    reason: str = ""


class RiskResult(BaseModel):
    path_risks: list[PathRisk] = Field(default_factory=list)


# ---- Provider run metadata (for the Gemma-vs-Gemini comparison) --------
class ModelRun(BaseModel):
    provider: Literal["gemma", "gemini"]
    model: str
    ok: bool
    mocked: bool = False
    latency_ms: int = 0
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    raw_text: str = ""
    parsed: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class AgentComparison(BaseModel):
    """One agent step run on both providers, side by side."""
    agent: str
    gemma: Optional[ModelRun] = None
    gemini: Optional[ModelRun] = None


# ---- API request / response -------------------------------------------
class WatchRequest(BaseModel):
    camera_id: str
    object_description: str
    bounding_box: Optional[BoundingBox] = None
    # Optional inline image (data URI) — overrides the camera's sample snapshot.
    image_data_uri: Optional[str] = None
    mode: Literal["nyc", "factory", "hospital"] = "nyc"


class WatchResponse(BaseModel):
    camera_id: str
    mode: str
    # The "primary" merged result (Gemma preferred, Gemini fallback).
    vision: Optional[VisionResult] = None
    tracker: Optional[TrackerResult] = None
    prediction: Optional[PredictionResult] = None
    risk: Optional[RiskResult] = None
    # Per-agent dual-run comparison for the UI.
    comparisons: list[AgentComparison] = Field(default_factory=list)
    # Human-readable control-room log lines.
    log: list[str] = Field(default_factory=list)


class Camera(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    roads: list[str] = Field(default_factory=list)
    image_url: Optional[str] = None
    # bundled sample snapshot served by the backend
    sample_image: Optional[str] = None
