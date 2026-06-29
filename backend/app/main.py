"""TheWatcher FastAPI backend."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .agents.orchestrator import Orchestrator
from .config import get_settings
from .schemas import Camera, WatchRequest, WatchResponse
from .services.nyc_data import NYCDataService

settings = get_settings()
app = FastAPI(title="TheWatcher API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

nyc = NYCDataService()
orchestrator = Orchestrator()


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "providers": {
            "gemma": {"enabled": settings.gemma_enabled, "model": settings.cerebras_model},
            "gemini": {"enabled": settings.gemini_enabled, "model": settings.gemini_model},
        },
        "data": {
            "ny511_live": bool(settings.ny511_api_key),
        },
    }


@app.get("/api/cameras", response_model=list[Camera])
async def list_cameras() -> list[Camera]:
    return await nyc.cameras()


@app.get("/api/cameras/{camera_id}", response_model=Camera)
async def get_camera(camera_id: str) -> Camera:
    cam = await nyc.camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="camera not found")
    return cam


@app.post("/api/watch", response_model=WatchResponse)
async def watch(req: WatchRequest) -> WatchResponse:
    cam = await nyc.camera(req.camera_id)
    if not cam:
        # allow factory/hospital modes with no real camera
        if req.mode == "nyc":
            raise HTTPException(status_code=404, detail="camera not found")
        cam = Camera(id=req.camera_id, name=f"{req.mode} feed", lat=0.0, lng=0.0)
    incidents = await nyc.incidents_near(cam.lat, cam.lng)
    return await orchestrator.run(req, cam, incidents)


def run() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.watcher_host,
        port=settings.watcher_port,
        reload=True,
    )


if __name__ == "__main__":
    run()
