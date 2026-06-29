# TheWatcher — Multimodal Safety & Tracking Copilot for NYC

A web-based, multi-agent, multimodal safety copilot. Pick an NYC traffic
camera, tell TheWatcher *what* to watch, and four Gemma-4 agents (Vision →
Tracker → Prediction → Risk) identify the object, map the camera, predict
where it goes next, and score the risk along each path — all overlaid on a
live NYC map.

**Every agent step runs on _both_ Gemma (via Cerebras) and Gemini at the same
time**, so you get a live side-by-side scoreboard of which model is doing the
better job. See [Gemma vs Gemini](#gemma-vs-gemini).

---

## Architecture

```
frontend/  React + Vite + TypeScript  (map, snapshot, control room, comparison)
   │  /api proxy → 
backend/   FastAPI (Python)
   ├─ providers/   Gemma (Cerebras) + Gemini  — same interface, dual-run
   ├─ agents/      Vision · Tracker · Prediction · Risk + orchestrator
   ├─ services/    511NY cameras + alerts (sample fallback)
   └─ data/        bundled sample NYC cameras
```

The orchestrator fires both providers **concurrently** for each agent,
captures latency + token usage + whether the JSON parsed, and feeds the
"primary" result (Gemma preferred) into the next agent.

---

## Quick start

> Only `CEREBRAS_API_KEY` is required. Without the others the app still runs:
> Gemini shows a "mock" column, 511NY uses bundled sample cameras, maps use
> free OpenStreetMap tiles.

### 1. Configure

```bash
cp .env.example .env        # then edit .env and add CEREBRAS_API_KEY
```

### 2. Backend (terminal 1)

```bash
cd backend
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# macOS/Linux:         source .venv/bin/activate
pip install -r requirements.txt
python -m app.main          # serves http://127.0.0.1:8000
```

Check it: open http://127.0.0.1:8000/api/health

### 3. Frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev                 # serves http://localhost:5173
```

Open **http://localhost:5173**, pick a camera, type what to watch, hit **Run**.

---

## Gemma vs Gemini

The **"Gemma vs Gemini"** tab in the right panel shows, for each of the four
agents:

| | Gemma (Cerebras) | Gemini |
|---|---|---|
| **Latency** | per-call ms | per-call ms |
| **Tokens** | prompt/completion/total | prompt/completion/total |
| **Output** | parsed JSON (or raw) | parsed JSON (or raw) |
| **Valid JSON?** | ✓ / ✗ | ✓ / ✗ |

A simple **scoreboard** tallies a per-agent "winner" = whichever model
returned valid JSON the fastest. This is a fair, automatic, demo-friendly
comparison — and the heuristic lives in
[`frontend/src/components/ComparisonView.tsx`](frontend/src/components/ComparisonView.tsx)
(`scoreRun`) if you want to weight it differently (e.g. by output quality).

> Until you add `GEMINI_API_KEY`, the Gemini column renders as `mock (no key)`
> so the layout and demo flow still work. Add the key and the column goes live
> instantly — no code change.

---

## Modes

- **NYC Traffic** — real flow (sample cameras until a 511NY key is added).
- **Factory (Sim)** / **Hospital (Sim)** — same pipeline on simulated feeds;
  intended for uploading a dashboard screenshot (Vision + Risk detect a
  failing robot arm / critical vital and suggest HALT / ALERT).

---

## What I need from you

To move from "runs with sample data" to "full live demo", in priority order:

1. **`CEREBRAS_API_KEY`** *(required)* — the only thing needed to run the real
   Gemma agents. Also confirm the **exact model id** you have access to
   (`.env` defaults to `gemma-4-31b`; set `CEREBRAS_MODEL` if it differs —
   e.g. the hackathon may expose a specific Gemma vision-capable id).
2. **`GEMINI_API_KEY`** — to make the side-by-side comparison live instead of
   mocked. (Default model `gemini-2.0-flash`; change via `GEMINI_MODEL`.)
3. **`NY511_API_KEY`** — to load real NYC cameras + live alerts instead of the
   5 bundled sample cameras. Free; register at 511ny.org.
4. **Real camera snapshots** *(optional but high-impact for the demo)* — the
   bundled snapshots are placeholder SVGs. For a convincing vision demo, drop
   1–2 real traffic-cam JPEGs in `backend/app/data/` and I'll wire them to the
   sample cameras (or we proxy them live once the 511NY key is in).
5. **Factory/Hospital sample images** — if you want those tabs populated,
   share 1 dashboard screenshot each.
6. **Decisions to confirm:**
   - Deploy target? (local-only for the hackathon video, or hosted?)
   - Do you want me to wire NYC Open Data (crash history / roadwork via
     Socrata) into the Risk agent? Needs `SOCRATA_APP_TOKEN`.

Once you paste the keys into `.env` (or send them), everything lights up with
no further code changes.

---

## Notes / ethics

- No face recognition or PII — tracks generic objects only.
- Snapshot-based, not continuous surveillance.
- Factory/Hospital are clearly simulated.
