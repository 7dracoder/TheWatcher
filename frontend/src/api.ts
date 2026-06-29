import type { Camera, Health, WatchResponse } from "./types";

const BASE = "/api";

export async function getHealth(): Promise<Health> {
  const r = await fetch(`${BASE}/health`);
  return r.json();
}

export async function getCameras(): Promise<Camera[]> {
  const r = await fetch(`${BASE}/cameras`);
  return r.json();
}

export interface WatchPayload {
  camera_id: string;
  object_description: string;
  mode: "nyc" | "factory" | "hospital";
  image_data_uri?: string;
}

export async function watch(payload: WatchPayload): Promise<WatchResponse> {
  const r = await fetch(`${BASE}/watch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`watch failed: ${r.status}`);
  return r.json();
}
