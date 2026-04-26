# Eye in the Sky

Eye in the Sky is a real-time emergency routing and situational awareness system designed for wildfire response. It combines a shared hazard/state backend, hazard-aware routing, a replayable fire-spread demo, and a VR “god view” command center to help dispatchers and field teams make safer routing decisions under rapidly changing conditions.

This repo was built for LAHacks 2026 (Apr 24–26, 2026 @ UCLA).

---

## Why it matters

Wildfires create a moving, uncertain hazard field:

- Roads can become blocked (debris, downed lines, active flame fronts).
- Conditions change minute-to-minute (wind shifts, flare-ups).
- Dispatch decisions depend on a common operating picture shared across roles (command center, EMS drivers, field units).

Eye in the Sky is a hackathon-scale prototype that shows how a shared “hazards + routes” state can drive **hazard-aware routing** and a **visual command center** (2D/desktop + VR).

---

## What it does

**Core flows**

1. **Route requests**: Submit start/end coordinates → backend returns a path and whether it was rerouted due to hazards.
2. **Hazard ingestion**: Post fire/blocked hazards → backend stores them (memory + optional MongoDB) and exposes them via `/state`.
3. **State polling**: Frontend polls `/state` ~every 2 seconds → renders hazards and active routes.
4. **VR command center**: Enter WebXR on Quest → set start/end, dispatch a route, view hazards and routes in 3D.

**Demo / offline-safe flows**

- **Eaton Fire replay**: A built-in replay button emits fire hazards over time (works even if external services are down).
- **Fixture-first GIS**: FIRMS fire points + NOAA/IEM wind data can load from committed fixtures for stable demos.

**Agent / field report flow (optional)**

- A Fetch.ai `uAgents` Chat Protocol agent can accept natural-language field reports.
- Reports can be parsed (Gemma via Google GenAI SDK, with deterministic fallback) and forwarded to the backend as hazards.

---

## Architecture (high level)

- **Frontend (`frontend/`)**: Cesium globe + Three.js VR scene. Calls backend `/route`, `/hazard`, `/field-report`, and polls `/state`.
- **Backend (`backend/`)**: FastAPI app exposing the API contract. Pluggable routing engine:
  - `backend/routing_engine.py`: fast demo grid router (not street-following).
  - `backend/routing_engine_osm.py`: road-following router using OSMnx/NetworkX (street-following).
- **GIS (`gis/`)**: FIRMS fire points pipeline + wind fetcher + fire spread simulation + snapshot export.
- **Agent (`agents/`)**: Field unit agent + generative parser wrapper.
- **Stub (`stub/`)**: Fallback backend that accepts posts when a real backend isn’t available.

---

## Quick start (laptop demo)

### 1) Python setup

From repo root:

```bash
python3 -m venv venv
source venv/bin/activate
make install
```

### 2) Frontend setup

```bash
cd frontend
npm ci
cd ..
```

### 3) Configure env files (recommended)

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Fill in what you have. Tokens are optional; the app has fallbacks.

### 4) Run backend (port 8000)

```bash
cd backend
../venv/bin/python -m uvicorn main:app --port 8000
```

### 5) Run frontend (port 5173)

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

Open:

- Desktop: `http://127.0.0.1:5173/`
- Quest (same WiFi): `https://<your-lan-ip>:5173/` (see `frontend/QUEST_SETUP.md`)

---

## Using the app

### Desktop (Cesium)

- Click once → set **START**
- Click again → set **END**
- Click again → dispatch route
- `REPLAY EATON FIRE` → emits hazards over time (and posts them to backend if online)

### VR (Quest / WebXR)

- Left trigger → set **START**
- Right trigger → set **END**
- Right grip → dispatch route
- “EXIT VR” button (in-VR overlay) → exit back to the normal web view

---

## Routing engines (important)

The backend routing engine is pluggable via `backend/.env`:

### Demo grid routing (fast, not street-following)

```bash
ROUTING_ENGINE_MODULE=routing_engine
ROUTING_ENGINE_PATH=./routing_engine.py
```

This is hazard-aware but routes on a 40×40 grid, so it won’t follow real streets.

### Road-following routing (recommended for realistic demos)

```bash
ROUTING_ENGINE_MODULE=routing_engine_osm
ROUTING_ENGINE_PATH=./routing_engine_osm.py
```

This uses an OpenStreetMap road graph and A* so polylines follow streets. First run may download OSM data and cache a graph locally.

---

## API (backend)

The primary endpoints are:

- `POST /route` → compute route between coordinates
- `POST /hazard` → inject a hazard (fire/blocked)
- `POST /field-report` → parse a field report (mock/simple in `backend/main.py`)
- `GET /state` → hazards + active routes (polled by frontend)
- `GET /health` → health check

See `backend_contract.md` for the detailed request/response shapes.

---

## GIS + fire simulation (optional)

Run the demo replay pipeline:

```bash
make simulate
```

Or export-only (no backend posting):

```bash
make simulate-no-post
```

Data mode:

- `AEGIS_DATA_MODE=fixture` uses committed fixtures (demo-safe).
- `AEGIS_DATA_MODE=real` attempts live FIRMS/IEM fetches (requires connectivity / keys).

---

## Agent (optional)

Run the field unit agent:

```bash
make agent
```

It can parse text using Google GenAI (Gemma) when `GOOGLE_AI_API_KEY` is set, and otherwise falls back to deterministic parsing.

---

## Environment variables

### Frontend (`frontend/.env`)

- `VITE_BACKEND_URL` (default: `http://localhost:8000`)
- `VITE_MAPBOX_TOKEN` (optional; improves imagery/terrain in some views)
- `VITE_CESIUM_ION_TOKEN` (optional; enables Cesium world terrain)
- `VITE_DEV_HTTPS` (Quest-friendly local HTTPS toggle)

### Backend (`backend/.env`)

- `PORT` (default `8000`)
- `MONGO_URI` / `MONGODB_URI` (optional; enables persistence)
- `DB_NAME` (default `la_hacks_2026`)
- `ROUTING_ENGINE_MODULE` / `ROUTING_ENGINE_PATH` (see above)

---

## Troubleshooting

### Frontend shows OFFLINE / console shows `ERR_CONNECTION_REFUSED`

You’re not running the backend on `VITE_BACKEND_URL`. Start backend or point to stub.

### Routes don’t follow roads

Enable the OSM routing engine in `backend/.env`:

```bash
ROUTING_ENGINE_MODULE=routing_engine_osm
ROUTING_ENGINE_PATH=./routing_engine_osm.py
```

Restart backend.

### VR overlays don’t line up with terrain

VR uses WebMercator projection aligned to the same Mapbox tile grid used for terrain. If you change `ZOOM`, `TILE_GRID`, or `WORLD_SIZE` in `frontend/src/xr/VRScene.js`, keep them consistent with the projection config.

---

## Repo map

- `frontend/` — Cesium + VR UI
- `backend/` — FastAPI backend + routing engine(s)
- `gis/` — FIRMS + wind + fire spread simulation
- `agents/` — GenAI parser + uAgents field unit agent
- `stub/` — fallback backend
- `scripts/` — demo orchestration + smoke tests
- `tests/` — unit tests for GIS/parser/routing utilities
