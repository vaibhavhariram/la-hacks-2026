# Eye in the Sky — Inter-Team Contract (Person C Assumptions)

> Written 2026-04-25. These are assumed answers to the 4 coordination questions from PLAN.md.
> **Override any line here the moment Person B responds.** Nothing here blocks build start.

---

## Q1 — `/field-report` body shape

**Assumption:** Person C parses with Gemma and sends structured data to B.

```json
POST /field-report
{
  "lat": 34.18,
  "lng": -118.09,
  "status": "blocked",
  "confidence": 0.92,
  "raw_text": "Highway 2 at mile marker 14 is completely blocked by fallen trees"
}
```

**Rationale:** Keeps Gemma latency on my side, gives B a clean structured record with no NLP needed. If B wants raw text only, drop the parsed fields and send `{"raw_text": "..."}` — one-line change in `agents/field_unit_agent.py`.

**Risk if wrong:** B's `/field-report` handler errors on unknown fields → add `raw_text` only, remove others.

---

## Q2 — MongoDB write ownership

**Assumption:** I write only via B's REST API (`POST /hazard`, `POST /field-report`). I do NOT write to MongoDB directly.

**Rationale:** Less coupling — B controls schema, I don't need the Atlas URI for anything except reading state.

**Risk if wrong:** If B's backend is down for a long period, I can't store data. Mitigation: stub server always running.

---

## Q3 — Hazard keying (does Person A need node_id?)

**Assumption:** I POST raw `(lat, lng)` to `/hazard`. Person A's router resolves to nearest graph node internally via B's API. I do NOT call A's `nearest_node()`.

**Rationale:** Avoids a hard dependency on A's API surface. If A needs node_id, B mediates the lookup.

**Risk if wrong:** A's router ignores fire hazards until this is plumbed. Fix: call B → B calls A, or I call A's nearest_node endpoint directly.

---

## Q4 — Port assignments

**Assumption:**
- My stub backend: `:8001`
- Person B's real backend: `:8000`
- Person A's routing engine: `:8002` (if exposed)
- `BACKEND_URL=http://localhost:8001` in dev; B gives real URL at integration

**Rationale:** Standard convention, avoids collision.

**Risk if wrong:** Port collision when B runs locally. Fix: change `BACKEND_URL` in `.env`.

---

## MongoDB collection names (bonus assumption)

| Collection | Owner | Purpose |
|-----------|-------|---------|
| `hazard_events` | Person B | Fire perimeter + road block records |
| `field_reports` | Person B | Parsed field unit reports |

I will not create or write to these collections directly.
