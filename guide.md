# TheWatcher — Complete Guide

> Multimodal, multi-agent safety & tracking copilot for NYC.
> Pick a camera → say what to watch → four Gemma-4 agents identify it, map it,
> predict where it goes, and score the risk — overlaid live on an NYC map.
> **Every agent runs on both Gemma (Cerebras) and Gemini, side by side.**

This single file is the source of truth: architecture, setup, how the
Gemma-vs-Gemini comparison works, current live-test status, the demo script,
and what's still needed.

---

## 1. Status at a glance

| Piece | State |
|---|---|
| Backend (FastAPI) | ✅ builds + boots, verified live |
| Gemma agents (Vision/Tracker/Prediction/Risk) | ✅ all 4 run **live** on `gemma-4-31b` |
| Gemini agents | ✅ all 4 run **live** on `gemini-2.5-flash` |
| Side-by-side comparison | ✅ **fully live** — both models, real metrics |
| Risk agent crash data | ✅ **live** NYC Open Data (Socrata) crash history |
| Frontend (React/Vite) | ✅ `npm run build` passes |
| Map tiles | ✅ **Geoapify** (osm-bright), OSM fallback |
| NYC cameras | ⏳ 5 bundled samples; live 511NY when that key arrives (emailed) |

**Verified full dual-model run** (both keys live):

```
                 GEMMA (gemma-4-31b)        GEMINI (gemini-2.5-flash)
[vision    ]  ok  871ms  520 tok  json✓   |  ok  8250ms  1924 tok  json✓
[tracker   ]  ok  664ms  304 tok  json✓   |  ok  5167ms  1203 tok  json✓
[prediction]  ok  605ms  224 tok  json✓   |  ok  3638ms   855 tok  json✓
[risk      ]  ok  790ms  311 tok  json✓   |  ok  5680ms  1302 tok  json✓
```

**Headline finding:** on identical prompts, **Gemma on Cerebras is ~6–10× faster
and uses ~4× fewer tokens** than Gemini 2.5-flash (which spends tokens on
"thinking"), while both produce valid JSON. That's the demo's money shot.

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
            └── ComparisonView.tsx   ★ Gemma vs Gemini scoreboard
```

### Request flow

```
Browser → /api/watch {camera_id, object_description, mode}
        → Orchestrator
             ├─ Vision     ┐
             ├─ Tracker    │ each step: Gemma + Gemini run CONCURRENTLY
             ├─ Prediction │ (asyncio.gather) → metrics captured
             └─ Risk       ┘ → "primary" result (Gemma preferred) feeds next
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

## 4. The Gemma vs Gemini comparison ★

This is the headline feature you asked for. The **"Gemma vs Gemini"** tab
(right panel) shows, for each agent, a side-by-side cell:

| Column | Gemma (Cerebras) | Gemini (Google) |
|---|---|---|
| Latency | per-call ms | per-call ms |
| Tokens | prompt / completion / total | prompt / completion / total |
| Output | parsed JSON (or raw fallback) | parsed JSON (or raw fallback) |
| Valid JSON? | ✓ / ✗ badge | ✓ / ✗ badge |
| Status | ok / error / mock | ok / error / mock |

A **scoreboard** at the top tallies a per-agent winner.

**How "winner" is decided** (`scoreRun` in
`frontend/src/components/ComparisonView.tsx`): the model that returned **valid
JSON the fastest** wins that agent. It's automatic and demo-friendly. To judge
by *output quality* instead, change that one function (e.g. add a rubric, or
have a judge model score both outputs).

**Why this design is fair:** both providers get the *identical* system+user
prompt (from `agents/prompts.py`) and the same image, run concurrently, and are
parsed by the same extractor. The only variable is the model.

**Current state:** ✅ both columns are live (`gemma-4-31b` vs `gemini-2.5-flash`).

### What a comparison typically reveals (talking points)

- **Speed:** Cerebras is built for very high tokens/sec — expect Gemma latencies
  to be low and consistent (we saw ~460–630 ms/agent). Great live-demo story.
- **Structure adherence:** both are prompted for strict JSON; the badge shows
  who actually complied.
- **Cost/efficiency:** token counts are shown per call for a like-for-like read.

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
5. Flip to **Gemma vs Gemini** tab → scoreboard + per-agent latency/tokens/JSON.
6. (If factory/hospital images added) flip tabs → HALT / ALERT overlay.
7. Tagline: *"TheWatcher — multimodal safety copilot for cities, factories, and
   care, powered by Cerebras + Gemma 4."*

---

## 7. What's needed from you

| # | Item | Effect | Status |
|---|---|---|---|
| 1 | `CEREBRAS_API_KEY` | live Gemma agents | ✅ done & verified |
| 2 | `GEMINI_API_KEY` | makes the comparison live | ✅ done & verified |
| 3 | `SOCRATA_APP_TOKEN` | real NYC crash data in Risk agent | ✅ done & verified |
| 4 | `VITE_GEOAPIFY_KEY` | nicer map tiles | ✅ done |
| 5 | `NY511_API_KEY` | real NYC cameras + live alerts | ⏳ pending (emailed) |
| 6 | 1–2 real traffic-cam JPEGs | convincing vision demo (samples are drawn) | ⏳ optional |
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
| Vision agent 400 error | image must be raster (PNG/JPEG), not SVG — samples are now PNG |
| Gemini column says "mock" | add `GEMINI_API_KEY` to `backend/.env`, restart |
| Only 5 cameras | no 511NY key → sample data; add `NY511_API_KEY` |
| Map tiles blank | offline; OSM tiles need internet |
| Wrong Gemma model | set `CEREBRAS_MODEL` in `.env` (yours: `gemma-4-31b`) |
| VS Code "package not installed" hint | select the `backend/.venv` interpreter |
