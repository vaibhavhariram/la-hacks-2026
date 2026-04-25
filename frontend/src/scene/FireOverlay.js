import * as THREE from 'three';
import { latLngToWorld } from '../utils/coords.js';
import { Tween, TweenManager, easing } from '../utils/tween.js';

const MAX_INSTANCES = 512;

export class FireOverlay {
  constructor(scene) {
    this.tweenManager = new TweenManager();
    this.hazards = new Map(); // id → { lat, lng, radius_m, tween, currentScale }

    const geo = new THREE.CircleGeometry(1, 32);
    const mat = new THREE.MeshBasicMaterial({
      color: 0xff4400,
      transparent: true,
      opacity: 0.6,
      side: THREE.DoubleSide,
    });

    this.mesh = new THREE.InstancedMesh(geo, mat, MAX_INSTANCES);
    this.mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.mesh.count = 0;
    this.mesh.rotation.x = -Math.PI / 2;
    this.mesh.position.y = 0.5;
    scene.add(this.mesh);

    this._dummy = new THREE.Object3D();
  }

  update(hazards, deltaMs) {
    this.tweenManager.update(deltaMs);

    const incoming = new Map(hazards.map((h) => [h.id ?? `${h.lat},${h.lng}`, h]));

    // remove stale
    for (const id of this.hazards.keys()) {
      if (!incoming.has(id)) this.hazards.delete(id);
    }

    // add new
    for (const [id, h] of incoming) {
      if (!this.hazards.has(id)) {
        const targetScale = h.radius_m / 100;
        const tween = new Tween(0, targetScale, 1000, easing.easeOut);
        this.tweenManager.add(tween);
        this.hazards.set(id, { ...h, tween, currentScale: 0 });
      }
    }

    // write instance matrices
    let i = 0;
    for (const [, h] of this.hazards) {
      if (i >= MAX_INSTANCES) break;
      const scale = h.tween.isComplete
        ? h.radius_m / 100
        : h.tween.update(0); // value already updated by tweenManager above

      const world = latLngToWorld(h.lat, h.lng);
      this._dummy.position.set(world.x, 0, world.z);
      this._dummy.scale.set(scale, scale, scale);
      this._dummy.updateMatrix();
      this.mesh.setMatrixAt(i, this._dummy.matrix);
      i++;
    }

    this.mesh.count = i;
    this.mesh.instanceMatrix.needsUpdate = true;
  }
}
