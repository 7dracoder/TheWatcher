import { useEffect, useState } from "react";
import type { Camera, WatchResponse } from "../types";

export default function SnapshotPanel({
  camera,
  result,
}: {
  camera: Camera | null;
  result: WatchResponse | null;
}) {
  // Tick to cache-bust the live JPEG (NYC DOT updates every ~2s).
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!camera || camera.sample_image) return;
    const id = setInterval(() => setTick((t) => t + 1), 3000);
    return () => clearInterval(id);
  }, [camera]);

  if (!camera)
    return <div className="panel-empty">Select a camera on the map.</div>;

  const box = result?.vision?.bounding_box;
  // Vision models return normalized 0-1000 coordinates (resolution-independent).
  const clampPct = (v: number) => Math.max(0, Math.min((v / 1000) * 100, 100));
  const pct = box && {
    left: clampPct(box.x),
    top: clampPct(box.y),
    width: clampPct(box.width),
    height: clampPct(box.height),
  };

  // Sample cameras carry an inline data-URI; live NYC DOT cameras stream via the
  // backend proxy (avoids CORS and lets us cache-bust for a live feel).
  const isLive = !camera.sample_image;
  const img = camera.sample_image
    ? camera.sample_image
    : `/api/cameras/${camera.id}/snapshot?t=${tick}`;

  return (
    <div className="snapshot">
      <div className="snapshot-frame">
        {img ? (
          <img src={img} alt={camera.name} />
        ) : (
          <div className="panel-empty">no snapshot</div>
        )}
        {isLive && <span className="live-badge">● LIVE</span>}
        {pct && (
          <div
            className="bbox"
            style={{
              left: `${pct.left}%`,
              top: `${pct.top}%`,
              width: `${pct.width}%`,
              height: `${pct.height}%`,
            }}
          >
            <span>{result?.vision?.object_label}</span>
          </div>
        )}
      </div>
      <div className="snapshot-meta">
        <strong>{camera.name}</strong>
        <span className="muted">{camera.roads.join(" · ")}</span>
      </div>
    </div>
  );
}
