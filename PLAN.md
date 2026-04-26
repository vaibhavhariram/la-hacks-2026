# AEGIS Person C — Implementation Plan

> LAHacks 2026 · Person C owns GIS pipeline, fire simulation, Gemma parser, Fetch.ai agents
> **APPROVED** — Phase 2 scaffolding in progress.

---

## 1. Subsystem Dependency Graph

```
[FIRMS pipeline]─────────────────────────────►[Fire spread sim]
       │                                              │
       ▼                                              ▼
[MongoDB / local JSON]                     [POST /hazard (stub→B)]
                                                      │
[NOAA wind fetcher]──────────────────────►[Fire spread sim]
                                                      │
[Google AI Studio key]                                │
       │                                              │
       ▼                                              │
[Gemma 2B parser]────────────────────────►[Fetch.ai uAgent]
                                                      │
[Agentverse registration]────────────────►[Fetch.ai uAgent]
                                                      │
                                                      ▼
                                          [POST /field-report (stub→B)]

[Stub backend]──────────blocks nothing──────────────────────────────
(absorbs all outbound calls so I never block on Person B)
```

**Key insight:** stub backend is the first thing I build. Once it exists, all 4 subsystems can be developed and tested in parallel with no dependency on B.

---

## 2. Recommended Build Order

| Step | What | Why |
|------|------|-----|
| 0 | Create all API accounts (FIRMS, Google AI Studio, Agentverse) | Approval emails can take minutes; start the clock now, before bed |
| 1 | Scaffold repo + pyproject.toml + .env.example | Zero cost, unblocks all subsequent work |
| 2 | Write mock stub server (`stub/backend_stub.py`) | Eliminates Person B dependency immediately; takes 15 min |
| 3 | FIRMS pipeline (`gis/firms_pipeline.py`) | Foundation data — every other subsystem references the fire perimeter |
| 4 | NOAA wind fetcher (`gis/noaa_wind.py`) | Standalone, fast, data needed before fire spread can run |
| 5 | Fire spread simulation (`gis/fire_spread.py`) | Depends on steps 3 + 4; highest visual impact for demo |
| 6 | Gemma parser (`agents/gemma_parser.py`) | Self-contained, easy to unit-test, needed before agents |
| 7 | Fetch.ai uAgent with Chat Protocol (`agents/field_unit_agent.py`) | Last because it depends on Gemma and Agentverse registration; also highest risk |
| 8 | Demo replay script (`scripts/run_demo.py`) | Wires everything together for the judging session |
| 9 | Integration against real Person B backend | Swap `BACKEND_URL` env var; no code changes needed |

---

## 3. API Accounts to Create Tonight (Before Bed)

| Service | URL | What you get | Notes |
|---------|-----|-------------|-------|
| **NASA FIRMS** | https://firms.modaps.eosdis.nasa.gov/api/ | `MAP_KEY` | Approval is usually instant; click "Get MAP Key" |
| **Google AI Studio** | https://aistudio.google.com | `GOOGLE_AI_API_KEY` | Free tier; Gemma 2 models available |
| **Agentverse (Fetch.ai)** | https://agentverse.ai | account + `AGENTVERSE_API_KEY` | Required for Chat Protocol $5K prize — non-negotiable |
| **MongoDB Atlas** | https://cloud.mongodb.com | cluster URI | Free M0 tier; get URI from Person B so both of you point at the same DB |

**Iowa Mesonet (NOAA wind):** No account needed. Free public REST API, no key required.

---

## 4. Python Dependencies for `pyproject.toml`

```toml
[project]
name = "aegis-gis"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    # HTTP
    "httpx>=0.27",
    "requests>=2.31",

    # GIS / geometry
    "shapely>=2.0",
    "pyproj>=3.6",
    "geojson>=3.1",
    "numpy>=1.26",
    "scipy>=1.13",

    # Database
    "pymongo>=4.7",
    "motor>=3.4",

    # Google AI / Gemma — VERIFIED: `pip install google-genai` → `from google import genai` works (v1.73.1)
    "google-genai>=1.0",

    # Fetch.ai agents
    "uagents>=0.13",
    "uagents-ai-engine>=0.4",

    # Mock backend stub
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",

    # Config
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
]
```

> **`google-genai` verified:** `pip install google-genai && python -c "from google import genai; print(genai.__version__)"` → `1.73.1` ✓

---

## 5. `.env` Variables

> **Do not put real keys in this file or in PLAN.md. Real keys go in `.env` (gitignored).**

```bash
# .env.example — copy to .env and fill in real values

# NASA FIRMS — https://firms.modaps.eosdis.nasa.gov/api/
FIRMS_MAP_KEY=

# Google AI Studio — https://aistudio.google.com/apikey
GOOGLE_AI_API_KEY=

# Agentverse — https://agentverse.ai → Settings → API Keys
AGENTVERSE_API_KEY=

# MongoDB Atlas — get URI from Person B
MONGODB_URI=mongodb+srv://...

# Backend URL — stub locally, swap to B's URL at integration
BACKEND_URL=http://localhost:8001

# Fetch.ai agent seed phrase for deterministic wallet address
AGENT_SEED=
```

| Variable | Where to get it |
|----------|----------------|
| `FIRMS_MAP_KEY` | NASA FIRMS registration email |
| `GOOGLE_AI_API_KEY` | Google AI Studio → "Get API key" |
| `AGENTVERSE_API_KEY` | Agentverse dashboard → Settings → API Keys |
| `MONGODB_URI` | Person B or your own Atlas cluster → Connect → Drivers |
| `BACKEND_URL` | `http://localhost:8001` during dev; Person B gives real URL at integration |
| `AGENT_SEED` | `python -c "import secrets; print(secrets.token_hex(32))"` |

---

## 6. Risk Register

| # | Risk | Probability | Impact | Fallback |
|---|------|------------|--------|---------|
| 1 | **FIRMS archived data for Jan 8 2025 returns no results / API is flaky** | Medium | High | Use FIRMS bulk CSV download (no key needed). Pre-download and commit `data/eaton_fire_jan8.geojson` tonight before building anything. This is the single most important pre-work action. |
| 2 | **Agentverse registration fails / Chat Protocol API breaks** | High | **Critical — $5K prize lost** | Agentverse registration is not a stretch goal, it is a hard requirement. If registration fails by hour 8, escalate immediately and spend up to one hour debugging. Canonical fallback: run agent in mailbox mode (locally running, registered remotely via Agentverse mailbox address) per Fetch.ai docs. Do NOT fall back to local-only demo and call it done — that does not qualify. |
| 3 | **Gemma 2B on Google AI Studio is too slow or unavailable** | Low | Medium | Swap model ID to `gemini-2.0-flash` — free, same API surface, faster and more reliable. One-line change. |
| 4 | **Person B's backend not ready at integration time** | High | Low | Stub server absorbs this. Swap `BACKEND_URL` env var when B is ready — zero code change. Keep stub running in a background terminal for the entire hackathon. |
| 5 | **Fire spread simulation produces visually wrong results** | Medium | Medium | Pre-compute 12 static time-step GeoJSONs offline, save to `data/snapshots/`. Demo replays them at 1 frame/second. Build the static export path from the start so it's always available as a fallback. |

---

## 7. Non-goals (do not build, even if tempted)

```
- Cellular automata fire spread (use directional cone + scatter only)
- Real fire physics (heat transfer, fuel moisture, terrain elevation effects)
- Multi-agent route negotiation (Person A's territory)
- Custom fine-tuned Gemma model (use Gemma 2B as-is, prompt-engineer only)
- Database schemas beyond what Person B asks for
- Web UI for testing (use curl + pytest)
- Production-grade error handling (log + skip, don't retry-with-backoff)
- Multi-region FIRMS fetch (LA bbox only, single date)
```

Re-read this list whenever you feel the urge to add a feature.

---

## 8. First 2 Hours of Build — Exact Checklist

```
[ ] 1. Create NASA FIRMS account → confirm MAP_KEY arrives
[ ] 2. Create Google AI Studio account → generate API key → verify:
        python -c "from google import genai; c = genai.Client(api_key='...'); print('ok')"
[ ] 3. Create Agentverse account → note login + generate API key
[ ] 4. Text/Slack Person B → get MongoDB Atlas URI + confirm /field-report body shape + port
[ ] 5. cd la-hacks-2026 && source venv/bin/activate
[ ] 6. pip install -e ".[dev]"
[ ] 7. cp .env.example .env → fill in all keys you have so far
[ ] 8. Start stub: uvicorn stub.backend_stub:app --port 8001 --reload
[ ] 9. Smoke test stub:
        curl -s -X POST http://localhost:8001/hazard \
          -H "Content-Type: application/json" \
          -d '{"type":"fire","lat":34.18,"lng":-118.1,"radius_m":500,"severity":0.8}' | python -m json.tool
[ ] 10. Implement gis/firms_pipeline.py → run it
[ ] 11. Verify FIRMS returns points for Eaton Fire bbox: -118.3,34.1,-117.9,34.4
[ ] 12. Cache output to gis/data/eaton_fire_jan8.json
```

By end of hour 2: stub running, FIRMS data cached locally, all API keys confirmed.

---

## 9. Directory Structure

```
la-hacks-2026/
├── gis/
│   ├── __init__.py
│   ├── firms_pipeline.py      # FIRMS fetch + GeoJSON conversion
│   ├── noaa_wind.py           # Iowa Mesonet historical wind fetch
│   ├── fire_spread.py         # Wind-driven radial spread model
│   └── data/                  # Cached API responses (gitignored for large files)
│       └── .gitkeep
├── agents/
│   ├── __init__.py
│   ├── gemma_parser.py        # Google AI SDK → extract lat/lng/status from text
│   └── field_unit_agent.py    # Fetch.ai uAgent with Chat Protocol
├── stub/
│   └── backend_stub.py        # Mock Person B backend (FastAPI, fully implemented)
├── scripts/
│   └── run_demo.py            # End-to-end demo replay (Eaton Fire Jan 8 2025)
├── tests/
│   ├── test_firms.py
│   ├── test_gemma.py
│   └── test_fire_spread.py
├── CONTRACT.md                # Assumed answers to Person B coordination questions
├── pyproject.toml
├── .env.example
├── .env                       # gitignored — real keys go here ONLY
├── .gitignore
└── PLAN.md
```

---

## 10. Git Discipline

### Branch strategy
- `main` is sacred — never push directly during the hackathon
- Work on `person-c/gis-agents`
- After each subsystem step lands and tests pass, open a PR to main, self-merge with squash-and-merge
- Pull from main frequently before starting any new step

### Initial setup (do once, run yourself)
```bash
git checkout main
git pull origin main
git checkout -b person-c/gis-agents
git push -u origin person-c/gis-agents
```

### After every meaningful step
A "meaningful step" = a subsystem milestone or runnable, testable unit (~30–90 min of build).
```bash
make test                        # must pass before committing
make lint                        # catch syntax errors
git status                       # confirm nothing unexpected staged
git diff --staged                # read what you're about to push
git add -A
git commit -m "<type>(<scope>): <imperative summary>"
git push origin person-c/gis-agents
```

### Commit message convention (Conventional Commits)
Format: `<type>(<scope>): <imperative summary>`

Types: `feat` · `fix` · `chore` · `docs` · `test` · `refactor`

Scopes: `firms` · `wind` · `spread` · `gemma` · `agents` · `stub` · `repo`

Good examples:
- `chore(repo): scaffold directory structure and pyproject.toml`
- `feat(stub): mock backend with /hazard and /field-report endpoints`
- `feat(firms): pull Eaton Fire data from NASA FIRMS API`
- `fix(spread): correct wind bearing convention (degrees from north)`
- `test(gemma): 10-example field report regression suite`
- `docs(plan): mark subsystem 2 complete`

Bad (never write): `update` · `wip` · `fixed bug` · `more changes`

### Commit cadence per Phase 3 step

| Step | Commits expected |
|------|-----------------|
| Scaffold | 1: `chore(repo): scaffold` |
| FIRMS pipeline | 2–3: client → cache → test pass |
| Wind + fire spread | 3–4: noaa → wind model → spread loop → stub integration |
| Gemma parser | 2–3: prompt → parser → test pass |
| Fetch.ai agents | 3–4: chat proto → field unit → agentverse register |
| End-to-end smoke | 1–2: e2e → fixes |
| Hand-off | 2: replay export → INTEGRATION.md |

Target: 14–19 commits. Fewer than 10 at handoff means commits were too coarse.

### When merging to main (end of each subsystem)
```bash
git checkout main && git pull origin main
git checkout person-c/gis-agents
git rebase main
git push --force-with-lease origin person-c/gis-agents
# open PR on GitHub → self-merge with squash-and-merge
```

### Pre-commit hook (already installed)
`.git/hooks/pre-commit` blocks `.env` files and files >5MB from being committed.
If it fires: `git reset HEAD <file>`, fix `.gitignore`, then re-commit.

---

## 11. Integration Handoff Points

| What I give Person A | What I give Person B | What I give Person D |
|---------------------|---------------------|---------------------|
| Fire perimeter GeoJSON at each time step (via `/hazard` POSTs) | Structured field reports from Gemma parser (via `/field-report` POSTs) | Nothing direct — D reads `/state` from B's API |
| Hazard polygons stored in MongoDB via B's API | Raw text logged so B can debug parser failures | Fire timestamps for replay timeline |
