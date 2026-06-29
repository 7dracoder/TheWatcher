import type { Camera, WatchResponse } from "../types";

export default function SnapshotPanel({
  camera,
  result,
}: {
  camera: Camera | null;
  result: WatchResponse | null;
}) {
  if (!camera)
    return <div className="panel-empty">Select a camera on the map.</div>;

  const box = result?.vision?.bounding_box;
  const img = camera.sample_image ?? camera.image_url ?? "";

  // Vision models return normalized 0-1000 coordinates (resolution-independent).
  const clampPct = (v: number) => Math.max(0, Math.min((v / 1000) * 100, 100));
  const pct = box && {
    left: clampPct(box.x),
    top: clampPct(box.y),
    width: clampPct(box.width),
    height: clampPct(box.height),
  };

  return (
    <div className="snapshot">
      <div className="snapshot-frame">
        {img ? (
          <img src={img} alt={camera.name} />
        ) : (
          <div className="panel-empty">no snapshot</div>
        )}
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
