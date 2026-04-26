const CENTER_LAT = 34.0522;
const CENTER_LNG = -118.2437;
const METERS_PER_UNIT = 100;

const LAT_METERS = 111320;
const LNG_METERS = 111320 * Math.cos((CENTER_LAT * Math.PI) / 180);

export function latLngToWorld(lat, lng) {
  const x = ((lng - CENTER_LNG) * LNG_METERS) / METERS_PER_UNIT;
  const z = -((lat - CENTER_LAT) * LAT_METERS) / METERS_PER_UNIT;
  return { x, y: 0, z };
}

export function worldToLatLng(x, z) {
  const lng = CENTER_LNG + (x * METERS_PER_UNIT) / LNG_METERS;
  const lat = CENTER_LAT - (z * METERS_PER_UNIT) / LAT_METERS;
  return { lat, lng };
}
