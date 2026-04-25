import * as THREE from 'three';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;

// Eaton Fire origin — Altadena, CA
const CENTER_LAT = 34.1897;
const CENTER_LNG = -118.1315;
const ZOOM = 14;       // crisp satellite detail (~10m/pixel)
const TILE_GRID = 5;   // 5x5 = 25 tiles, covers the full fire spread area

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

async function loadTileImage(url) {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => resolve(img);
    img.onerror = () => {
      console.warn('[Ground] tile failed:', url);
      const blank = document.createElement('canvas');
      blank.width = 256; blank.height = 256;
      resolve(blank);
    };
    img.src = url;
  });
}

export class Ground {
  constructor(scene, renderer) {
    this.scene = scene;
    this.renderer = renderer;
    this.plane = null;
    this._buildFallbackPlane();
    this._buildTerrain();
  }

  _buildFallbackPlane() {
    const geo = new THREE.PlaneGeometry(2000, 2000);
    const mat = new THREE.MeshBasicMaterial({ color: 0x1a1a2e, side: THREE.DoubleSide });
    this.plane = new THREE.Mesh(geo, mat);
    this.plane.rotation.x = -Math.PI / 2;
    this.scene.add(this.plane);
  }

  async _buildTerrain() {
    try {
      if (!MAPBOX_TOKEN) {
        console.warn('[Ground] VITE_MAPBOX_TOKEN is not set; using fallback plane only.');
        return;
      }

      const center = latLngToTile(CENTER_LAT, CENTER_LNG, ZOOM);
      const half = Math.floor(TILE_GRID / 2);
      const tileSize = 256;
      const gridPx = TILE_GRID * tileSize; // 1280 x 1280

      const satCanvas = document.createElement('canvas');
      satCanvas.width = gridPx;
      satCanvas.height = gridPx;
      const satCtx = satCanvas.getContext('2d');

      const demCanvas = document.createElement('canvas');
      demCanvas.width = gridPx;
      demCanvas.height = gridPx;
      const demCtx = demCanvas.getContext('2d');

      const fetches = [];
      for (let dy = -half; dy <= half; dy++) {
        for (let dx = -half; dx <= half; dx++) {
          const tx = center.x + dx;
          const ty = center.y + dy;
          const px = (dx + half) * tileSize;
          const py = (dy + half) * tileSize;

          const satUrl = `https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/${ZOOM}/${tx}/${ty}?access_token=${MAPBOX_TOKEN}`;
          const demUrl = `https://api.mapbox.com/v4/mapbox.terrain-rgb/${ZOOM}/${tx}/${ty}.pngraw?access_token=${MAPBOX_TOKEN}`;

          fetches.push(
            Promise.all([loadTileImage(satUrl), loadTileImage(demUrl)]).then(([satImg, demImg]) => {
              satCtx.drawImage(satImg, px, py, tileSize, tileSize);
              demCtx.drawImage(demImg, px, py, tileSize, tileSize);
            })
          );
        }
      }

      await Promise.all(fetches);

      // high-res geometry: 256 segments gives ~8 world units per vertex = ~800m — enough for smooth hills
      const segments = 256;
      const worldSize = 2000;
      const geo = new THREE.PlaneGeometry(worldSize, worldSize, segments, segments);
      geo.rotateX(-Math.PI / 2);

      const demPixels = demCtx.getImageData(0, 0, gridPx, gridPx);
      const positions = geo.attributes.position;

      for (let i = 0; i < positions.count; i++) {
        const u = positions.getX(i) / worldSize + 0.5;
        const v = positions.getZ(i) / worldSize + 0.5;

        const px = Math.min(Math.floor(u * gridPx), gridPx - 1);
        const py = Math.min(Math.floor(v * gridPx), gridPx - 1);
        const idx = (py * gridPx + px) * 4;

        const r = demPixels.data[idx];
        const g = demPixels.data[idx + 1];
        const b = demPixels.data[idx + 2];
        const elevMeters = terrainRGBToMeters(r, g, b);

        // 1 world unit = 100 meters; 3x vertical exaggeration for dramatic VR hills
        positions.setY(i, (elevMeters / 100) * 3);
      }

      geo.computeVertexNormals();

      const texture = new THREE.CanvasTexture(satCanvas);
      texture.flipY = false;
      // max anisotropy = sharpest texture at oblique angles (Google Earth look)
      texture.anisotropy = this.renderer
        ? this.renderer.capabilities.getMaxAnisotropy()
        : 16;
      texture.minFilter = THREE.LinearMipmapLinearFilter;
      texture.generateMipmaps = true;

      const mat = new THREE.MeshLambertMaterial({ map: texture });

      this.scene.remove(this.plane);
      this.plane.geometry.dispose();
      this.plane.material.dispose();

      this.plane = new THREE.Mesh(geo, mat);
      this.scene.add(this.plane);

      console.log('[Ground] 3D terrain loaded — zoom 14, 5x5 tiles, 256-segment mesh');
    } catch (e) {
      console.warn('[Ground] Terrain load failed, keeping fallback:', e.message);
    }
  }

  getPlane() {
    return this.plane;
  }
}
