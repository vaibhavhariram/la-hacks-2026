import * as THREE from 'three';
import { latLngToWorld } from '../utils/coords.js';
import { fetchState } from '../api/client.js';

const COLOR_BLUE = new THREE.Color(0x0088ff);
const COLOR_AMBER = new THREE.Color(0xffaa00);
const ROUTE_Y = 3;
const POLL_MS = 2000;

function routeKey(route) {
  return route.unit_id ?? route.route_id ?? 'route';
}

export class RouteManager {
  constructor(scene) {
    this.scene = scene;
    this.group = new THREE.Group();
    scene.add(this.group);

    // unitId → { mesh, material, waypoints, rerouted, flashTimer }
    this.routes = new Map();

    this._statusDot = document.getElementById('status-dot');
    this._statusText = document.getElementById('status-text');

    this._poll();
  }

  _poll() {
    setInterval(async () => {
      const state = await fetchState();
      if (state && state.routes) {
        this.syncRoutes(state.routes);
        this._setConnected(true);
      }
      if (state && state.hazards) {
        this._lastHazards = state.hazards;
      }
    }, POLL_MS);
  }

  _setConnected(ok) {
    if (this._statusDot) {
      this._statusDot.className = ok ? 'connected' : '';
      this._statusText.textContent = ok ? 'CONNECTED' : 'OFFLINE';
    }
  }

  getLatestHazards() {
    return this._lastHazards ?? [];
  }

  syncRoutes(routesArray) {
    const seen = new Set();

    for (const r of routesArray) {
      const key = routeKey(r);
      seen.add(key);
      const existing = this.routes.get(key);

      if (!existing) {
        this._addRoute(r);
      } else if (r.rerouted && !existing.rerouted) {
        this._updateRoute(key, r);
        this.highlightReroute(key);
      } else {
        this._updateRoute(key, r);
      }
    }

    // remove routes no longer in state
    for (const [id] of this.routes) {
      if (!seen.has(id)) this._removeRoute(id);
    }
  }

  _buildTube(waypoints) {
    const pts = waypoints.map((wp) => {
      const w = latLngToWorld(wp.lat, wp.lng);
      return new THREE.Vector3(w.x, ROUTE_Y, w.z);
    });

    if (pts.length < 2) return null;

    const curve = new THREE.CatmullRomCurve3(pts);
    const geo = new THREE.TubeGeometry(curve, 200, 0.8, 8, false);
    return geo;
  }

  _addRoute(r) {
    const geo = this._buildTube(r.waypoints);
    if (!geo) return;

    const mat = new THREE.MeshBasicMaterial({ color: COLOR_BLUE.clone() });
    const mesh = new THREE.Mesh(geo, mat);
    this.group.add(mesh);
    this.routes.set(routeKey(r), { mesh, material: mat, waypoints: r.waypoints, rerouted: r.rerouted, flashTimer: 0 });
  }

  _updateRoute(unitId, r) {
    const entry = this.routes.get(unitId);
    if (!entry) return;

    const newGeo = this._buildTube(r.waypoints);
    if (!newGeo) return;

    entry.mesh.geometry.dispose();
    entry.mesh.geometry = newGeo;
    entry.waypoints = r.waypoints;
    entry.rerouted = r.rerouted;
  }

  _removeRoute(unitId) {
    const entry = this.routes.get(unitId);
    if (!entry) return;
    entry.mesh.geometry.dispose();
    entry.material.dispose();
    this.group.remove(entry.mesh);
    this.routes.delete(unitId);
  }

  highlightReroute(unitId) {
    const entry = this.routes.get(unitId);
    if (!entry) return;

    entry.material.color.set(COLOR_AMBER);
    entry.flashTimer = 800;
  }

  addSingleRoute(waypoints, unitId = 'dispatched') {
    const r = { unit_id: unitId, waypoints, rerouted: false };
    if (this.routes.has(unitId)) {
      this._updateRoute(unitId, r);
    } else {
      this._addRoute(r);
    }
  }

  update(deltaMs) {
    for (const [, entry] of this.routes) {
      if (entry.flashTimer > 0) {
        entry.flashTimer -= deltaMs;
        if (entry.flashTimer <= 0) {
          entry.material.color.set(COLOR_BLUE);
        }
      }
    }
  }
}
