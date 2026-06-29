"""System + user prompt templates for each agent.

Every agent is instructed to return STRICT JSON so both Gemma and Gemini
outputs can be parsed and compared on equal footing.
"""
from __future__ import annotations

from ..schemas import Camera

JSON_RULE = (
    "Respond with ONLY a single valid JSON object. No prose, no markdown, "
    "no code fences. Use double quotes for all keys and string values."
)

# ---- Vision ------------------------------------------------------------
VISION_SYSTEM = (
    "You are the Vision Inspector agent in TheWatcher, a city-safety copilot. "
    "You analyze a camera snapshot and locate the object the user describes. "
    "Estimate a bounding box in pixel coordinates relative to the image "
    "(assume a 640x480 frame if you cannot tell). " + JSON_RULE
)


def vision_user(description: str, mode: str) -> str:
    return (
        f"Scene type: {mode}. The user wants to watch: \"{description}\".\n"
        "Find that object/region in the image and return JSON exactly shaped as:\n"
        '{"object_label": str, "bounding_box": {"x": int, "y": int, '
        '"width": int, "height": int}, "context": str}\n'
        "IMPORTANT: bounding_box uses NORMALIZED coordinates on a 0-1000 scale "
        "(x,y = top-left corner; 0,0 = top-left of image, 1000,1000 = "
        "bottom-right), so it is resolution-independent.\n"
        "context: one short sentence on position, direction or status."
    )


# ---- Tracker -----------------------------------------------------------
TRACKER_SYSTEM = (
    "You are the Tracker agent. Given camera metadata and the vision context, "
    "resolve the camera to a map location and infer the intersection topology "
    "(connected roads and allowed travel directions). " + JSON_RULE
)


def tracker_user(camera: Camera, vision_context: str) -> str:
    return (
        f"Camera id={camera.id}, name=\"{camera.name}\", "
        f"lat={camera.lat}, lng={camera.lng}, roads={camera.roads}.\n"
        f"Vision context: \"{vision_context}\".\n"
        "Return JSON exactly shaped as:\n"
        '{"camera_id": str, "lat": number, "lng": number, '
        '"intersection": {"roads": [str], "lanes": [str]}}\n'
        "lanes are compass directions a tracked object could travel, e.g. "
        '["northbound","southbound","eastbound","westbound"].'
    )


# ---- Prediction --------------------------------------------------------
PREDICTION_SYSTEM = (
    "You are the Prediction Planner agent. Given intersection topology and the "
    "tracked object's context, estimate plausible next moves and assign "
    "probabilities that sum to ~1.0. " + JSON_RULE
)


def prediction_user(intersection: dict, vision_context: str) -> str:
    return (
        f"Intersection: {intersection}.\n"
        f"Object context: \"{vision_context}\".\n"
        "Return JSON exactly shaped as:\n"
        '{"paths": [{"direction": str, "probability": number}]}\n'
        'direction is one of north/south/east/west/stop. Include 2-4 paths.'
    )


# ---- Risk --------------------------------------------------------------
RISK_SYSTEM = (
    "You are the Risk Assessor agent. Given predicted paths and any known "
    "incidents/roadwork, score the risk (0..1) of each path and explain why. "
    + JSON_RULE
)


def risk_user(paths: list[dict], incidents: list[str]) -> str:
    inc = "; ".join(incidents) if incidents else "no active incidents reported"
    return (
        f"Predicted paths: {paths}.\n"
        f"Known incidents/alerts near the camera: {inc}.\n"
        "Return JSON exactly shaped as:\n"
        '{"path_risks": [{"direction": str, "risk_score": number, "reason": str}]}'
    )
