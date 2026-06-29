import { useEffect, useState } from "react";
import { getCameras, getHealth, watch } from "./api";
import type { Camera, Health, WatchResponse } from "./types";
import MapView from "./components/MapView";
import SnapshotPanel from "./components/SnapshotPanel";
import AgentChat from "./components/AgentChat";
import ComparisonView from "./components/ComparisonView";

type Mode = "nyc" | "factory" | "hospital";
type Tab = "control" | "compare";

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selected, setSelected] = useState<Camera | null>(null);
  const [description, setDescription] = useState("yellow taxi in the crosswalk");
  const [mode, setMode] = useState<Mode>("nyc");
  const [tab, setTab] = useState<Tab>("control");
  const [result, setResult] = useState<WatchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => {});
    getCameras()
      .then((cs) => {
        setCameras(cs);
        if (cs.length) setSelected(cs[0]);
      })
      .catch((e) => setError(String(e)));
  }, []);

  async function runWatch() {
    if (!selected) return;
    setLoading(true);
    setError(null);
    try {
      const res = await watch({
        camera_id: selected.id,
        object_description: description,
        mode,
      });
      setResult(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">◉</span> TheWatcher
          <span className="tagline">multimodal safety copilot · NYC</span>
        </div>
        <div className="providers">
          <ProviderPill
            label="Gemma"
            on={health?.providers.gemma.enabled}
            model={health?.providers.gemma.model}
          />
          <span className="pill">
            511NY: {health?.data.ny511_live ? "live" : "sample"}
          </span>
        </div>
      </header>

      <div className="modebar">
        {(["nyc", "factory", "hospital"] as Mode[]).map((m) => (
          <button
            key={m}
            className={mode === m ? "active" : ""}
            onClick={() => setMode(m)}
          >
            {m === "nyc" ? "NYC Traffic" : m === "factory" ? "Factory (Sim)" : "Hospital (Sim)"}
          </button>
        ))}
      </div>

      <main className="grid">
        <section className="col map-col">
          <MapView
            cameras={cameras}
            selected={selected}
            onSelect={setSelected}
            result={result}
          />
        </section>

        <section className="col mid-col">
          <SnapshotPanel camera={selected} result={result} />
          <div className="controls">
            <label>What should TheWatcher watch?</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
            <button className="run-btn" onClick={runWatch} disabled={loading || !selected}>
              {loading ? "Running agents…" : "▶ Run agents (Gemma)"}
            </button>
            {error && <div className="error-box">{error}</div>}
          </div>
        </section>

        <section className="col right-col">
          <div className="tabs">
            <button
              className={tab === "control" ? "active" : ""}
              onClick={() => setTab("control")}
            >
              Control Room
            </button>
            <button
              className={tab === "compare" ? "active" : ""}
              onClick={() => setTab("compare")}
            >
              Gemma Analysis
            </button>
          </div>
          <div className="tab-body">
            {tab === "control" ? (
              <AgentChat log={result?.log ?? []} />
            ) : (
              <ComparisonView comparisons={result?.comparisons ?? []} />
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

function ProviderPill({
  label,
  on,
  model,
}: {
  label: string;
  on?: boolean;
  model?: string;
}) {
  return (
    <span className={`pill ${on ? "pill-on" : "pill-off"}`} title={model}>
      {label}: {on ? "on" : "off"}
    </span>
  );
}
