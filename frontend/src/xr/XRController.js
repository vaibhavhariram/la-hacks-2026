import * as THREE from 'three';
import { worldToLatLng } from '../utils/coords.js';
import { fetchRoute } from '../api/client.js';
import { speak } from '../audio/VoiceAlerts.js';

const RAY_LENGTH = 20;

export class XRController {
  constructor(renderer, scene, markers, routeManager) {
    this.markers = markers;
    this.routeManager = routeManager;
    this.groundPlane = null;

    this._raycaster = new THREE.Raycaster();
    this._cursor = this._makeCursor(scene);
    this._dispatching = false;

    // XR controllers
    this._ctrl0 = renderer.xr.getController(0); // left
    this._ctrl1 = renderer.xr.getController(1); // right
    scene.add(this._ctrl0);
    scene.add(this._ctrl1);

    this._addRay(scene, this._ctrl0);
    this._addRay(scene, this._ctrl1);

    this._ctrl0.addEventListener('selectstart', () => this._onLeftTrigger());
    this._ctrl1.addEventListener('selectstart', () => this._onRightTrigger());
    this._ctrl1.addEventListener('squeezestart', () => this._onRightGrip());

    // Desktop fallback
    this._clickState = 0; // 0=set start, 1=set end, 2=dispatch
    this._mouse = new THREE.Vector2();
    this._setupDesktopFallback(renderer);
  }

  setGroundPlane(plane) {
    this.groundPlane = plane;
  }

  // accepts a getter fn so async terrain swap is always reflected
  setGroundPlaneGetter(fn) {
    this._groundPlaneGetter = fn;
  }

  _makeCursor(scene) {
    const geo = new THREE.SphereGeometry(1.5, 8, 8);
    const mat = new THREE.MeshBasicMaterial({ color: 0xffffff, opacity: 0.8, transparent: true });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.visible = false;
    scene.add(mesh);
    return mesh;
  }

  _addRay(scene, controller) {
    const pts = [new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, -RAY_LENGTH)];
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    const mat = new THREE.LineBasicMaterial({ color: 0x00ff88, opacity: 0.5, transparent: true });
    const line = new THREE.Line(geo, mat);
    controller.add(line);
  }

  _getPlane() {
    return this._groundPlaneGetter ? this._groundPlaneGetter() : this.groundPlane;
  }

  _getRightControllerHit() {
    const plane = this._getPlane();
    if (!plane || !this._ctrl1.matrixWorld) return null;
    const dir = new THREE.Vector3(0, 0, -1).applyQuaternion(this._ctrl1.quaternion);
    const origin = new THREE.Vector3().setFromMatrixPosition(this._ctrl1.matrixWorld);
    this._raycaster.set(origin, dir);
    const hits = this._raycaster.intersectObject(plane);
    return hits.length > 0 ? hits[0].point : null;
  }

  _onLeftTrigger() {
    const hit = this._getRightControllerHit();
    if (hit) this.markers.setStart(hit);
  }

  _onRightTrigger() {
    const hit = this._getRightControllerHit();
    if (hit) this.markers.setEnd(hit);
  }

  _onRightGrip() {
    const start = this.markers.getStart();
    const end = this.markers.getEnd();
    if (start && end) this._dispatchRoute(start, end);
  }

  async _dispatchRoute(startPos, endPos) {
    if (this._dispatching) return;
    this._dispatching = true;

    const s = worldToLatLng(startPos.x, startPos.z);
    const e = worldToLatLng(endPos.x, endPos.z);

    speak('Route calculated. Dispatching unit to destination.');

    try {
      const result = await fetchRoute(s.lat, s.lng, e.lat, e.lng);
      const waypoints = result.waypoints ?? [];
      this.routeManager.addSingleRoute(waypoints, 'dispatched');
      if (result.rerouted) {
        speak('Warning. Route rerouted due to hazard. New path calculated.');
        this.routeManager.highlightReroute('dispatched');
      }
    } finally {
      this._dispatching = false;
    }
  }

  _setupDesktopFallback(renderer) {
    const canvas = renderer.domElement;

    canvas.addEventListener('click', (e) => {
      if (renderer.xr.isPresenting) return;
      if (!this._getPlane()) return;

      const rect = canvas.getBoundingClientRect();
      this._mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this._mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      this._raycaster.setFromCamera(this._mouse, this._desktopCamera);
      const hits = this._raycaster.intersectObject(this._getPlane());
      if (!hits.length) return;

      const pt = hits[0].point;
      if (this._clickState === 0) {
        this.markers.setStart(pt);
        this._clickState = 1;
      } else if (this._clickState === 1) {
        this.markers.setEnd(pt);
        this._clickState = 2;
      } else {
        const start = this.markers.getStart();
        const end = this.markers.getEnd();
        if (start && end) this._dispatchRoute(start, end);
        this._clickState = 0;
      }
    });
  }

  setDesktopCamera(camera) {
    this._desktopCamera = camera;
  }

  update() {
    if (!this._getPlane()) return;
    const hit = this._getRightControllerHit();
    if (hit) {
      this._cursor.position.copy(hit);
      this._cursor.position.y = 1;
      this._cursor.visible = true;
    } else {
      this._cursor.visible = false;
    }
  }
}
