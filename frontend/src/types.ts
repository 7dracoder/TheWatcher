export interface Camera {
  id: string;
  name: string;
  lat: number;
  lng: number;
  roads: string[];
  image_url: string | null;
  sample_image: string | null;
}

export interface ModelRun {
  provider: "gemma" | "gemini";
  model: string;
  ok: boolean;
  mocked: boolean;
  latency_ms: number;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  raw_text: string;
  parsed: Record<string, unknown> | null;
  error: string | null;
}

export interface AgentComparison {
  agent: string;
  gemma: ModelRun | null;
  gemini: ModelRun | null;
}

export interface PathPrediction {
  direction: string;
  probability: number;
}

export interface PathRisk {
  direction: string;
  risk_score: number;
  reason: string;
}

export interface WatchResponse {
  camera_id: string;
  mode: string;
  vision: {
    object_label: string;
    bounding_box: { x: number; y: number; width: number; height: number } | null;
    context: string;
  } | null;
  tracker: {
    camera_id: string;
    lat: number;
    lng: number;
    intersection: { roads: string[]; lanes: string[] };
  } | null;
  prediction: { paths: PathPrediction[] } | null;
  risk: { path_risks: PathRisk[] } | null;
  comparisons: AgentComparison[];
  log: string[];
}

export interface Health {
  status: string;
  providers: {
    gemma: { enabled: boolean; model: string };
    gemini: { enabled: boolean; model: string };
  };
  data: { ny511_live: boolean };
}
