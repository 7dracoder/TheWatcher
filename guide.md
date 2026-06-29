# TheWatcher — Complete Guide

> Multimodal, multi-agent safety & tracking copilot for NYC.
> Pick a camera → say what to watch → four Gemma-4 agents identify it, map it,
> predict where it goes, and score the risk — overlaid live on an NYC map.
> **Every agent runs on Gemma 4 (via Cerebras), with a per-agent analysis panel.**

This single file is the source of truth: architecture, setup, how the
Gemma analysis panel works, current live-test status, the demo script,
and what's still needed.

---

## 1. Status at a glance

| Piece | State |
|---|---|
| Backend (FastAPI) | ✅ builds + boots, verified live |
| Gemma agents (Vision/Tracker/Prediction/Risk) | ✅ all 4 run **live** on `gemma-4-31b` |
| Gemma Analysis panel | ✅ per-agent latency / tokens / JSON + reasoning |
| Gemini | ⏸️ disabled by choice — provider kept dormant, easy to re-enable |
| Risk agent crash data | ✅ **live** NYC Open Data (Socrata) crash history |
| Frontend (React/Vite) | ✅ `npm run build` passes |
| Map tiles | ✅ **Geoapify** (osm-bright), OSM fallback |
| NYC cameras | ✅ **955 live NYC DOT cameras** (no key) + live JPEG snapshots |

**Verified Gemma-only run** (live):

```
              GEMMA (gemma-4-31b)
[vision    ]  ok  823ms  579 tok  json✓
[tracker   ]  ok  462ms  359 tok  json✓
[prediction]  ok  377ms  226 tok  json✓
[risk      ]  ok  421ms  305 tok  json✓
```

**Gemma Analysis panel:** the right-hand tab shows, per agent, Gemma's latency,
token usage, JSON-validity, and full reasoning output — plus totals across the
pipeline. (We earlier ran Gemini side-by-side; per your call it's disabled and
the panel is now a clean Gemma analysis. The Gemini provider is still in the
codebase, dormant — re-enable in `orchestrator._run_agent`.)

**Live Risk data:** the Risk agent now reasons over real NYC crash history —
e.g. the 7th Ave @ W 34th St corner returns *"6,263 historical crashes within
~300m (1,310 injured, 4 killed)"* from NYC Open Data.

Cerebras key has access to: `gpt-oss-120b`, `zai-glm-4.7`, **`gemma-4-31b`**.

---

## 2. Architecture

```
TheWatcher/
├── guide.md            ← you are here
├── README.md           short version of this guide
├── .env.example        template (copy to backend/.env)
│
├── backend/            Python · FastAPI
│   ├── requirements.txt
│   └── app/
│       ├── main.py            FastAPI app + routes
│       ├── config.py          env settings (pydantic-settings)
│       ├── schemas.py         all request/response/agent models
│       ├── providers/
│       │   ├── base.py            LLMProvider interface + JSON extraction
│       │   ├── cerebras_provider.py   Gemma via Cerebras (OpenAI-compatible)
│       │   └── gemini_provider.py     Gemini via Google REST (mock fallback)
│       ├── agents/
│       │   ├── prompts.py         system+user prompt per agent (strict JSON)
│       │   └── orchestrator.py    runs each agent on BOTH models, merges
│       ├── services/
│       │   └── nyc_data.py        511NY cameras+alerts; sample fallback; PNG snapshots
│       └── data/
│           └── sample_cameras.json   5 NYC cameras
│
└── frontend/           React + Vite + TypeScript
    ├── package.json · vite.config.ts · tsconfig.json · index.html
    └── src/
        ├── App.tsx            layout, mode tabs, run button
        ├── api.ts · types.ts  typed client + shared types
        ├── styles.css         dark "control room" theme
        └── components/
            ├── MapView.tsx          Leaflet map, camera markers, risk-colored arcs
            ├── SnapshotPanel.tsx    snapshot + vision bounding box
            ├── AgentChat.tsx        control-room log
            └── ComparisonView.tsx   ★ Gemma analysis panel (per-agent metrics)
```

### Request flow

```
Browser → /api/watch {camera_id, object_description, mode}
        → Orchestrator
             ├─ Vision     ┐
             ├─ Tracker    │ each step runs on Gemma →
             ├─ Prediction │ metrics captured (latency / tokens / JSON)
             └─ Risk       ┘ → parsed result feeds the next agent
        → WatchResponse { vision, tracker, prediction, risk, comparisons[], log[] }
```

Every stage degrades gracefully: if a model errors or returns unparseable
output, a sensible fallback keeps the pipeline running (see `_safe` /
fallbacks in `orchestrator.py`).

---

## 3. Setup & run

> Only `CEREBRAS_API_KEY` is required. It's already in `backend/.env`.
> Deps are already installed locally from the live test, so on this machine you
> can skip the `pip install` / `npm install` lines.

### Backend (terminal 1)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m app.main                  # → http://127.0.0.1:8000
```

Health check → http://127.0.0.1:8000/api/health

### Frontend (terminal 2)

```powershell
cd frontend
npm install
npm run dev                         # → http://localhost:5173
```

Open **http://localhost:5173**.

### API reference

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/health` | provider/data status |
| GET | `/api/cameras` | list cameras (live 511NY or samples) |
| GET | `/api/cameras/{id}` | one camera |
| POST | `/api/watch` | run the 4-agent dual-model pipeline |

---

## 4. The Gemma Analysis panel ★

The **"Gemma Analysis"** tab (right panel) shows, for each agent, Gemma's run:

| Field | Shown |
|---|---|
| Latency | per-call ms |
| Tokens | total tokens used |
| Output | parsed JSON (or raw fallback) |
| Valid JSON? | ✓ / ✗ badge |
| Reasoning | the agent's structured output / explanation |

A header strip tallies pipeline **totals**: total latency, total tokens, and
how many of the 4 agents returned valid JSON.

**Why it's a clean story:** every agent gets a strict-JSON prompt (from
`agents/prompts.py`) and the same live image, and is parsed by the same
extractor — so the panel is an honest readout of how Gemma performs each step.

> We originally ran Gemini side-by-side here. Per the current design decision,
> Gemini is **disabled** and the panel is a Gemma-only analysis. The Gemini
> provider and adapter remain in the codebase (dormant); re-enable by adding a
> `self.gemini.run(...)` call in `orchestrator._run_agent` and rendering the
> `gemini` field again in `ComparisonView.tsx`.

### Talking points

- **Speed:** Cerebras runs Gemma at very high tokens/sec — agents land in
  ~380–820 ms each, so the whole 4-agent pipeline finishes in ~2 s. Great live
  demo feel.
- **Structure adherence:** every agent is prompted for strict JSON; the badge
  shows compliance (4/4 valid in testing).
- **Cost/efficiency:** per-agent token counts are shown for a transparent read.

---

## 5. Modes

- **NYC Traffic** — main flow. Sample cameras until a 511NY key is added.
- **Factory (Sim)** / **Hospital (Sim)** — same pipeline, simulated feeds.
  Intended use: upload a dashboard screenshot; Vision + Risk flag a failing
  robot arm / critical vital and suggest **HALT** / **ALERT**. (Wire-up is
  ready; needs sample images — see §7.)

---

## 6. Demo script (60s)

1. Map of NYC with camera markers; pick **7th Ave @ W 34th St**.
2. Snapshot appears; type **"yellow taxi heading north"**; hit **Run agents**.
3. **Control Room** tab streams the 4 agent log lines.
4. Map shows the object marker + probability arcs, colored green→red by risk.
5. Flip to **Gemma Analysis** tab → per-agent latency/tokens/JSON + reasoning, with pipeline totals.
6. (If factory/hospital images added) flip tabs → HALT / ALERT overlay.
7. Tagline: *"TheWatcher — multimodal safety copilot for cities, factories, and
   care, powered by Cerebras + Gemma 4."*

---

## 7. What's needed from you

| # | Item | Effect | Status |
|---|---|---|---|
| 1 | `CEREBRAS_API_KEY` | live Gemma agents | ✅ done & verified |
| 2 | `GEMINI_API_KEY` | only needed if re-enabling the comparison | ⏸️ not used now |
| 3 | `SOCRATA_APP_TOKEN` | real NYC crash data in Risk agent | ✅ done & verified |
| 4 | `VITE_GEOAPIFY_KEY` | nicer map tiles | ✅ done |
| 5 | NYC DOT cameras | 955 live cameras + snapshots, no key | ✅ done |
| 6 | `NY511_API_KEY` | adds live *traffic alerts* (cameras already covered) | ⏳ optional |
| 7 | Factory + Hospital screenshots | populate the Sim tabs | ⏳ optional |

**Decisions to confirm:**
- Deploy target — local for the hackathon video, or hosted?
- Make the initial git commit now? (nothing is committed yet; `.env` is
  gitignored and will NOT be committed.)

Add any key by editing `backend/.env`, then restart the backend.

---

## 8. Security & ethics

- ⚠️ **The Cerebras key you pasted in chat is exposed — rotate it after the
  hackathon.** It lives only in `backend/.env` (gitignored).
- No face recognition / no PII — tracks generic objects (cars, pedestrians).
- Snapshot-based, not continuous surveillance.
- Factory/Hospital are clearly simulated.

---

## 9. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Vision agent 400 error | image must be raster (PNG/JPEG), not SVG — live snapshots are JPEG |
| Only 5 cameras | NYC DOT fetch failed → using samples; retries next call (transient) |
| Markers laggy | 955 cameras render at once — ask to add clustering |
| Map tiles blank | offline; OSM tiles need internet |
| Wrong Gemma model | set `CEREBRAS_MODEL` in `.env` (yours: `gemma-4-31b`) |
| VS Code "package not installed" hint | select the `backend/.venv` interpreter |
