# AEGIS Laptop Demo Runbook

This is the no-surprises path for a judged single-laptop demo. It uses committed fixture data by default, so it does not depend on FIRMS, NOAA, Gemma, or MongoDB being online.

## One-Time Setup

```bash
python3 -m venv venv
source venv/bin/activate
make install
cd frontend && npm ci && cd ..
```

Optional real/demo polish keys go in untracked `.env` files only:

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

Fill these when available:

- `AGENTVERSE_API_KEY` and `AGENT_SEED` for Fetch.ai prize rehearsal.
- `GOOGLE_AI_API_KEY` for real Gemma parsing.
- `VITE_CESIUM_ION_TOKEN` for satellite imagery/terrain polish.
- `MONGO_URI` or `MONGODB_URI` for persistent backend writes.
- `FIRMS_MAP_KEY` only if refreshing real fire data.

## Pre-Demo Checks

```bash
make demo-smoke
make frontend-build
```

`make demo-smoke` runs Python lint/tests and fixture replay validation. If the backend is already running on `127.0.0.1:8000`, it also verifies `/health`, `/route`, `/hazard`, `/field-report`, and `/state`.

## Terminal Layout

Terminal 1: backend API on port 8000.

```bash
cd backend
../venv/bin/python -m uvicorn main:app --port 8000
```

Terminal 2: frontend on port 5173.

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/`. The top bar should show `CONNECTED`.

Terminal 3: demo actions.

```bash
make backend-smoke
make demo-replay
BACKEND_URL=http://127.0.0.1:8000 venv/bin/python -c "import asyncio; from types import SimpleNamespace; from agents.field_unit_agent import _handle_report_text; logger=SimpleNamespace(info=print,error=print); ctx=SimpleNamespace(logger=logger); print(asyncio.run(_handle_report_text(ctx, 'Road blocked by debris near 34.19, -118.11')))"
curl -s http://127.0.0.1:8000/state | python -m json.tool
```

Expected `/state` result: at least one route, at least one `fire` hazard, and at least one `blocked` hazard.

## Judge Demo Flow

1. Show frontend connected to backend.
2. Click `REPLAY EATON FIRE`; fire hazards appear and backend `/state` fills.
3. Dispatch a route by clicking start, end, then dispatch.
4. Run or describe the field report path: natural language report posts raw `/field-report`, parser detects blocked road, and agent posts `/hazard`.
5. Refresh `/state` to prove everything is in the shared backend state.

## If Something Breaks

- Frontend says offline: confirm backend is running on `127.0.0.1:8000` and `VITE_BACKEND_URL=http://localhost:8000` or unset.
- Cesium imagery is plain: set `VITE_CESIUM_ION_TOKEN`; the no-token fallback is expected to be less pretty but demo-safe.
- Replay has no live data: use fixture mode with `AEGIS_DATA_MODE=fixture`; this is the official fallback.
- Mongo warnings appear: safe to ignore during laptop demo unless persistence is being judged.
- Agentverse is not registered: continue local laptop demo, then debug `AGENTVERSE_API_KEY`/`AGENT_SEED` separately for prize qualification.
