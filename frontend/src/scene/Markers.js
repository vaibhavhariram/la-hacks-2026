import * as THREE from 'three';

export class Markers {
  constructor(scene) {
    this.scene = scene;
    this.startMarker = null;
    this.endMarker = null;
    this.group = new THREE.Group();
    scene.add(this.group);
  }

  _makeRing(color) {
    const geo = new THREE.TorusGeometry(4, 0.6, 8, 32);
    const mat = new THREE.MeshBasicMaterial({ color, toneMapped: false });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.rotation.x = Math.PI / 2;
    mesh.position.y = 2;
    return mesh;
  }

  setStart(worldPos) {
    if (!this.startMarker) {
      this.startMarker = this._makeRing(0x00ff88);
      this.group.add(this.startMarker);
    }
    this.startMarker.position.set(worldPos.x, 2, worldPos.z);
  }

  setEnd(worldPos) {
    if (!this.endMarker) {
      this.endMarker = this._makeRing(0xff4444);
      this.group.add(this.endMarker);
    }
    this.endMarker.position.set(worldPos.x, 2, worldPos.z);
  }

  clearAll() {
    if (this.startMarker) {
      this.group.remove(this.startMarker);
      this.startMarker.geometry.dispose();
      this.startMarker.material.dispose();
      this.startMarker = null;
    }
    if (this.endMarker) {
      this.group.remove(this.endMarker);
      this.endMarker.geometry.dispose();
      this.endMarker.material.dispose();
      this.endMarker = null;
    }
  }

  getStart() {
    return this.startMarker ? this.startMarker.position.clone() : null;
  }

  getEnd() {
    return this.endMarker ? this.endMarker.position.clone() : null;
  }

  update(delta) {
    const speed = 0.8;
    if (this.startMarker) this.startMarker.rotation.z += speed * delta;
    if (this.endMarker) this.endMarker.rotation.z -= speed * delta;
  }
}
