import { MOCK_ROUTE, MOCK_STATE, MOCK_FIELD_REPORT } from './mockData.js';

const BASE_URL = 'http://localhost:8000';

export async function fetchRoute(startLat, startLng, endLat, endLng) {
  try {
    const res = await fetch(`${BASE_URL}/route`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start_lat: startLat,
        start_lng: startLng,
        end_lat: endLat,
        end_lng: endLng,
        unit_id: `unit-${Date.now()}`,
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.warn('[client] fetchRoute fallback to mock:', e.message);
    return MOCK_ROUTE;
  }
}

export async function postHazard(lat, lng, radiusM, severity, type = 'fire') {
  try {
    const res = await fetch(`${BASE_URL}/hazard`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat, lng, radius_m: radiusM, severity, type }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.warn('[client] postHazard fallback to mock:', e.message);
    return { affected_nodes: 0, updated_edges: 0 };
  }
}

export async function fetchState() {
  try {
    const res = await fetch(`${BASE_URL}/state`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.warn('[client] fetchState fallback to mock:', e.message);
    return MOCK_STATE;
  }
}

export async function postFieldReport(text) {
  try {
    const res = await fetch(`${BASE_URL}/field-report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.warn('[client] postFieldReport fallback to mock:', e.message);
    return MOCK_FIELD_REPORT;
  }
}
