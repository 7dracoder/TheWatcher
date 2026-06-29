import type { AgentComparison, ModelRun } from "../types";

const AGENT_TITLES: Record<string, string> = {
  vision: "👁️ Vision Inspector",
  tracker: "📍 Tracker",
  prediction: "🧭 Prediction Planner",
  risk: "⚠️ Risk Assessor",
};

function Metric({ run }: { run: ModelRun | null }) {
  if (!run) return <span className="muted">—</span>;
  if (!run.ok) return <span className="badge badge-err">error</span>;
  return (
    <span className="metrics">
      <span className="badge badge-ok">{run.latency_ms} ms</span>
      {run.total_tokens != null && (
        <span className="badge">{run.total_tokens} tok</span>
      )}
      {run.parsed ? (
        <span className="badge badge-ok">valid JSON</span>
      ) : (
        <span className="badge badge-warn">unparsed</span>
      )}
    </span>
  );
}

export default function AnalysisView({
  comparisons,
}: {
  comparisons: AgentComparison[];
}) {
  if (!comparisons.length)
    return (
      <div className="panel-empty">
        Run a watch to see the Gemma analysis per agent.
      </div>
    );

  const runs = comparisons.map((c) => c.gemma).filter(Boolean) as ModelRun[];
  const totalMs = runs.reduce((s, r) => s + (r.latency_ms || 0), 0);
  const totalTok = runs.reduce((s, r) => s + (r.total_tokens || 0), 0);
  const okCount = runs.filter((r) => r.ok && r.parsed).length;

  return (
    <div className="comparison">
      <div className="scoreboard">
        <div className="score lead">
          <div className="score-name">Total latency</div>
          <div className="score-num">{totalMs}<span className="unit">ms</span></div>
        </div>
        <div className="score">
          <div className="score-name">Total tokens</div>
          <div className="score-num">{totalTok}</div>
        </div>
        <div className="score">
          <div className="score-name">Valid JSON</div>
          <div className="score-num">
            {okCount}<span className="unit">/{comparisons.length}</span>
          </div>
        </div>
      </div>
      <p className="scoreboard-note">
        Gemma <code>gemma-4-31b</code> on Cerebras — per-agent reasoning analysis.
      </p>

      {comparisons.map((c) => {
        const run = c.gemma;
        return (
          <div className="cmp-row" key={c.agent}>
            <div className="cmp-agent-head">
              <span className="cmp-agent">
                {AGENT_TITLES[c.agent] ?? c.agent}
              </span>
              <Metric run={run} />
            </div>
            <div className="cmp-cell cmp-winner">
              {run?.error && <div className="cmp-error">{run.error}</div>}
              <pre className="cmp-json">
                {run?.parsed
                  ? JSON.stringify(run.parsed, null, 2)
                  : run?.raw_text
                    ? run.raw_text.slice(0, 500)
                    : "(no output)"}
              </pre>
            </div>
          </div>
        );
      })}
    </div>
  );
}
