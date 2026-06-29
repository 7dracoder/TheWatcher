import type { AgentComparison, ModelRun } from "../types";

const AGENT_TITLES: Record<string, string> = {
  vision: "👁️ Vision Inspector",
  tracker: "📍 Tracker",
  prediction: "🧭 Prediction Planner",
  risk: "⚠️ Risk Assessor",
};

function scoreRun(r: ModelRun | null): number {
  // Simple win heuristic: parsed valid JSON + lower latency.
  if (!r || !r.ok || !r.parsed) return -1;
  return 1000 - Math.min(r.latency_ms, 1000) / 10;
}

function Metric({ run }: { run: ModelRun | null }) {
  if (!run) return <span className="muted">—</span>;
  if (run.mocked)
    return <span className="badge badge-mock">mock (no key)</span>;
  if (!run.ok)
    return <span className="badge badge-err">error</span>;
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

function Cell({ run, winner }: { run: ModelRun | null; winner: boolean }) {
  return (
    <div className={`cmp-cell ${winner ? "cmp-winner" : ""}`}>
      <Metric run={run} />
      {run?.error && <div className="cmp-error">{run.error}</div>}
      <pre className="cmp-json">
        {run?.parsed
          ? JSON.stringify(run.parsed, null, 2)
          : run?.raw_text
            ? run.raw_text.slice(0, 400)
            : "(no output)"}
      </pre>
    </div>
  );
}

export default function ComparisonView({
  comparisons,
}: {
  comparisons: AgentComparison[];
}) {
  if (!comparisons.length)
    return (
      <div className="panel-empty">
        Run a watch to see Gemma vs Gemini side by side.
      </div>
    );

  // Aggregate scoreboard
  let gemmaWins = 0;
  let geminiWins = 0;
  for (const c of comparisons) {
    const g = scoreRun(c.gemma);
    const e = scoreRun(c.gemini);
    if (g > e) gemmaWins++;
    else if (e > g) geminiWins++;
  }

  return (
    <div className="comparison">
      <div className="scoreboard">
        <div className={`score ${gemmaWins >= geminiWins ? "lead" : ""}`}>
          <div className="score-name">Gemma (Cerebras)</div>
          <div className="score-num">{gemmaWins}</div>
        </div>
        <div className="score-vs">vs</div>
        <div className={`score ${geminiWins > gemmaWins ? "lead" : ""}`}>
          <div className="score-name">Gemini</div>
          <div className="score-num">{geminiWins}</div>
        </div>
      </div>
      <p className="scoreboard-note">
        Per-agent winner = produced valid JSON fastest. {gemmaWins + geminiWins}
        /{comparisons.length} agents had a clear winner.
      </p>

      {comparisons.map((c) => {
        const g = scoreRun(c.gemma);
        const e = scoreRun(c.gemini);
        return (
          <div className="cmp-row" key={c.agent}>
            <div className="cmp-agent">{AGENT_TITLES[c.agent] ?? c.agent}</div>
            <div className="cmp-grid">
              <div className="cmp-head">Gemma</div>
              <div className="cmp-head">Gemini</div>
              <Cell run={c.gemma} winner={g > e && g >= 0} />
              <Cell run={c.gemini} winner={e > g && e >= 0} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
