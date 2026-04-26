import { MOCK_ROUTE, MOCK_STATE, MOCK_FIELD_REPORT } from './mockData.js';

const BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

function normalizeWaypoint(point) {
  if (Array.isArray(point) && point.length >= 2) {
    return { lat: Number(point[0]), lng: Number(point[1]) };
  }

  if (point && typeof point === 'object') {
    return { lat: Number(point.lat), lng: Number(point.lng) };
  }

  return null;
}

export function normalizeWaypoints(points = []) {
  if (!Array.isArray(points)) return [];
  return points.map(normalizeWaypoint).filter((point) => (
    point
    && Number.isFinite(point.lat)
    && Number.isFinite(point.lng)
  ));
}

export function normalizeRoute(route = {}) {
  const waypoints = normalizeWaypoints(route.waypoints ?? route.path ?? []);
  return {
    ...route,
    path: waypoints,
    waypoints,
  };
}

export function normalizeState(state = {}) {
  return {
    ...state,
    routes: Array.isArray(state.routes) ? state.routes.map(normalizeRoute) : [],
    hazards: Array.isArray(state.hazards) ? state.hazards : [],
  };
}

export async function fetchRoute(startLat, startLng, endLat, endLng, unitId = `unit-${Date.now()}`) {
  try {
    const res = await fetch(`${BASE_URL}/route`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start_lat: startLat,
        start_lng: startLng,
        end_lat: endLat,
        end_lng: endLng,
        unit_id: unitId,
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return normalizeRoute(await res.json());
  } catch (e) {
    console.warn('[client] fetchRoute fallback to mock:', e.message);
    return normalizeRoute(MOCK_ROUTE);
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
    return normalizeState(await res.json());
  } catch (e) {
    console.warn('[client] fetchState fallback to mock:', e.message);
    return normalizeState(MOCK_STATE);
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
