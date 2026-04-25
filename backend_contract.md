0. Global Conventions
Coordinate System (MANDATORY)
[lat, lng]
Latitude first, longitude second
All coordinates are WGS84 (standard GPS)
Units:
Distance: meters
Time: seconds
Severity: 0.0 → 1.0
Timestamps
ISO 8601 UTC
Example: "2026-04-25T21:30:00Z"
IDs
route_id: string (uuid)
unit_id: string (optional, provided by frontend/agent)
event_id: string (uuid)
Standard Response Wrapper (optional but preferred)
{
  "success": true,
  "data": { ... },
  "error": null
}
1. POST /route
Purpose

Compute optimal route between two coordinates using dynamic hazard-aware A*.

Request
{
  "start_lat": 34.191,
  "start_lng": -118.131,
  "end_lat": 34.196,
  "end_lng": -118.126,
  "unit_id": "ambulance-7"
}
Response
{
  "route_id": "uuid-123",
  "path": [
    [34.191, -118.131],
    [34.193, -118.129],
    [34.196, -118.126]
  ],
  "cost": 1234.5,
  "estimated_time_s": 540,
  "rerouted": false,
  "hazards_considered": 12,
  "created_at": "2026-04-25T21:30:00Z"
}
Notes
path is ordered waypoints
rerouted = true if hazards affected the route
cost is internal A* cost (not necessarily distance)
2. POST /hazard
Purpose

Inject hazard into routing graph (fire spread, blocked road, etc.)

Request
{
  "type": "fire",
  "lat": 34.193,
  "lng": -118.129,
  "radius_m": 100,
  "severity": 0.8,
  "source": "simulation",
  "timestamp": "2026-04-25T21:30:00Z"
}
Fields
type:
  "fire" | "blocked"

severity:
  0.0 → 1.0

source:
  "simulation" | "field_report" | "manual"
Response
{
  "event_id": "hazard-uuid",
  "affected_nodes": 42,
  "updated_edges": 87,
  "active_hazards": 128
}
Behavior
Calls internal hazard_store.update_hazard()
Updates routing weights immediately
Future /route calls reflect this
3. POST /field-report
Purpose

Convert natural language field reports into structured hazards.

Request
{
  "text": "bridge on 5th is gone, complete collapse",
  "unit_id": "ambulance-7"
}
Response
{
  "parsed": {
    "lat": 34.1901,
    "lng": -118.1322,
    "status": "blocked",
    "confidence": 0.91
  },
  "action_taken": true,
  "event_id": "hazard-uuid",
  "message": "Road marked as blocked"
}
Behavior
Send text → Gemma parser
Receive structured JSON
If status == blocked:
create hazard with high penalty
Save raw + parsed report
Failure Case
{
  "parsed": {
    "lat": null,
    "lng": null,
    "status": null,
    "confidence": 0.2
  },
  "action_taken": false,
  "message": "Could not determine location"
}
4. GET /state
Purpose

Return full real-time system state for visualization layer.

Response
{
  "timestamp": "2026-04-25T21:30:00Z",

  "hazards": [
    {
      "event_id": "hazard-1",
      "type": "fire",
      "lat": 34.193,
      "lng": -118.129,
      "radius_m": 100,
      "severity": 0.8,
      "created_at": "2026-04-25T21:30:00Z"
    }
  ],

  "routes": [
    {
      "route_id": "route-7",
      "unit_id": "ambulance-7",
      "path": [[34.191, -118.131], [34.193, -118.129]],
      "rerouted": true,
      "last_updated": "2026-04-25T21:30:00Z"
    }
  ],

  "stats": {
    "total_hazards": 128,
    "active_routes": 5
  }
}
Notes
Polled every ~2 seconds by frontend
Can be extended without breaking contract
5. Optional: GET /route/{route_id}
Purpose

Fetch historical route

Response
{
  "route_id": "route-7",
  "path": [...],
  "cost": 1234.5,
  "rerouted": true,
  "created_at": "..."
}
6. Optional: POST /session
Purpose

Track demo sessions (nice for Devpost storytelling)

Request
{
  "session_name": "Eaton Fire Replay",
  "user": "demo"
}
Response
{
  "session_id": "session-uuid"
}
7. Error Format (GLOBAL)
{
  "success": false,
  "error": {
    "code": "INVALID_INPUT",
    "message": "Missing start_lat"
  }
}
8. Performance Expectations
/route latency target: < 500ms
/hazard latency target: < 200ms
/state latency target: < 100ms
9. Backend Responsibilities (Person B)
FastAPI server
Endpoint validation (Pydantic)
MongoDB writes (async, non-blocking)
Hazard state exposure
Integration with:
Routing engine (Person A)
Fire simulation (Person C)
Frontend (Person D)
Gemma parser (Person C)

---

## 10. Non-Goals (Do NOT build)

```txt
- Authentication
- User accounts
- Complex permissions
- Perfect schemas
- Production security
11. Stability Rule
Once this contract is agreed upon:
DO NOT CHANGE FIELD NAMES OR STRUCTURE

Add fields if needed, but never remove or rename.