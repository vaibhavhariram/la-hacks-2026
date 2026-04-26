import * as THREE from 'three';
import { latLngToWorldMercator, worldToLatLngMercator } from '../utils/mercator.js';
import { TweenManager } from '../utils/tween.js';

const CENTER_LAT = 34.1897;
const CENTER_LNG = -118.1315;
const ZOOM = 15;        // was 14 — 4x more detail, streets visible
const TILE_GRID = 7;    // was 5 — wider coverage area

// Drop terrain 300m below XR origin so you float over it at god-view altitude.
// Thumbstick adjusts this live via _flyOffset.
const TERRAIN_DROP = -300;
const WORLD_SIZE = 2000;
const ELEVATION_SCALE = 4;  // was 2 — mountains look more dramatic in VR

const FLY_SPEED = 3;        // units/frame at full thumbstick deflection
const ZOOM_SPEED = 8;       // altitude change per frame

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN ?? '';

// Keep overlays visible above the terrain mesh.
const HAZARD_Y = 40;
const ROUTE_Y = 60;
const PROJ = { centerLat: CENTER_LAT, centerLng: CENTER_LNG, zoom: ZOOM, tileGrid: TILE_GRID, worldSize: WORLD_SIZE };

function latLngToTile(lat, lng, zoom) {
  const n = Math.pow(2, zoom);
  const x = Math.floor(((lng + 180) / 360) * n);
  const latRad = (lat * Math.PI) / 180;
  const y = Math.floor(((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n);
  return { x, y };
}

function terrainRGBToMeters(r, g, b) {
  return -10000 + (r * 65536 + g * 256 + b) * 0.1;
}

async function loadImage(url) {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => resolve(img);
    img.onerror = () => {
      const blank = document.createElement('canvas');
      blank.width = 256; blank.height = 256;
      resolve(blank);
    };
    img.src = url;
  });
}

export class VRScene {
  constructor() {
    this.renderer = null;
    this.scene = null;
    this.camera = null;
    this.xrSession = null;
    this.tweenManager = new TweenManager();

    this.hazards = [];
    this.routes = [];

    this._worldGroup = null;
    this._hazardMesh = null;
    this._routeGroup = null;
    this._startMarker = null;
    this._endMarker = null;
    this._terrain = null;
    this._dummy = new THREE.Object3D();

    this._uiGroup = null;
    this._exitButton = null;

    this._startPos = null;
    this._endPos = null;
    this._onDispatch = null;
    this._onExit = null;

    this._lastTime = performance.now();

    // Thumbstick locomotion state
    this._flyOffset = new THREE.Vector3(0, 0, 0); // accumulated pan/altitude offset
    this._leftStick = new THREE.Vector2(0, 0);    // left stick: pan X/Z
    this._rightStick = new THREE.Vector2(0, 0);   // right stick Y: altitude
    this._gamepadPollInterval = null;
  }

  async launch({ onDispatch, onExit }) {
    this._onDispatch = onDispatch;
    this._onExit = onExit;

    if (!navigator.xr) { alert('WebXR not available in this browser.'); return; }
    const supported = await navigator.xr.isSessionSupported('immersive-vr').catch(() => false);
    if (!supported) { alert('immersive-vr not supported — open on Quest 2 browser.'); return; }

    this._buildRenderer();
    this._buildScene();
    this._buildLights();
    this._buildStarfield();
    this._buildWorldGroup();
    this._buildFallbackGround();
    this._buildFireMesh();
    this._buildRouteGroup();
    this._buildMarkers();
    this._buildUiOverlay();

    this._loadTerrain();

    this.xrSession = await navigator.xr.requestSession('immersive-vr', {
      requiredFeatures: ['local-floor'],
    });

    this.renderer.xr.setSession(this.xrSession);
    this.xrSession.addEventListener('end', () => this._handleSessionEnd());
    this._setupControllers();
    this.renderer.setAnimationLoop(() => this._renderLoop());
  }

  _buildRenderer() {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.xr.enabled = true;
    this.renderer.domElement.style.cssText = 'position:fixed;top:0;left:0;z-index:5;';
    document.body.appendChild(this.renderer.domElement);
  }

  _buildScene() {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x000008);
    this.camera = new THREE.PerspectiveCamera(80, window.innerWidth / window.innerHeight, 0.1, 20000);
    this.scene.add(this.camera);
  }

  _buildLights() {
    this.scene.add(new THREE.AmbientLight(0xffffff, 1.6));
    const dir = new THREE.DirectionalLight(0xfff4e0, 1.2);
    dir.position.set(500, 800, 300);
    this.scene.add(dir);
  }

  _buildStarfield() {
    const count = 3000;
    const positions = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const r = 8000;
      positions[i * 3]     = (Math.random() - 0.5) * r;
      positions[i * 3 + 1] = Math.random() * r * 0.5 + 200;
      positions[i * 3 + 2] = (Math.random() - 0.5) * r;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    const mat = new THREE.PointsMaterial({ color: 0xffffff, size: 2.0, sizeAttenuation: true });
    this.scene.add(new THREE.Points(geo, mat));
  }

  _buildWorldGroup() {
    this._worldGroup = new THREE.Group();
    this._worldGroup.position.y = TERRAIN_DROP;
    this.scene.add(this._worldGroup);
  }

  _buildFallbackGround() {
    const geo = new THREE.PlaneGeometry(WORLD_SIZE, WORLD_SIZE, 4, 4);
    const mat = new THREE.MeshBasicMaterial({ color: 0x1a2a1a });
    const plane = new THREE.Mesh(geo, mat);
    plane.rotation.x = -Math.PI / 2;
    plane.name = 'fallback-ground';
    this._worldGroup.add(plane);
    this._terrain = plane;
  }

  async _loadTerrain() {
    try {
      const center = latLngToTile(CENTER_LAT, CENTER_LNG, ZOOM);
      const half = Math.floor(TILE_GRID / 2);
      const tileSize = 256;
      const gridPx = TILE_GRID * tileSize;

      const satCanvas = document.createElement('canvas');
      satCanvas.width = gridPx; satCanvas.height = gridPx;
      const satCtx = satCanvas.getContext('2d');

      const demCanvas = document.createElement('canvas');
      demCanvas.width = gridPx; demCanvas.height = gridPx;
      const demCtx = demCanvas.getContext('2d');

      const fetches = [];
      for (let dy = -half; dy <= half; dy++) {
        for (let dx = -half; dx <= half; dx++) {
          const tx = center.x + dx;
          const ty = center.y + dy;
          const px = (dx + half) * tileSize;
          const py = (dy + half) * tileSize;
          fetches.push(
            Promise.all([
              loadImage(`https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/${ZOOM}/${tx}/${ty}?access_token=${MAPBOX_TOKEN}`),
              loadImage(`https://api.mapbox.com/v4/mapbox.terrain-rgb/${ZOOM}/${tx}/${ty}.pngraw?access_token=${MAPBOX_TOKEN}`),
            ]).then(([sat, dem]) => {
              satCtx.drawImage(sat, px, py, tileSize, tileSize);
              demCtx.drawImage(dem, px, py, tileSize, tileSize);
            })
          );
        }
      }
      await Promise.all(fetches);

      const segments = 320;
      const geo = new THREE.PlaneGeometry(WORLD_SIZE, WORLD_SIZE, segments, segments);
      geo.rotateX(-Math.PI / 2);

      const demPixels = demCtx.getImageData(0, 0, gridPx, gridPx);
      const pos = geo.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        const u = Math.min(Math.floor((pos.getX(i) / WORLD_SIZE + 0.5) * gridPx), gridPx - 1);
        const v = Math.min(Math.floor((pos.getZ(i) / WORLD_SIZE + 0.5) * gridPx), gridPx - 1);
        const idx = (v * gridPx + u) * 4;
        const elev = terrainRGBToMeters(demPixels.data[idx], demPixels.data[idx + 1], demPixels.data[idx + 2]);
        pos.setY(i, (elev / 100) * ELEVATION_SCALE);
      }
      geo.computeVertexNormals();

      const tex = new THREE.CanvasTexture(satCanvas);
      tex.flipY = false;
      tex.anisotropy = this.renderer.capabilities.getMaxAnisotropy();
      tex.minFilter = THREE.LinearMipmapLinearFilter;
      tex.generateMipmaps = true;

      const mesh = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ map: tex }));
      mesh.name = 'terrain';

      const fallback = this._worldGroup.getObjectByName('fallback-ground');
      if (fallback) this._worldGroup.remove(fallback);
      this._worldGroup.add(mesh);
      this._terrain = mesh;

      console.log('[VRScene] terrain loaded (zoom 15, 7x7 grid)');
    } catch (e) {
      console.warn('[VRScene] terrain load failed:', e.message);
    }
  }

  _buildFireMesh() {
    const geo = new THREE.CircleGeometry(1, 32);
    const mat = new THREE.MeshBasicMaterial({
      color: 0xff4400, transparent: true, opacity: 0.65, side: THREE.DoubleSide,
    });
    this._hazardMesh = new THREE.InstancedMesh(geo, mat, 512);
    this._hazardMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this._hazardMesh.count = 0;
    this._hazardMesh.rotation.x = -Math.PI / 2;
    this._hazardMesh.position.y = HAZARD_Y;
    this._worldGroup.add(this._hazardMesh);
  }

  _buildRouteGroup() {
    this._routeGroup = new THREE.Group();
    this._worldGroup.add(this._routeGroup);
  }

  _buildMarkers() {
    const makeRing = (color) => {
      const geo = new THREE.TorusGeometry(5, 0.8, 8, 32);
      const mat = new THREE.MeshBasicMaterial({ color });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.rotation.x = Math.PI / 2;
      mesh.visible = false;
      this._worldGroup.add(mesh);
      return mesh;
    };
    this._startMarker = makeRing(0x00ff88);
    this._endMarker = makeRing(0xff4444);
  }

  _buildUiOverlay() {
    // Fixed-to-view UI so users can exit VR without relying on DOM clicks.
    this._uiGroup = new THREE.Group();
    this._uiGroup.position.set(0.25, -0.25, -0.8);
    this.camera.add(this._uiGroup);

    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 192;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = 'rgba(0,0,0,0.55)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = '#ff4400';
    ctx.lineWidth = 12;
    ctx.strokeRect(10, 10, canvas.width - 20, canvas.height - 20);
    ctx.fillStyle = '#ff4400';
    ctx.font = 'bold 64px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('EXIT VR', canvas.width / 2, canvas.height / 2);

    const tex = new THREE.CanvasTexture(canvas);
    tex.needsUpdate = true;

    const geo = new THREE.PlaneGeometry(0.35, 0.13);
    const mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true });
    this._exitButton = new THREE.Mesh(geo, mat);
    this._exitButton.name = 'exit-vr-button';
    this._uiGroup.add(this._exitButton);
  }

  _uiHit(controller) {
    if (!this._exitButton) return false;
    const raycaster = new THREE.Raycaster();
    const dir = new THREE.Vector3(0, 0, -1).applyQuaternion(controller.quaternion);
    const origin = new THREE.Vector3().setFromMatrixPosition(controller.matrixWorld);
    raycaster.set(origin, dir);
    const hits = raycaster.intersectObject(this._exitButton, false);
    return hits.length > 0;
  }

  _setupControllers() {
    const ctrl0 = this.renderer.xr.getController(0); // left
    const ctrl1 = this.renderer.xr.getController(1); // right
    this.scene.add(ctrl0);
    this.scene.add(ctrl1);

    // Laser pointer on right controller
    const pts = [new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, -800)];
    const ray = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(pts),
      new THREE.LineBasicMaterial({ color: 0x00ff88, opacity: 0.35, transparent: true })
    );
    ctrl1.add(ray);

    const raycaster = new THREE.Raycaster();

    const getTerrainHit = () => {
      if (!this._terrain) return null;
      const dir = new THREE.Vector3(0, 0, -1).applyQuaternion(ctrl1.quaternion);
      const origin = new THREE.Vector3().setFromMatrixPosition(ctrl1.matrixWorld);
      raycaster.set(origin, dir);
      const hits = raycaster.intersectObject(this._terrain, false);
      return hits.length ? hits[0].point : null;
    };

    // left trigger → set start (or UI click)
    ctrl0.addEventListener('selectstart', () => {
      if (this._uiHit(ctrl0)) {
        this.destroy();
        return;
      }
      const hit = getTerrainHit();
      if (!hit) return;
      const local = this._worldGroup.worldToLocal(hit.clone());
      this._startPos = local.clone();
      this._startMarker.position.set(local.x, local.y + 5, local.z);
      this._startMarker.visible = true;
    });

    // right trigger → set end (or UI click)
    ctrl1.addEventListener('selectstart', () => {
      if (this._uiHit(ctrl1)) {
        this.destroy();
        return;
      }
      const hit = getTerrainHit();
      if (!hit) return;
      const local = this._worldGroup.worldToLocal(hit.clone());
      this._endPos = local.clone();
      this._endMarker.position.set(local.x, local.y + 5, local.z);
      this._endMarker.visible = true;
    });

    // right grip → dispatch
    ctrl1.addEventListener('squeezestart', () => {
      if (this._uiHit(ctrl1)) {
        this.destroy();
        return;
      }
      this._dispatchRoute();
    });
  }

  // Read gamepad thumbsticks each frame inside the XR session
  _pollGamepads() {
    const session = this.renderer.xr.getSession();
    if (!session) return;
    for (const source of session.inputSources) {
      const gp = source.gamepad;
      if (!gp) continue;
      const axes = gp.axes;
      if (source.handedness === 'left' && axes.length >= 4) {
        // axes[2]/[3] = left thumbstick X/Y on Quest 2
        this._leftStick.set(axes[2] ?? 0, axes[3] ?? 0);
      }
      if (source.handedness === 'right' && axes.length >= 4) {
        this._rightStick.set(axes[2] ?? 0, axes[3] ?? 0);
      }
    }
  }

  _applyLocomotion() {
    const lx = Math.abs(this._leftStick.x) > 0.12 ? this._leftStick.x : 0;
    const lz = Math.abs(this._leftStick.y) > 0.12 ? this._leftStick.y : 0;
    const ry = Math.abs(this._rightStick.y) > 0.12 ? this._rightStick.y : 0;

    if (lx === 0 && lz === 0 && ry === 0) return;

    // Pan relative to where the player is looking (yaw only, ignore pitch)
    const cam = this.renderer.xr.getCamera();
    const yaw = new THREE.Euler(0, cam.rotation.y, 0, 'YXZ');
    const forward = new THREE.Vector3(0, 0, -1).applyEuler(yaw);
    const right   = new THREE.Vector3(1, 0,  0).applyEuler(yaw);

    // Move the worldGroup — panning moves terrain under you
    this._worldGroup.position.addScaledVector(right,   -lx * FLY_SPEED);
    this._worldGroup.position.addScaledVector(forward,  lz * FLY_SPEED);
    // Right stick Y: push up/down
    this._worldGroup.position.y += ry * ZOOM_SPEED;
  }

  _dispatchRoute() {
    if (!this._startPos || !this._endPos || !this._onDispatch) return;
    const start = worldToLatLngMercator(this._startPos.x, this._startPos.z, PROJ);
    const end = worldToLatLngMercator(this._endPos.x, this._endPos.z, PROJ);
    const startLat = start.lat;
    const startLng = start.lng;
    const endLat = end.lat;
    const endLng = end.lng;
    this._onDispatch({ lat: startLat, lng: startLng }, { lat: endLat, lng: endLng });
  }

  updateHazards(hazards) {
    this.hazards = hazards;
    if (!this._hazardMesh) return;
    let i = 0;
    for (const h of hazards) {
      if (i >= 512) break;
      const w = latLngToWorldMercator(h.lat, h.lng, PROJ);
      this._dummy.position.set(w.x, 0, w.z);
      const scale = h.radius_m / 100;
      this._dummy.scale.set(scale, scale, scale);
      this._dummy.updateMatrix();
      this._hazardMesh.setMatrixAt(i++, this._dummy.matrix);
    }
    this._hazardMesh.count = i;
    this._hazardMesh.instanceMatrix.needsUpdate = true;
  }

  updateRoutes(routes) {
    this.routes = routes;
    if (!this._routeGroup) return;
    while (this._routeGroup.children.length) {
      const c = this._routeGroup.children[0];
      c.geometry?.dispose(); c.material?.dispose();
      this._routeGroup.remove(c);
    }
    for (const r of routes) {
      const wps = r.waypoints ?? r.path ?? [];
      if (wps.length < 2) continue;
      const pts = wps.map((wp) => {
        const w = latLngToWorldMercator(wp.lat ?? wp[0], wp.lng ?? wp[1], PROJ);
        return new THREE.Vector3(w.x, ROUTE_Y, w.z);
      });
      const curve = new THREE.CatmullRomCurve3(pts);
      const geo = new THREE.TubeGeometry(curve, 200, 1.5, 8, false);
      const mat = new THREE.MeshBasicMaterial({ color: r.rerouted ? 0xffaa00 : 0x0088ff });
      this._routeGroup.add(new THREE.Mesh(geo, mat));
    }
  }

  _renderLoop() {
    const now = performance.now();
    const delta = Math.min(now - this._lastTime, 50);
    this._lastTime = now;
    this.tweenManager.update(delta);

    this._pollGamepads();
    this._applyLocomotion();

    if (this._startMarker?.visible) this._startMarker.rotation.z += 0.008;
    if (this._endMarker?.visible) this._endMarker.rotation.z -= 0.008;
    this.renderer.render(this.scene, this.camera);
  }

  _handleSessionEnd() {
    this.renderer.setAnimationLoop(null);
    this.renderer.domElement.remove();
    this.renderer.dispose();
    this.renderer = null;
    this.scene = null;
    this.xrSession = null;
    if (this._onExit) this._onExit();
  }

  destroy() {
    if (this.xrSession) this.xrSession.end();
    else this._handleSessionEnd();
  }
}
