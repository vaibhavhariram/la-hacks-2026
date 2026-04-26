// WebMercator helpers for mapping lat/lng to the Mapbox tile grid used by
// `Ground` / `VRScene` terrain meshes. This keeps overlays aligned with imagery.

function _clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

export function latLngToTileFloat(lat, lng, zoom) {
  const n = 2 ** zoom;
  const x = ((lng + 180) / 360) * n;

  const latRad = (lat * Math.PI) / 180;
  const y =
    ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n;

  return { x, y, n };
}

export function tileFloatToLatLng(x, y, zoom) {
  const n = 2 ** zoom;
  const lng = (x / n) * 360 - 180;

  // Inverse WebMercator
  const latRad = Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / n)));
  const lat = (latRad * 180) / Math.PI;

  return { lat, lng };
}

export function latLngToWorldMercator(lat, lng, opts) {
  const { centerLat, centerLng, zoom, tileGrid, worldSize } = opts;
  const tileSize = 256;

  const center = latLngToTileFloat(centerLat, centerLng, zoom);
  const half = Math.floor(tileGrid / 2);
  const x0 = Math.floor(center.x) - half;
  const y0 = Math.floor(center.y) - half;

  const gridPx = tileGrid * tileSize;
  const p = latLngToTileFloat(lat, lng, zoom);
  const xPx = (p.x - x0) * tileSize;
  const yPx = (p.y - y0) * tileSize;

  const u = _clamp(xPx / gridPx, 0, 1);
  const v = _clamp(yPx / gridPx, 0, 1);

  // VR/Ground plane mapping: v increases southward => z increases.
  const xWorld = (u - 0.5) * worldSize;
  const zWorld = (v - 0.5) * worldSize;

  return { x: xWorld, y: 0, z: zWorld };
}

export function worldToLatLngMercator(x, z, opts) {
  const { centerLat, centerLng, zoom, tileGrid, worldSize } = opts;
  const tileSize = 256;

  const center = latLngToTileFloat(centerLat, centerLng, zoom);
  const half = Math.floor(tileGrid / 2);
  const x0 = Math.floor(center.x) - half;
  const y0 = Math.floor(center.y) - half;

  const gridPx = tileGrid * tileSize;
  const u = _clamp(x / worldSize + 0.5, 0, 1);
  const v = _clamp(z / worldSize + 0.5, 0, 1);

  const xPx = u * gridPx;
  const yPx = v * gridPx;

  const xtile = x0 + xPx / tileSize;
  const ytile = y0 + yPx / tileSize;

  return tileFloatToLatLng(xtile, ytile, zoom);
}

